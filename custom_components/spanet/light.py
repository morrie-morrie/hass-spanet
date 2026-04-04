"""SpaNET light platform."""

from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SK_LIGHTS
from .entity import SpaEntity
from .runtime_data import get_entry_coordinators


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []
    for coordinator in get_entry_coordinators(hass, config_entry):
        entities.append(SpaLight(coordinator))
    async_add_entity(entities)
    return True


class SpaLight(SpaEntity, LightEntity):
    """Represents spa light control as a native light entity."""

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "light", "Light")
        self.hass = coordinator.hass

    @property
    def is_on(self) -> bool | None:
        try:
            value = self.coordinator.get_state(f"{SK_LIGHTS}.state")
        except Exception:
            return None
        return value == "on"

    @property
    def brightness(self) -> int | None:
        try:
            level = int(self.coordinator.get_state(f"{SK_LIGHTS}.brightness"))
        except Exception:
            return None
        level = max(1, min(5, level))
        return int(round((level / 5) * 255))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.set_lights("on")
        if ATTR_BRIGHTNESS in kwargs and kwargs[ATTR_BRIGHTNESS] is not None:
            value = int(kwargs[ATTR_BRIGHTNESS])
            mapped = max(1, min(5, round((value / 255) * 5)))
            await self.coordinator.set_light_brightness(mapped)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.set_lights("off")
