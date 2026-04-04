"""SpaNET buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SpaEntity
from .runtime_data import get_entry_coordinators


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in get_entry_coordinators(hass, config_entry):
        entities.append(
            SpaButton(
                coordinator,
                "Run Sanitise",
                coordinator.trigger_sanitise,
            )
        )
        entities.append(
            SpaButton(
                coordinator,
                "Stop Sanitise",
                coordinator.stop_sanitise,
            )
        )

    async_add_entity(entities)
    return True


class SpaButton(SpaEntity, ButtonEntity):
    """A SpaNET action button."""

    def __init__(self, coordinator, name, press_callback) -> None:
        super().__init__(coordinator, "button", name)
        self.hass = coordinator.hass
        self._press_callback = press_callback

    async def async_press(self) -> None:
        await self._press_callback()
