from datetime import datetime
import time
from typing import Any, Dict, Optional, List, Tuple
import aiohttp
import async_timeout
import logging
from urllib.parse import urlparse

_LOGGER = logging.getLogger(__name__)

class SolarkCloudClient:
    def __init__(self, username: str, password: str, plant_id: str, base_url: str = "https://api.solarkcloud.com", session: Optional[aiohttp.ClientSession] = None, auth_mode: str = "auto", update_seconds: int = 0) -> None:
        self._username = username
        self._password = password
        self._plant_id = str(plant_id or "")
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._auth_mode = auth_mode
        self.last_error: Optional[str] = None

        self._update_seconds = update_seconds

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _ensure_token(self) -> None:
        now = time.time()
        if self._token and self._token_expiry and now < self._token_expiry:
            return
        await self._login()

    def _login_headers(self, base: str, mode: str) -> Dict[str, str]:
        h = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json",
        }
        if mode == "strict":
            h["Origin"] = base
            h["Referer"] = f"{base}/"
        return h

    async def _try_login_once(
        self, base: str, headers_mode: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        url = f"{base}/oauth/token"
        payload = {
            "client_id": "csp-web",
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
        }
        headers = self._login_headers(base, headers_mode)
        async with async_timeout.timeout(20):
            async with self.session.post(url, json=payload, headers=headers) as resp:
                txt = await resp.text()
                if resp.status != 200:
                    return False, f"{resp.status} {txt[:180]}", resp.status
                data = await resp.json(content_type=None)
        token = None
        expires_in = 3600
        if isinstance(data, dict):
            token = (
                (data.get("data") or {}).get("access_token")
                or data.get("access_token")
                or data.get("token")
            )
            expires_in = int(
                (data.get("data") or {}).get(
                    "expires_in", data.get("expires_in", expires_in)
                )
            )
        if not token:
            return False, "no access_token in response", None
        self._token = token
        self._token_expiry = time.time() + max(60, expires_in - 600)
        return True, None, None

    async def _login(self) -> None:
        self.last_error = None
        bases = [self._base_url]
        # Offer cross-host fallback if the user entered one of the two known hosts
        host = urlparse(self._base_url).netloc
        alt = (
            "https://www.mysolark.com"
            if "api.solarkcloud.com" in host
            else "https://api.solarkcloud.com"
        )
        if alt not in bases:
            bases.append(alt)

        modes = []
        if self._auth_mode == "auto":
            modes = ["strict", "legacy"]
        elif self._auth_mode == "strict":
            modes = ["strict"]
        else:
            modes = ["legacy"]

        # Try combinations
        for b in bases:
            for m in modes:
                ok, err, code = await self._try_login_once(b, m)
                if ok:
                    self._base_url = b  # use the working base
                    return
                else:
                    self.last_error = f"login failed at {b} ({m}): {err}"
                    _LOGGER.debug(self.last_error)
        raise RuntimeError(self.last_error or "Login failed")

    async def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        await self._ensure_token()
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        async with async_timeout.timeout(20):
            async with self.session.get(url, headers=headers, params=params) as resp:
                txt = await resp.text()
                if resp.status != 200:
                    self.last_error = f"GET {path} failed: {resp.status} {txt[:180]}"
                    raise RuntimeError(self.last_error)
                return await resp.json(content_type=None)

    async def get_flow(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        from datetime import datetime, timezone

        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        params = {"date": date_str, "id": self._plant_id, "lan": "en"}
        data = await self._get(
            f"/api/v1/plant/energy/{self._plant_id}/flow", params=params
        )
        return (data.get("data") if isinstance(data, dict) else data) or {}

    async def get_generation_use(
        self, date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        from datetime import datetime, timezone

        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        params = {"date": date_str, "lan": "en"}
        data = await self._get(
            f"/api/v1/plant/energy/{self._plant_id}/generation/use", params=params
        )
        return (data.get("data") if isinstance(data, dict) else data) or {}

    async def get_plants(self) -> Dict[str, Any]:
        return await self._get(
            "/api/v1/plants", params={"page": 1, "limit": 10, "name": "", "status": ""}
        )

    def parse_daily_energy_from_flow(
        self, flow: Dict[str, Any], metrics: Dict[str, Any], invert: bool = False
    ) -> Dict[str, Any]:
        if metrics == {}:
            return {
                "grid_import_energy_today": 0,
                "grid_export_energy_today": 0,
                "load_energy_today": 0,
            }
        grid_import = grid_export = grid_import_energy_today = (
            grid_export_energy_today
        ) = load_energy_today = None
        load = self._to_float(
            self._pick(flow, "loadOrEpsPower", "loadPower", "load", "housePower")
        )
        grid_signed = self._to_float(
            self._pick(flow, "gridOrMeterPower", "gridPower", "grid", "gridNet")
        )
        if grid_signed is not None:
            if not invert:
                if grid_signed >= 0:
                    grid_import = grid_signed
                    grid_export = 0.0
                else:
                    grid_import = 0.0
                    grid_export = abs(grid_signed)
            else:
                # Inverted: positive = export, negative = import
                if grid_signed >= 0:
                    grid_export = grid_signed
                    grid_import = 0.0
                else:
                    grid_export = 0.0
                    grid_import = abs(grid_signed)
        if metrics is not None:
            # get prior grid_import_energy_today
            grid_import_energy_today = metrics["grid_import_energy_today"] + (
                grid_import / 1000
            ) * (self._update_seconds / 60)
            grid_export_energy_today = metrics["grid_export_energy_today"] + (
                grid_export / 1000
            ) * (self._update_seconds / 60)
            load_energy_today = metrics["load_energy_today"] + (load / 1000) * (
                self._update_seconds / 60
            )
        hour = int(datetime.today().strftime("%H"))
        minute = int(datetime.today().strftime("%M"))
        if hour == 0 and minute <= 2:
            # reset daily statistics at midnight
            grid_import_energy_today = (grid_import / 1000) * (
                self._update_seconds / 60
            )
            grid_export_energy_today = (grid_export / 1000) * (
                self._update_seconds / 60
            )
            load_energy_today = (load / 1000) * (self._update_seconds / 60)

        return {
            "grid_import_energy_today": grid_import_energy_today,
            "grid_export_energy_today": grid_export_energy_today,
            "load_energy_today": load_energy_today,
        }

    @staticmethod
    def _pick(d: Dict[str, Any], *keys, default=None):
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        flow = d.get("flow")
        if isinstance(flow, dict):
            for k in keys:
                if k in flow and flow[k] is not None:
                    return flow[k]
        return default

    @staticmethod
    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    @classmethod
    def parse_metrics_from_flow(
        cls, flow: Dict[str, Any], invert: bool = False
    ) -> Dict[str, Any]:
        pv = cls._to_float(cls._pick(flow, "pvPower", "pv", "solarPower", "pv_input"))
        load = cls._to_float(
            cls._pick(flow, "loadOrEpsPower", "loadPower", "load", "housePower")
        )
        grid_signed = cls._to_float(
            cls._pick(flow, "gridOrMeterPower", "gridPower", "grid", "gridNet")
        )
        batt = cls._to_float(
            cls._pick(flow, "battPower", "batteryPower", "battery", "batt")
        )
        soc = cls._to_float(
            cls._pick(flow, "soc", "batterySoc", "batterySoC", "battSoc")
        )
        if grid_signed is not None:
            if not invert:
                if grid_signed >= 0:
                    grid_import = grid_signed
                    grid_export = 0.0
                else:
                    grid_import = 0.0
                    grid_export = abs(grid_signed)
            else:
                # Inverted: positive = export, negative = import
                if grid_signed >= 0:
                    grid_export = grid_signed
                    grid_import = 0.0
                else:
                    grid_export = 0.0
                    grid_import = abs(grid_signed)

        return {
            "pv_power": pv,
            "load_power": load,
            "grid_import_power": grid_import,
            "grid_export_power": grid_export,
            "battery_power": batt,
            "battery_soc": soc,
        }

    @classmethod
    def parse_energy_today_from_generation_use(
        cls, genuse: Dict[str, Any]
    ) -> Optional[float]:
        val = genuse.get("pv")
        try:
            return float(val) if val is not None else None
        except Exception:
            return None

    @classmethod
    def parse_grid_energy_today_from_generation_use(
        cls, genuse: Dict[str, Any]
    ) -> Dict[str, Optional[float]]:
        def f(v):
            try:
                return float(v) if v is not None else None
            except Exception:
                return None

        return {
            "grid_import_energy_today": f(genuse.get("gridBuy")),
            "grid_export_energy_today": f(genuse.get("gridSell")),
            "load_energy_today": f(genuse.get("load")),
            "battery_charge_energy_today": f(genuse.get("batteryCharge")),
            "battery_discharge_energy_today": f(genuse.get("batteryDischarge"))
            if "batteryDischarge" in genuse
            else None,
        }
