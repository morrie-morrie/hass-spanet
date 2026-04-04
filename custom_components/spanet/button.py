"""SpaNET buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities.append(
            SpaButton(
                coordinator,
                "Run Sanitise",
                coordinator.trigger_sanitise,
                entity_category=EntityCategory.CONFIG,
            )
        )
        entities.append(
            SpaButton(
                coordinator,
                "Stop Sanitise",
                coordinator.stop_sanitise,
                entity_category=EntityCategory.CONFIG,
            )
        )

    async_add_entity(entities)
    return True


class SpaButton(SpaEntity, ButtonEntity):
    """A SpaNET action button."""

    def __init__(self, coordinator, name, press_callback, entity_category: EntityCategory | None = None) -> None:
        super().__init__(coordinator, "button", name)
        self.hass = coordinator.hass
        self._press_callback = press_callback
        self._attr_entity_category = entity_category

    async def async_press(self) -> None:
        await self._press_callback()
