"""SpaNET number entities."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SK_BLOWER
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []
    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        if SK_BLOWER in coordinator.state:
            entities.append(SpaBlowerSpeedNumber(coordinator))
    async_add_entity(entities)
    return True


class SpaBlowerSpeedNumber(SpaEntity, NumberEntity):
    """Blower variable speed control."""

    _attr_native_min_value = 1
    _attr_native_max_value = 5
    _attr_native_step = 1
    _attr_icon = "mdi:fan-speed-3"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "number", "Blower Speed")
        self._attr_name = "Blower Variable Speed"

    @property
    def available(self) -> bool:
        try:
            return self.coordinator.get_state(f"{SK_BLOWER}.state") == "variable"
        except Exception:
            return False

    @property
    def native_value(self):
        try:
            return int(self.coordinator.get_state(f"{SK_BLOWER}.speed"))
        except Exception:
            return None

    @property
    def extra_state_attributes(self):
        return {"active_when_mode": "variable"}

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.set_blower_speed(int(value))
