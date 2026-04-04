"""SpaNET switches."""

from __future__ import annotations

from functools import partial

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    OPT_ENABLE_HEAT_PUMP,
    SK_ELEMENT_BOOST,
    SK_ELEMENT_BOOST_SUPPORTED,
    SK_PUMPS,
    SK_SLEEP_TIMERS,
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
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in get_entry_coordinators(hass, config_entry):
        for k, v in sorted(coordinator.state.get(SK_PUMPS, {}).items(), key=_pump_sort_key):
            if v.get("hasSwitch", False) and not v.get("auto", False):
                entities.append(
                    SpaSwitch(
                        coordinator,
                        v.get("displayName", f"Pump {k}"),
                        f"{SK_PUMPS}.{k}.state",
                        partial(coordinator.set_pump, k),
                    )
                )

        for k, _ in coordinator.state.get(SK_SLEEP_TIMERS, {}).items():
            entities.append(
                SpaSwitch(
                    coordinator,
                    f"Sleep Timer {k}",
                    f"{SK_SLEEP_TIMERS}.{k}.state",
                    partial(coordinator.set_sleep_timer, k),
                    entity_category=EntityCategory.CONFIG,
                )
            )

        if config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            entities.append(
                SpaSwitch(
                    coordinator,
                    "Element Boost",
                    SK_ELEMENT_BOOST,
                    coordinator.set_element_boost,
                    availability_key=SK_ELEMENT_BOOST_SUPPORTED,
                    entity_category=EntityCategory.CONFIG,
                )
            )

    async_add_entity(entities)
    return True


class SpaSwitch(SpaEntity, SwitchEntity):
    """A switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, name, state_key, switch_callback, availability_key: str | None = None, entity_category: EntityCategory | None = None) -> None:
        super().__init__(coordinator, "switch", name)
        self.hass = coordinator.hass
        self._state_key = state_key
        self._switch_callback = switch_callback
        self._availability_key = availability_key
        self._attr_entity_category = entity_category

    @property
    def available(self) -> bool:
        if self._availability_key is None:
            return True
        return bool(self.coordinator.state.get(self._availability_key, False))

    @property
    def is_on(self):
        try:
            value = self.coordinator.get_state(self._state_key)
        except Exception:
            return None
        if value is None:
            return None
        if value in {"on", "auto", "high", "low", "ramp", "variable"}:
            return True
        if value == "off":
            return False
        return int(value) == 1

    async def async_turn_on(self, **kwargs):
        await self._switch_callback("on")

    async def async_turn_off(self, **kwargs):
        await self._switch_callback("off")

    def entity_default_value(self):
        return False
