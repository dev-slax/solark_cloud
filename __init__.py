from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarkApiError, SolarkAuthError, SolarkCloudClient
from .const import (
    AUTH_MODE_AUTO,
    AUTH_MODES,
    CONF_AUTH_MODE,
    CONF_BASE_URL,
    CONF_INVERT_GRID_SIGN,
    CONF_PLANT_ID,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KNOWN_API_URLS,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
    PORTAL_URL,
)

_LOGGER = logging.getLogger(__name__)


def _bounded_scan_interval(value: Any) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SCAN_INTERVAL
    return max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, seconds))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    legacy_api_url = entry.data.get(CONF_BASE_URL, DEFAULT_API_URL).rstrip("/")
    api_url = legacy_api_url if legacy_api_url in KNOWN_API_URLS else DEFAULT_API_URL
    if legacy_api_url != api_url:
        _LOGGER.warning("Ignoring unsupported legacy Sol-Ark API base URL")

    update_seconds = _bounded_scan_interval(
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    auth_mode = entry.options.get(CONF_AUTH_MODE, AUTH_MODE_AUTO)
    if auth_mode not in AUTH_MODES:
        auth_mode = AUTH_MODE_AUTO
    invert_grid = bool(entry.options.get(CONF_INVERT_GRID_SIGN, False))

    client = SolarkCloudClient(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data.get(CONF_PLANT_ID, ""),
        async_get_clientsession(hass),
        api_url=api_url,
        origin_url=PORTAL_URL,
        fallback_urls=KNOWN_API_URLS,
        auth_mode=auth_mode,
    )

    async def async_update_data() -> dict[str, Any]:
        try:
            flow = await client.get_flow()
            flow_metrics = client.parse_metrics_from_flow(flow, invert=invert_grid)

            generation = await client.get_generation_use()
            energy_today = client.parse_energy_today_from_generation_use(generation)
            cloud_energy = client.parse_grid_energy_today_from_generation_use(generation)

            metrics = flow_metrics | {"energy_today": energy_today} | cloud_energy
            return {"metrics": metrics, "last_error": None}
        except SolarkAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SolarkApiError as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_coordinator",
        update_method=async_update_data,
        update_interval=timedelta(seconds=update_seconds),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
