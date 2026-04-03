"""SpaNET switches."""

from __future__ import annotations

from functools import partial

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    OPT_ENABLE_HEAT_PUMP,
    SK_BLOWER,
    SK_ELEMENT_BOOST,
    SK_LIGHTS,
    SK_OXY,
    SK_PUMPS,
    SK_SANITISE_STATUS,
    SK_SLEEP_TIMERS,
)
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []

    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        for k, v in coordinator.get_state(SK_PUMPS).items():
            if v["hasSwitch"] and v["speeds"] == 1:
                entities.append(
                    SpaSwitch(
                        coordinator,
                        f"Pump {k}",
                        f"{SK_PUMPS}.{k}.state",
                        partial(coordinator.set_pump, k),
                    )
                )

        entities.append(SpaSwitch(coordinator, "Lights", f"{SK_LIGHTS}.state", coordinator.set_lights))

        if SK_OXY in coordinator.state:
            entities.append(SpaSwitch(coordinator, "Oxy", SK_OXY, coordinator.set_oxy))

        if SK_BLOWER in coordinator.state:
            entities.append(
                SpaSwitch(
                    coordinator,
                    "Blower",
                    f"{SK_BLOWER}.state",
                    coordinator.set_blower,
                )
            )

        entities.append(
            SpaSwitch(
                coordinator,
                "Sanitise Status",
                SK_SANITISE_STATUS,
                coordinator.set_sanitiser,
            )
        )

        for k, _ in coordinator.get_state(SK_SLEEP_TIMERS).items():
            entities.append(
                SpaSwitch(
                    coordinator,
                    f"Sleep Timer {k}",
                    f"{SK_SLEEP_TIMERS}.{k}.state",
                    partial(coordinator.set_sleep_timer, k),
                )
            )

        if config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            entities.append(
                SpaSwitch(
                    coordinator,
                    "Element Boost",
                    SK_ELEMENT_BOOST,
                    coordinator.set_element_boost,
                )
            )

    async_add_entity(entities)
    return True


class SpaSwitch(SpaEntity, SwitchEntity):
    """A switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, name, state_key, switch_callback) -> None:
        super().__init__(coordinator, "switch", name)
        self.hass = coordinator.hass
        self._state_key = state_key
        self._switch_callback = switch_callback

    @property
    def is_on(self):
        value = self.coordinator.get_state(self._state_key)
        if value is None:
            return None
        if value in {"on", "auto", "high", "low"}:
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
