"""SpaNet Sensors"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import (
    DOMAIN,
    SK_DATE_TIME,
    SK_HEATER,
    SK_PUMPS,
    SK_SANITISE,
    SK_SANITISE_TIME,
    SK_SETTEMP,
    SK_SLEEPING,
    SK_SUPPORT_MODE,
    SK_WATERTEMP,
)
from .entity import SpaEntity

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities += [
            SpaTemperatureSensor(coordinator, "Water Temperature", SK_WATERTEMP),
            SpaTemperatureSensor(coordinator, "Set Temperature", SK_SETTEMP),
            SpaBinarySensor(coordinator, "Heater", SK_HEATER),
            SpaBinarySensor(coordinator, "Sanitise", SK_SANITISE),
            SpaBinarySensor(coordinator, "Sleeping", SK_SLEEPING),
            SpaTextSensor(
                coordinator,
                "Sanitise Time",
                SK_SANITISE_TIME,
                entity_category=EntityCategory.CONFIG,
            ),
            SpaTextSensor(
                coordinator,
                "Date/Time",
                SK_DATE_TIME,
                entity_category=EntityCategory.DIAGNOSTIC,
                device_suffix="system",
                device_name=f"{coordinator.spa_name} System",
            ),
            SpaTextSensor(
                coordinator,
                "Support Mode",
                SK_SUPPORT_MODE,
                entity_category=EntityCategory.DIAGNOSTIC,
                device_suffix="system",
                device_name=f"{coordinator.spa_name} System",
            ),
        ]

        for k, v in coordinator.get_state(SK_PUMPS).items():
            if not v["hasSwitch"]:
                entities.append(SpaBinarySensor(coordinator, f"Pump {k}", f"pumps.{k}.state"))

    async_add_entity(entities)


class SpaSensor(SpaEntity):
    """A sensor"""

    def __init__(
        self,
        coordinator,
        name,
        status_id,
        device_suffix: str | None = None,
        device_name: str | None = None,
    ) -> None:
        super().__init__(
            coordinator,
            "sensor",
            name,
            device_suffix=device_suffix,
            device_name=device_name,
        )
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


class SpaBinarySensor(SpaSensor, BinarySensorEntity):
    """A binary sensor"""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self):
        value = self.coordinator.get_state(self._status_id)
        if value is None:
            return None
        if value == "on":
            return True
        if value == "off":
            return False
        if value == "auto":
            return False
        return int(value) == 1


class SpaTextSensor(SpaSensor, SensorEntity):
    """A generic text sensor."""

    def __init__(
        self,
        coordinator,
        name,
        status_id,
        entity_category: EntityCategory | None = None,
        device_suffix: str | None = None,
        device_name: str | None = None,
    ) -> None:
        super().__init__(
            coordinator,
            name,
            status_id,
            device_suffix=device_suffix,
            device_name=device_name,
        )
        if device_suffix or device_name:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.spa_id}_{device_suffix}")},
                name=device_name,
            )
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        try:
            return self.coordinator.get_state(self._status_id)
        except Exception:
            return None
