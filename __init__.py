
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS, DEFAULT_SCAN_INTERVAL
from .api import SolArkCloudApi, SolArkAuthError, SolArkApiError

_LOGGER = logging.getLogger(__name__)

type SolarkData = dict

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = SolArkCloudApi(
        hass,
        username=entry.data["username"],
        password=entry.data["password"],
        plant_id=entry.data.get("plant_id"),
        base_url=entry.data.get("base_url"),
    )

    async def _async_update() -> SolarkData:
        try:
            return await api.async_get_flow_and_day_energy()
        except (SolArkAuthError, SolArkApiError) as e:
            raise UpdateFailed(str(e)) from e

    coordinator = DataUpdateCoordinator[SolarkData](
        hass,
        _LOGGER,
        name="solark_cloud",
        update_method=_async_update,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )
    # Do first refresh to populate sensors
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
