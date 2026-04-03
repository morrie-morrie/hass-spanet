"""SpaNET sleep timer time entities."""

from __future__ import annotations

from datetime import time
from functools import partial

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api_mappings import extract_time_string
from .const import DOMAIN, SK_SANITISE_TIME, SK_SLEEP_TIMERS
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []
    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities.append(
            SpaConfigTime(
                coordinator,
                "Sanitise Time",
                SK_SANITISE_TIME,
                coordinator.set_sanitise_time,
            )
        )
        for key, _ in coordinator.get_state(SK_SLEEP_TIMERS).items():
            entities.append(
                SpaSleepTimerTime(
                    coordinator,
                    f"Sleep Timer {key} On Time",
                    f"{SK_SLEEP_TIMERS}.{key}.startTime",
                    partial(coordinator.set_sleep_timer_on_time, key),
                )
            )
            entities.append(
                SpaSleepTimerTime(
                    coordinator,
                    f"Sleep Timer {key} Off Time",
                    f"{SK_SLEEP_TIMERS}.{key}.endTime",
                    partial(coordinator.set_sleep_timer_off_time, key),
                )
            )

    async_add_entity(entities)
    return True


class SpaSleepTimerTime(SpaEntity, TimeEntity):
    """Spa sleep timer time setting."""

    def __init__(self, coordinator, name: str, state_key: str, setter):
        super().__init__(coordinator, "time", name)
        self._state_key = state_key
        self._setter = setter
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> time | None:
        try:
            value = self.coordinator.get_state(self._state_key)
        except Exception:
            return None
        parsed = extract_time_string(value)
        if not parsed:
            return None
        try:
            hour, minute = parsed.split(":")[0:2]
            return time(hour=int(hour), minute=int(minute))
        except (ValueError, TypeError):
            return None

    async def async_set_value(self, value: time) -> None:
        await self._setter(f"{value.hour:02d}:{value.minute:02d}")


class SpaConfigTime(SpaEntity, TimeEntity):
    """Spa generic time setting."""

    def __init__(self, coordinator, name: str, state_key: str, setter):
        super().__init__(coordinator, "time", name)
        self._state_key = state_key
        self._setter = setter
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> time | None:
        try:
            value = self.coordinator.get_state(self._state_key)
        except Exception:
            return None
        parsed = extract_time_string(value)
        if not parsed:
            return None
        try:
            hour, minute = parsed.split(":")[0:2]
            return time(hour=int(hour), minute=int(minute))
        except (ValueError, TypeError):
            return None

    async def async_set_value(self, value: time) -> None:
        await self._setter(f"{value.hour:02d}:{value.minute:02d}")
