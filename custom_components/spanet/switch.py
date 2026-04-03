"""SpaNET switches."""

from __future__ import annotations

from functools import partial

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SK_BLOWER,
    SK_ELEMENT_BOOST,
    SK_ELEMENT_BOOST_SUPPORTED,
    SK_LIGHTS,
    SK_LOCK_MODE,
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
                        device_suffix="controls",
                        device_name=f"{coordinator.spa_name} Controls",
                    )
                )

        entities.append(
            SpaSwitch(
                coordinator,
                "Lights",
                f"{SK_LIGHTS}.state",
                coordinator.set_lights,
                device_suffix="lights",
                device_name=f"{coordinator.spa_name} Lights",
            )
        )

        if SK_BLOWER in coordinator.state:
            entities.append(
                SpaSwitch(
                    coordinator,
                    "Blower",
                    f"{SK_BLOWER}.state",
                    coordinator.set_blower,
                    device_suffix="controls",
                    device_name=f"{coordinator.spa_name} Controls",
                )
            )

        if SK_SANITISE_STATUS in coordinator.state:
            entities.append(
                SpaSwitch(
                    coordinator,
                    "Sanitise Status",
                    SK_SANITISE_STATUS,
                    coordinator.set_sanitiser,
                    entity_category=EntityCategory.CONFIG,
                )
            )

        if SK_LOCK_MODE in coordinator.state:
            entities.append(
                SpaSwitch(
                    coordinator,
                    "Lock Mode",
                    SK_LOCK_MODE,
                    coordinator.set_lock_mode_switch,
                    entity_category=EntityCategory.CONFIG,
                    device_suffix="system",
                    device_name=f"{coordinator.spa_name} System",
                )
            )

        for k, _ in coordinator.get_state(SK_SLEEP_TIMERS).items():
            entities.append(
                SpaSwitch(
                    coordinator,
                    f"Sleep Timer {k}",
                    f"{SK_SLEEP_TIMERS}.{k}.state",
                    partial(coordinator.set_sleep_timer, k),
                    entity_category=EntityCategory.CONFIG,
                )
            )

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

    def __init__(self, coordinator, name, state_key, switch_callback, availability_key: str | None = None, entity_category: EntityCategory | None = None, device_suffix: str | None = None, device_name: str | None = None) -> None:
        super().__init__(
            coordinator,
            "switch",
            name,
            device_suffix=device_suffix,
            device_name=device_name,
        )
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
