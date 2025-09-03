
from __future__ import annotations
import logging
from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

PARSE_CANDIDATES_POWER_W = [
    ("pv", "power"),
    ("pv", "w"),
    ("pvPower",),
    ("solar", "power"),
    ("solarPower",),
]
PARSE_CANDIDATES_ENERGY_KWH = [
    ("pv", "eDay"),
    ("pv", "energyDay"),
    ("energy", "day"),
    ("eDay",),
    ("day_energy",),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = [
        SolArkPvPowerSensor(coordinator, entry),
        SolArkPvEnergyTodaySensor(coordinator, entry),
    ]
    async_add_entities(entities)


class BaseSolArkSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    @property
    def available(self) -> bool:
        v = self._value() is not None
        return v and super().available

    def _extract_nested(self, data: Any, *keys: str) -> Any:
        cur = data
        for k in keys:
            if cur is None:
                return None
            if isinstance(cur, dict):
                # try several casings
                candidates = [k, k.lower(), k.upper(), k.capitalize()]
                found = None
                for c in candidates:
                    if c in cur:
                        found = cur[c]
                        break
                cur = found
            else:
                # object attribute
                cur = getattr(cur, k, None) or getattr(cur, k.lower(), None) or getattr(cur, k.upper(), None)
        return cur

    def _search_candidates(self, candidates: list[tuple[str, ...]]) -> Any:
        flow = self.coordinator.data.get("flow", {})
        # sometimes flow might be nested under 'data'
        if isinstance(flow, dict) and "data" in flow:
            flow = flow["data"]
        for keys in candidates:
            val = self._extract_nested(flow, *keys)
            if isinstance(val, (int, float)):
                return val
        # fallback: scan for key names containing hints
        return None


class SolArkPvPowerSensor(BaseSolArkSensor):
    _attr_native_unit_of_measurement = "W"
    _attr_device_class = "power"
    _attr_name = "PV Power"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_pv_power"

    def _value(self):
        return self._search_candidates(PARSE_CANDIDATES_POWER_W)

    @property
    def native_value(self):
        return self._value()


class SolArkPvEnergyTodaySensor(BaseSolArkSensor):
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "total_increasing"
    _attr_name = "PV Energy Today"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_pv_energy_today"

    def _value(self):
        # Prefer day energy from 'day' payload first
        day = self.coordinator.data.get("day") or {}
        if isinstance(day, dict):
            for k in ("eDay", "day", "energy", "pvEnergy", "today"):
                v = day.get(k)
                if isinstance(v, (int, float)):
                    return v
                if isinstance(v, dict):
                    for kk in ("value", "kWh"):
                        vv = v.get(kk)
                        if isinstance(vv, (int, float)):
                            return vv
        # fall back to flow candidates
        val = self._search_candidates(PARSE_CANDIDATES_ENERGY_KWH)
        return val

    @property
    def native_value(self):
        return self._value()
