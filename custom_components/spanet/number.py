"""SpaNET number entities."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SK_FILTRATION_CYCLE,
    SK_FILTRATION_RUNTIME,
    SK_TIMEOUT,
)
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities.extend(
            [
                SpaNumber(
                    coordinator,
                    "Filtration Runtime",
                    SK_FILTRATION_RUNTIME,
                    coordinator.set_filtration_runtime,
                    minimum=0,
                    maximum=1440,
                    step=1,
                    native_unit=UnitOfTime.MINUTES,
                    entity_category=EntityCategory.CONFIG,
                    mode=NumberMode.BOX,
                ),
                SpaNumber(
                    coordinator,
                    "Filtration Cycle Gap",
                    SK_FILTRATION_CYCLE,
                    coordinator.set_filtration_cycle,
                    minimum=0,
                    maximum=1440,
                    step=1,
                    native_unit=UnitOfTime.MINUTES,
                    entity_category=EntityCategory.CONFIG,
                    mode=NumberMode.BOX,
                ),
                SpaNumber(
                    coordinator,
                    "Timeout",
                    SK_TIMEOUT,
                    coordinator.set_timeout,
                    minimum=0,
                    maximum=240,
                    step=1,
                    native_unit=UnitOfTime.MINUTES,
                    entity_category=EntityCategory.CONFIG,
                    mode=NumberMode.BOX,
                ),
            ]
        )

    async_add_entity(entities)
    return True


class SpaNumber(SpaEntity, NumberEntity):
    """A numeric setting entity."""

    def __init__(
        self,
        coordinator,
        name: str,
        state_key: str,
        setter,
        minimum: float,
        maximum: float,
        step: float,
        native_unit: str | None = None,
        entity_category: EntityCategory | None = None,
        mode: NumberMode | None = None,
        availability_callback=None,
    ):
        super().__init__(coordinator, "number", name)
        self._state_key = state_key
        self._setter = setter
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = native_unit
        self._attr_entity_category = entity_category
        self._attr_mode = mode or NumberMode.SLIDER
        self._availability_callback = availability_callback

    @property
    def available(self) -> bool:
        if self._availability_callback is None:
            return True
        return bool(self._availability_callback(self.coordinator))

    @property
    def native_value(self):
        value = self.coordinator.get_state(self._state_key)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self._setter(int(value))
