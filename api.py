from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)
_REQUEST_TIMEOUT_SECONDS = 20
_TOKEN_EXPIRY_MARGIN_SECONDS = 600


class SolarkError(Exception):
    """Base exception for expected Sol-Ark API failures."""


class SolarkAuthError(SolarkError):
    """Authentication was rejected by MySolArk."""


class SolarkApiError(SolarkError):
    """MySolArk could not be reached or returned an invalid response."""


class SolarkCloudClient:
    """Minimal asynchronous client for the MySolArk cloud API."""

    def __init__(
        self,
        username: str,
        password: str,
        plant_id: str,
        session: aiohttp.ClientSession,
        *,
        api_url: str = "https://p2.api.solarkcloud.com",
        origin_url: str = "https://www.solarkcloud.com",
        fallback_urls: tuple[str, ...] = (),
        auth_mode: str = "auto",
    ) -> None:
        self._username = username
        self._password = password
        self._plant_id = str(plant_id or "")
        self._session = session
        self._api_url = api_url.rstrip("/")
        self._origin_url = origin_url.rstrip("/")
        self._fallback_urls = tuple(url.rstrip("/") for url in fallback_urls)
        self._auth_mode = auth_mode
        self._token: str | None = None
        self._token_expiry: float | None = None
        self.last_error: str | None = None

    async def _ensure_token(self) -> None:
        now = time.time()
        if self._token and self._token_expiry and now < self._token_expiry:
            return
        await self._login()

    @staticmethod
    def _login_headers(origin: str, mode: str) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json",
        }
        if mode == "strict":
            headers["Origin"] = origin
            headers["Referer"] = f"{origin}/"
        return headers

    async def _try_login_once(
        self, base: str, headers_mode: str
    ) -> tuple[bool, bool]:
        payload = {
            "client_id": "csp-web",
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
        }

        try:
            async with asyncio.timeout(_REQUEST_TIMEOUT_SECONDS):
                async with self._session.post(
                    f"{base}/oauth/token",
                    json=payload,
                    headers=self._login_headers(self._origin_url, headers_mode),
                ) as response:
                    if response.status != 200:
                        auth_rejected = response.status in (400, 401, 403)
                        self.last_error = (
                            f"login failed at {base} ({headers_mode}): "
                            f"HTTP {response.status}"
                        )
                        return False, auth_rejected
                    try:
                        data = await response.json(content_type=None)
                    except (ValueError, TypeError):
                        self.last_error = f"login returned invalid JSON at {base}"
                        return False, False
        except TimeoutError:
            self.last_error = f"login timed out at {base}"
            return False, False
        except aiohttp.ClientError:
            self.last_error = f"login request failed at {base}"
            return False, False

        token: str | None = None
        expires_in = 3600
        if isinstance(data, dict):
            nested = data.get("data")
            nested = nested if isinstance(nested, dict) else {}
            token = (
                nested.get("access_token")
                or data.get("access_token")
                or data.get("token")
            )
            raw_expiry = nested.get("expires_in", data.get("expires_in", expires_in))
            try:
                expires_in = int(raw_expiry)
            except (TypeError, ValueError):
                expires_in = 3600

        if not token:
            self.last_error = f"login returned no token at {base}"
            return False, False

        self._token = str(token)
        self._token_expiry = time.time() + max(
            60, expires_in - _TOKEN_EXPIRY_MARGIN_SECONDS
        )
        self.last_error = None
        return True, False

    async def _login(self) -> None:
        self.last_error = None

        bases: list[str] = []
        for base in (self._api_url, *self._fallback_urls):
            if base and base not in bases:
                bases.append(base)

        if self._auth_mode == "auto":
            modes = ("strict", "legacy")
        elif self._auth_mode == "strict":
            modes = ("strict",)
        else:
            modes = ("legacy",)

        saw_auth_rejection = False
        # Deliberately bounded: at most two known hosts x two auth modes.
        for base in bases[:2]:
            for mode in modes:
                ok, auth_rejected = await self._try_login_once(base, mode)
                saw_auth_rejection = saw_auth_rejection or auth_rejected
                if ok:
                    self._api_url = base
                    return
                _LOGGER.debug("%s", self.last_error)

        if saw_auth_rejection:
            raise SolarkAuthError(self.last_error or "authentication rejected")
        raise SolarkApiError(self.last_error or "login failed")

    async def _request_json(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        # Exactly one retry is permitted after a 401. No recursion.
        for attempt in range(2):
            await self._ensure_token()
            headers = {
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            }

            try:
                async with asyncio.timeout(_REQUEST_TIMEOUT_SECONDS):
                    async with self._session.get(
                        f"{self._api_url}{path}", headers=headers, params=params
                    ) as response:
                        if response.status == 401:
                            self._token = None
                            self._token_expiry = None
                            if attempt == 0:
                                continue
                            raise SolarkAuthError("authentication rejected")
                        if response.status != 200:
                            self.last_error = (
                                f"GET {path} failed: HTTP {response.status}"
                            )
                            raise SolarkApiError(self.last_error)
                        try:
                            data = await response.json(content_type=None)
                        except (ValueError, TypeError) as err:
                            raise SolarkApiError(
                                f"GET {path} returned invalid JSON"
                            ) from err
            except TimeoutError as err:
                raise SolarkApiError(f"GET {path} timed out") from err
            except aiohttp.ClientError as err:
                raise SolarkApiError(f"GET {path} request failed") from err

            if not isinstance(data, dict):
                raise SolarkApiError(
                    f"GET {path} returned an unexpected payload"
                )

            self.last_error = None
            return data

        raise SolarkAuthError("authentication rejected")

    async def get_flow(self, date_str: str | None = None) -> dict[str, Any]:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        params = {"date": date_str, "id": self._plant_id, "lan": "en"}
        data = await self._request_json(
            f"/api/v1/plant/energy/{self._plant_id}/flow", params=params
        )
        payload = data.get("data")
        return payload if isinstance(payload, dict) else {}

    async def get_generation_use(self, date_str: str | None = None) -> dict[str, Any]:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        params = {"date": date_str, "lan": "en"}
        data = await self._request_json(
            f"/api/v1/plant/energy/{self._plant_id}/generation/use", params=params
        )
        payload = data.get("data")
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _pick(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        flow = data.get("flow")
        if isinstance(flow, dict):
            for key in keys:
                if key in flow and flow[key] is not None:
                    return flow[key]
        return default

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def parse_metrics_from_flow(
        cls, flow: dict[str, Any], invert: bool = False
    ) -> dict[str, float | None]:
        pv = cls._to_float(cls._pick(flow, "pvPower", "pv", "solarPower", "pv_input"))
        load = cls._to_float(
            cls._pick(flow, "loadOrEpsPower", "loadPower", "load", "housePower")
        )
        grid_signed = cls._to_float(
            cls._pick(flow, "gridOrMeterPower", "gridPower", "grid", "gridNet")
        )
        battery = cls._to_float(
            cls._pick(flow, "battPower", "batteryPower", "battery", "batt")
        )
        soc = cls._to_float(
            cls._pick(flow, "soc", "batterySoc", "batterySoC", "battSoc")
        )

        grid_import: float | None = None
        grid_export: float | None = None
        if grid_signed is not None:
            if invert:
                grid_export = max(grid_signed, 0.0)
                grid_import = max(-grid_signed, 0.0)
            else:
                grid_import = max(grid_signed, 0.0)
                grid_export = max(-grid_signed, 0.0)

        return {
            "pv_power": pv,
            "load_power": load,
            "grid_import_power": grid_import,
            "grid_export_power": grid_export,
            "battery_power": battery,
            "battery_soc": soc,
        }

    @classmethod
    def parse_energy_today_from_generation_use(
        cls, genuse: dict[str, Any]
    ) -> float | None:
        return cls._to_float(genuse.get("pv"))

    @classmethod
    def parse_grid_energy_today_from_generation_use(
        cls, genuse: dict[str, Any]
    ) -> dict[str, float | None]:
        return {
            "grid_import_energy_today": cls._to_float(genuse.get("gridBuy")),
            "grid_export_energy_today": cls._to_float(genuse.get("gridSell")),
            "load_energy_today": cls._to_float(genuse.get("load")),
            "battery_charge_energy_today": cls._to_float(genuse.get("batteryCharge")),
            "battery_discharge_energy_today": cls._to_float(
                genuse.get("batteryDischarge")
            ),
        }
