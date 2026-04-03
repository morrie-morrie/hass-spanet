"""SpaNET selects."""

from __future__ import annotations

from functools import partial

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HEAT_PUMP,
    OPERATION_MODES,
    OPT_ENABLE_HEAT_PUMP,
    POWER_SAVE,
    SLEEP_TIMER_DAY_PROFILES,
    SK_BLOWER,
    SK_HEAT_PUMP,
    SK_OPERATION_MODE,
    SK_POWER_SAVE,
    SK_PUMPS,
    SK_SLEEP_TIMERS,
)
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    pump_options = ["off", "auto", "low", "high"]
    blower_options = ["off", "on", "auto", "low", "high"]
    entities = []

    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities.append(
            SpaSelect(
                coordinator,
                "Operation Mode",
                SK_OPERATION_MODE,
                OPERATION_MODES[1:],
                coordinator.set_operation_mode,
                entity_category=EntityCategory.CONFIG,
            )
        )
        entities.append(
            SpaSelect(
                coordinator,
                "Power Save",
                SK_POWER_SAVE,
                POWER_SAVE[1:],
                coordinator.set_power_save,
                entity_category=EntityCategory.CONFIG,
            )
        )

        if config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            entities.append(
                SpaSelect(
                    coordinator,
                    "Heat Pump",
                    SK_HEAT_PUMP,
                    HEAT_PUMP,
                    coordinator.set_heat_pump,
                    entity_category=EntityCategory.CONFIG,
                )
            )

        if SK_BLOWER in coordinator.state:
            entities.append(
                SpaSelect(
                    coordinator,
                    "Blower Mode",
                    f"{SK_BLOWER}.state",
                    blower_options,
                    coordinator.set_blower,
                )
            )

        for k, v in coordinator.get_state(SK_PUMPS).items():
            if v["hasSwitch"] and v["speeds"] > 1:
                entities.append(
                    SpaSelect(
                        coordinator,
                        f"Pump {k}",
                        f"{SK_PUMPS}.{k}.state",
                        pump_options,
                        partial(coordinator.set_pump, k),
                    )
                )

        for k, _ in coordinator.get_state(SK_SLEEP_TIMERS).items():
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
    ) -> None:
        super().__init__(coordinator, "select", name)
        self.hass = coordinator.hass
        self._state_key = state_key
        self._options = options
        self._setter = setter
        self._attr_entity_category = entity_category

    @property
    def current_option(self):
        return self.coordinator.get_state(self._state_key)

    @property
    def options(self):
        return self._options

    async def async_select_option(self, option):
        await self._setter(option)
