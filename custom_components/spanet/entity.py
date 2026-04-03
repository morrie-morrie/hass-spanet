"""SpaNet Sensors"""
from __future__ import annotations
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class SpaEntity(CoordinatorEntity):
    def __init__(
        self,
        coordinator,
        entity_type,
        name,
        device_suffix: str | None = None,
        device_name: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.hass = coordinator.hass

        self.entity_id = f"{entity_type}.{self._build_entity_id(coordinator.spa_name.lower() + '_' + name)}"
        self._attr_unique_id = (
            f"{entity_type}.{self._build_entity_id(coordinator.spa_id + '_' + name)}"
        )
        self._attr_name = f"{coordinator.spa_name} {name}"

        device_id = self.coordinator.spa_id
        identifiers = {(DOMAIN, device_id)}
        if device_suffix:
            identifiers = {(DOMAIN, f"{device_id}_{device_suffix}")}

        self._attr_device_info = DeviceInfo(
            identifiers=identifiers,
            name=device_name,
        )

    def _build_entity_id(self, name):
        entity_id = ""
        for char in name:
            if char.isalnum() or char == "_":
                entity_id += char
        return entity_id
