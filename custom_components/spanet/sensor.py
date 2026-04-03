"""SpaNET sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import (
    DOMAIN,
    SK_SETTEMP,
    SK_SUPPORT_MODE,
    SK_WATERTEMP,
)
from .entity import SpaEntity

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities += [
            SpaTemperatureSensor(coordinator, "Water Temperature", SK_WATERTEMP),
            SpaTemperatureSensor(coordinator, "Set Temperature", SK_SETTEMP),
            SpaTextSensor(
                coordinator,
                "Support Mode",
                SK_SUPPORT_MODE,
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
        ]

    async_add_entities(entities)


class SpaSensor(SpaEntity):
    """A sensor"""

    def __init__(self, coordinator, name, status_id) -> None:
        super().__init__(coordinator, "sensor", name)
        self.hass = coordinator.hass
        self._status_id = status_id


class SpaTemperatureSensor(SpaSensor, SensorEntity):
    """A temp sensor"""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    @property
    def native_value(self):
        value = self.coordinator.get_state(self._status_id)
        if value is None:
            return None
        return int(value) / 10


class SpaTextSensor(SpaSensor, SensorEntity):
    """A generic text sensor."""

    def __init__(
        self,
        coordinator,
        name,
        status_id,
        entity_category: EntityCategory | None = None,
    ) -> None:
        super().__init__(coordinator, name, status_id)
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        try:
            return self.coordinator.get_state(self._status_id)
        except Exception:
            return None
