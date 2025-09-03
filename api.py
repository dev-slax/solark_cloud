
from __future__ import annotations
import logging
from typing import Any, Optional
from homeassistant.core import HomeAssistant

import asyncio

_LOGGER = logging.getLogger(__name__)

class SolArkAuthError(Exception):
    pass

class SolArkApiError(Exception):
    pass

class SolArkCloudApi:
    """Thin wrapper around the third-party solark-cloud package with graceful fallbacks.
    We intentionally do not rely on undocumented endpoints here. The solark-cloud package
    abstracts auth + calls to MySolArk (api.solarkcloud.com).
    """
    def __init__(self, hass: HomeAssistant, username: str, password: str, plant_id: Optional[str] = None, base_url: Optional[str] = None):
        self._hass = hass
        self._username = username
        self._password = password
        self._plant_id = plant_id  # may be None; we will pick the first plant.
        self._base_url = base_url
        self._client = None

    def _load_client(self):
        """Load and initialize the solark-cloud client lazily."""
        if self._client is not None:
            return self._client

        try:
            # The library's public API is minimal; try a few likely class names.
            import solark_cloud  # type: ignore
        except Exception as e:
            raise SolArkApiError("The 'solark-cloud' package is not available") from e

        # Identify a constructor
        candidate_class_names = ["Client", "SolArkClient", "SolarkClient", "SolArkCloud", "API"]
        client_cls = None
        for name in candidate_class_names:
            client_cls = getattr(solark_cloud, name, None)
            if client_cls:
                break

        if client_cls is None:
            # Some packages expose a function to create a client
            make = getattr(solark_cloud, "client", None) or getattr(solark_cloud, "create_client", None)
            if make:
                self._client = make(self._username, self._password)  # type: ignore
                return self._client
            raise SolArkApiError("Unsupported solark-cloud client API; upgrade the integration or library.")

        try:
            # Many libs take username/password; base_url is optional.
            try:
                self._client = client_cls(self._username, self._password, base_url=self._base_url)  # type: ignore
            except TypeError:
                self._client = client_cls(self._username, self._password)  # type: ignore
            return self._client
        except Exception as e:
            raise SolArkAuthError(f"Failed to initialize Sol-Ark client: {e}") from e

    def _sync_list_plants(self):
        c = self._load_client()
        # Try common methods
        for method in ("plants", "get_plants", "list_plants"):
            m = getattr(c, method, None)
            if callable(m):
                res = m()
                if res:
                    return res
        raise SolArkApiError("Could not list plants via solark-cloud client.")

    def _sync_get_flow(self, plant_id: str):
        c = self._load_client()
        for method in ("flow", "get_flow", "plant_flow", "get_power_flow"):
            m = getattr(c, method, None)
            if callable(m):
                return m(plant_id)
        # Some clients use plant objects
        for method in ("plant", "get_plant"):
            m = getattr(c, method, None)
            if callable(m):
                plant = m(plant_id)
                for pm in ("flow", "get_flow", "power_flow"):
                    mm = getattr(plant, pm, None)
                    if callable(mm):
                        return mm()
        raise SolArkApiError("Could not fetch power flow from solark-cloud client.")

    def _sync_get_day_energy(self, plant_id: str):
        c = self._load_client()
        # Try common methods: energy_day or history
        for method in ("energy_day", "get_energy_day", "energy", "get_energy"):
            m = getattr(c, method, None)
            if callable(m):
                try:
                    return m(plant_id, period="day")  # type: ignore
                except TypeError:
                    return m(plant_id)  # type: ignore
        # Plant object
        for method in ("plant", "get_plant"):
            m = getattr(c, method, None)
            if callable(m):
                plant = m(plant_id)
                for pm in ("energy_day", "get_energy_day", "energy", "get_energy"):
                    mm = getattr(plant, pm, None)
                    if callable(mm):
                        try:
                            return mm(period="day")  # type: ignore
                        except TypeError:
                            return mm()  # type: ignore
        # No luck; just return None and sensors will skip
        return None

    async def async_get_flow_and_day_energy(self) -> dict[str, Any]:
        return await self._hass.async_add_executor_job(self._get_flow_and_day_energy)

    def _get_flow_and_day_energy(self) -> dict[str, Any]:
        # Resolve plant_id if missing
        plant_id = self._plant_id
        if not plant_id:
            plants = self._sync_list_plants()
            # Support list of dicts or objects with 'id'
            if isinstance(plants, dict) and "plants" in plants:
                items = plants["plants"]
            else:
                items = plants
            if not items:
                raise SolArkApiError("No plants available on this account.")
            first = items[0]
            plant_id = getattr(first, "id", None) or first.get("id") if isinstance(first, dict) else None
            if not plant_id:
                # Some APIs use 'plantId' or 'plant_id'
                if isinstance(first, dict):
                    plant_id = first.get("plantId") or first.get("plant_id")
            if not plant_id:
                raise SolArkApiError("Could not determine plant_id from API response; please set it in the integration options.")
            self._plant_id = str(plant_id)

        flow = self._sync_get_flow(self._plant_id)
        day = self._sync_get_day_energy(self._plant_id)

        return {"flow": flow, "day": day, "plant_id": self._plant_id}
