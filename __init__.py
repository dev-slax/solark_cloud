from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL

from .const import (
    DOMAIN, PLATFORMS, DEFAULT_BASE_URL,
    CONF_PLANT_ID, CONF_BASE_URL, DEFAULT_SCAN_INTERVAL,
    CONF_AUTH_MODE, AUTH_MODE_AUTO, CONF_INVERT_GRID_SIGN,
)
from .api import SolarkCloudClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    plant_id = entry.data.get(CONF_PLANT_ID)
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    auth_mode = entry.options.get(CONF_AUTH_MODE, AUTH_MODE_AUTO)
    invert_grid = entry.options.get(CONF_INVERT_GRID_SIGN, False)

    update_seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    client = SolarkCloudClient(
        username,
        password,
        plant_id or "",
        base_url=base_url,
        auth_mode=auth_mode,
        update_seconds=update_seconds,
    )

    async def async_update_data() -> dict[str, Any]:
        try:
            flow = await client.get_flow()
            flow_metrics = client.parse_metrics_from_flow(flow)
            genuse = await client.get_generation_use()
            energy_today = client.parse_energy_today_from_generation_use(genuse)
            if coordinator.data is not None:
                grid_energy = client.parse_daily_energy_from_flow(
                    flow, coordinator.data["metrics"]
                )
            else:
                grid_energy = {
                    # initialize if nonexistent
                    "grid_import_energy_today": 0,
                    "grid_export_energy_today": 0,
                    "load_energy_today": 0,
                }
            metrics = flow_metrics | {"energy_today": energy_today} | grid_energy
            return {"metrics": metrics, "last_error": client.last_error}
        except Exception as err:
            _LOGGER.error("Update failed: %s", err)
            return {"metrics": {}, "last_error": str(err)}

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER,
        name=f"{DOMAIN}_coordinator",
        update_method=async_update_data,
        update_interval=timedelta(seconds=update_seconds),
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning("First refresh failed: %s", err)

    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data and (client := data.get("client")):
        await client.close()
    return unload_ok
