"""SpaNET selects."""

from __future__ import annotations

from functools import partial

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api_mappings import (
    HEAT_PUMP_OPTIONS,
    OPERATION_MODE_OPTIONS,
    PUMP_SELECT_OPTIONS,
    POWER_SAVE_OPTIONS,
)
from .const import (
    DOMAIN,
    OPT_ENABLE_HEAT_PUMP,
    SLEEP_TIMER_DAY_PROFILES,
    SK_FILTRATION_CYCLE,
    SK_FILTRATION_RUNTIME,
    SK_HEAT_PUMP,
    SK_OPERATION_MODE,
    SK_POWER_SAVE,
    SK_PUMPS,
    SK_SLEEP_TIMERS,
    SK_TIMEOUT,
)
from .entity import SpaEntity

FILTRATION_CYCLE_OPTIONS = [str(value) for value in range(1, 25)]
FILTRATION_RUNTIME_OPTIONS = [str(value) for value in (1, 2, 3, 4, 6, 8, 12, 24)]
TIMEOUT_OPTIONS = [str(value) for value in range(1, 61)]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities.append(
            SpaSelect(
                coordinator,
                "Operation Mode",
                SK_OPERATION_MODE,
                OPERATION_MODE_OPTIONS,
                coordinator.set_operation_mode,
                entity_category=EntityCategory.CONFIG,
            )
        )
        entities.append(
            SpaSelect(
                coordinator,
                "Power Save",
                SK_POWER_SAVE,
                POWER_SAVE_OPTIONS,
                coordinator.set_power_save,
                entity_category=EntityCategory.CONFIG,
            )
        )
        entities.append(
            SpaNumericSelect(
                coordinator,
                "Filtration Cycle Gap",
                SK_FILTRATION_CYCLE,
                FILTRATION_CYCLE_OPTIONS,
                coordinator.set_filtration_cycle,
                entity_category=EntityCategory.CONFIG,
            )
        )
        entities.append(
            SpaNumericSelect(
                coordinator,
                "Filtration Runtime",
                SK_FILTRATION_RUNTIME,
                FILTRATION_RUNTIME_OPTIONS,
                coordinator.set_filtration_runtime,
                entity_category=EntityCategory.CONFIG,
            )
        )
        entities.append(
            SpaNumericSelect(
                coordinator,
                "Timeout",
                SK_TIMEOUT,
                TIMEOUT_OPTIONS,
                coordinator.set_timeout,
                entity_category=EntityCategory.CONFIG,
            )
        )

        if config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            entities.append(
                SpaSelect(
                    coordinator,
                    "Heat Pump",
                    SK_HEAT_PUMP,
                    HEAT_PUMP_OPTIONS,
                    coordinator.set_heat_pump,
                    entity_category=EntityCategory.CONFIG,
                )
            )

        for k, v in sorted(coordinator.state.get(SK_PUMPS, {}).items()):
            if v.get("hasSwitch", False) and v.get("auto", False):
                entities.append(
                    SpaSelect(
                        coordinator,
                        v.get("displayName", f"Pump {k}"),
                        f"{SK_PUMPS}.{k}.state",
                        v.get("supportedStates", PUMP_SELECT_OPTIONS),
                        partial(coordinator.set_pump, k),
                    )
                )

        for k, _ in coordinator.state.get(SK_SLEEP_TIMERS, {}).items():
            entities.append(
                SpaSelect(
                    coordinator,
                    f"Sleep Timer {k} Days",
                    f"{SK_SLEEP_TIMERS}.{k}.dayProfile",
                    [*list(SLEEP_TIMER_DAY_PROFILES.keys()), "Custom"],
                    partial(coordinator.set_sleep_timer_day_profile, k),
                    entity_category=EntityCategory.CONFIG,
                )
            )

    async_add_entity(entities)
    return True


class SpaSelect(SpaEntity, SelectEntity):
    """A selector."""

    def __init__(
        self,
        coordinator,
        name,
        state_key,
        options,
        setter,
        entity_category: EntityCategory | None = None,
        availability_callback=None,
    ) -> None:
        super().__init__(coordinator, "select", name)
        self.hass = coordinator.hass
        self._state_key = state_key
        self._options = options
        self._setter = setter
        self._attr_entity_category = entity_category
        self._availability_callback = availability_callback

    @property
    def available(self) -> bool:
        if self._availability_callback is None:
            return True
        return bool(self._availability_callback(self.coordinator))

    @property
    def current_option(self):
        value = self.coordinator.get_state(self._state_key)
        if value in self._options:
            return value
        return None

    @property
    def options(self):
        return self._options

    async def async_select_option(self, option):
        await self._setter(option)


class SpaNumericSelect(SpaSelect):
    """Select entity backed by an integer coordinator state."""

    @property
    def current_option(self):
        value = self.coordinator.get_state(self._state_key)
        if value is None:
            return None
        option = str(int(value))
        if option in self._options:
            return option
        return None

    async def async_select_option(self, option):
        await self._setter(int(option))
