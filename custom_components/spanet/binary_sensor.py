"""SpaNET binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    SK_CLOUD_CONNECTED,
    SK_HEATER,
    SK_PUMPS,
    SK_SANITISE,
    SK_SLEEPING,
)
from .entity import SpaEntity
from .runtime_data import get_entry_coordinators


def _pump_sort_key(item: tuple[str, dict]) -> tuple[int, str]:
    key = str(item[0])
    if key == "A":
        return (-1, "A")
    if key.isdigit():
        return (0, f"{int(key):04d}")
    return (1, key)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in get_entry_coordinators(hass, config_entry):
        entities.extend(
            [
                SpaCloudConnectivityBinarySensor(coordinator),
                SpaBinarySensor(coordinator, "Heater", SK_HEATER),
                SpaBinarySensor(coordinator, "Sanitise Active", SK_SANITISE),
                SpaBinarySensor(coordinator, "Sleeping", SK_SLEEPING),
            ]
        )

        for key, value in sorted(coordinator.get_state(SK_PUMPS).items(), key=_pump_sort_key):
            entities.append(
                SpaBinarySensor(
                    coordinator,
                    value.get("displayName", f"Pump {key}"),
                    f"{SK_PUMPS}.{key}.state",
                )
            )

    async_add_entities(entities)
    return True


class SpaBinarySensor(SpaEntity, BinarySensorEntity):
    """SpaNET binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator, name: str, status_id: str) -> None:
        super().__init__(coordinator, "binary_sensor", name)
        self._status_id = status_id

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


class SpaCloudConnectivityBinarySensor(SpaEntity, BinarySensorEntity):
    """SpaNET cloud connectivity state."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "binary_sensor", "Cloud Connected")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self):
        return self.coordinator.state.get(SK_CLOUD_CONNECTED)
