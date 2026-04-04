import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPANET_DIR = ROOT / "custom_components" / "spanet"


def _install_homeassistant_stubs():
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    components = sys.modules.setdefault(
        "homeassistant.components", types.ModuleType("homeassistant.components")
    )
    components_select = sys.modules.setdefault(
        "homeassistant.components.select", types.ModuleType("homeassistant.components.select")
    )
    components_switch = sys.modules.setdefault(
        "homeassistant.components.switch", types.ModuleType("homeassistant.components.switch")
    )
    components_number = sys.modules.setdefault(
        "homeassistant.components.number", types.ModuleType("homeassistant.components.number")
    )
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
    )
    const_module = sys.modules.setdefault(
        "homeassistant.const", types.ModuleType("homeassistant.const")
    )
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    helpers = sys.modules.setdefault(
        "homeassistant.helpers", types.ModuleType("homeassistant.helpers")
    )
    helpers_entity = sys.modules.setdefault(
        "homeassistant.helpers.entity", types.ModuleType("homeassistant.helpers.entity")
    )
    helpers_entity_platform = sys.modules.setdefault(
        "homeassistant.helpers.entity_platform",
        types.ModuleType("homeassistant.helpers.entity_platform"),
    )
    helpers_update_coordinator = sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator",
        types.ModuleType("homeassistant.helpers.update_coordinator"),
    )

    class SelectEntity:
        pass

    class SwitchEntity:
        pass

    class SwitchDeviceClass:
        SWITCH = "switch"

    class NumberEntity:
        pass

    class NumberMode:
        SLIDER = "slider"
        BOX = "box"

    class ConfigEntry:
        def __init__(self, entry_id="entry-1", options=None):
            self.entry_id = entry_id
            self.options = options or {}

    class HomeAssistant:
        def __init__(self):
            self.data = {}

    class DeviceInfo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class EntityCategory:
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class DataUpdateCoordinator:
        def __init__(self, hass, logger, name=None, update_interval=None):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval

        async def async_request_refresh(self):
            return None

        async def async_config_entry_first_refresh(self):
            return None

    class UpdateFailed(Exception):
        pass

    components_select.SelectEntity = SelectEntity
    components_switch.SwitchEntity = SwitchEntity
    components_switch.SwitchDeviceClass = SwitchDeviceClass
    components_number.NumberEntity = NumberEntity
    components_number.NumberMode = NumberMode
    config_entries.ConfigEntry = ConfigEntry
    const_module.UnitOfTime = SimpleNamespace(MINUTES="min")
    core.HomeAssistant = HomeAssistant
    helpers_entity.DeviceInfo = DeviceInfo
    helpers_entity.EntityCategory = EntityCategory
    helpers_entity_platform.AddEntitiesCallback = object
    helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
    helpers_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    helpers_update_coordinator.UpdateFailed = UpdateFailed

    components.__path__ = getattr(components, "__path__", [])


def _ensure_package():
    if "custom_components" not in sys.modules:
        pkg = types.ModuleType("custom_components")
        pkg.__path__ = [str(ROOT / "custom_components")]
        sys.modules["custom_components"] = pkg
    if "custom_components.spanet" not in sys.modules:
        pkg = types.ModuleType("custom_components.spanet")
        pkg.__path__ = [str(SPANET_DIR)]
        sys.modules["custom_components.spanet"] = pkg


def _load(module_name: str, filename: str):
    _install_homeassistant_stubs()
    _ensure_package()
    spec = importlib.util.spec_from_file_location(module_name, SPANET_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


const = _load("custom_components.spanet.const", "const.py")
_load("custom_components.spanet.entity", "entity.py")
select_module = _load("custom_components.spanet.select", "select.py")
switch_module = _load("custom_components.spanet.switch", "switch.py")
number_module = _load("custom_components.spanet.number", "number.py")


class _Coordinator:
    def __init__(self, state):
        self.hass = SimpleNamespace()
        self.spa_name = "Morison Spa"
        self.spa_id = "1"
        self.state = state

    def get_state(self, key, sub_key=None):
        obj = self.state
        path = key.split(".")
        if sub_key is not None:
            path.append(sub_key)
        for p in path:
            obj = obj[p]
        return obj

    async def set_pump(self, _key, _value):
        return None

    async def set_blower(self, _value):
        return None

    async def set_blower_switch(self, _value):
        return None

    async def set_blower_speed(self, _value):
        return None

    async def set_light_profile(self, _value):
        return None

    async def set_light_animation(self, _value):
        return None

    async def set_operation_mode(self, _value):
        return None

    async def set_power_save(self, _value):
        return None

    async def set_heat_pump(self, _value):
        return None

    async def set_sleep_timer_day_profile(self, _key, _value):
        return None

    async def set_lights(self, _value):
        return None

    async def set_sanitiser(self, _value):
        return None

    async def set_lock_mode_switch(self, _value):
        return None

    async def set_sleep_timer(self, _key, _value):
        return None

    async def set_element_boost(self, _value):
        return None

    async def set_light_brightness(self, _value):
        return None

    async def set_light_speed(self, _value):
        return None

    async def set_filtration_runtime(self, _value):
        return None

    async def set_filtration_cycle(self, _value):
        return None

    async def set_timeout(self, _value):
        return None


def _hass_and_entry(coordinator, options=None):
    hass = SimpleNamespace(
        data={const.DOMAIN: {"entry-1": {"coordinators": [coordinator]}}}
    )
    config_entry = SimpleNamespace(entry_id="entry-1", options=options or {})
    return hass, config_entry


@pytest.mark.asyncio
async def test_pump_entities_follow_capabilities_without_duplicates():
    coordinator = _Coordinator(
        {
            const.SK_PUMPS: {
                "A": {
                    "hasSwitch": True,
                    "auto": True,
                    "speeds": -1,
                    "state": "auto",
                    "displayName": "Pump A",
                    "supportedStates": ["off", "auto", "on"],
                },
                "1": {"hasSwitch": True, "auto": False, "speeds": 1, "state": "off", "displayName": "Pump 1"},
                "2": {"hasSwitch": True, "auto": False, "speeds": 1, "state": "off", "displayName": "Pump 2"},
            },
            const.SK_SLEEP_TIMERS: {},
            const.SK_FILTRATION_RUNTIME: 0,
            const.SK_FILTRATION_CYCLE: 0,
            const.SK_TIMEOUT: 0,
        }
    )
    hass, config_entry = _hass_and_entry(coordinator)

    created_selects = []
    created_switches = []

    await select_module.async_setup_entry(hass, config_entry, created_selects.extend)
    await switch_module.async_setup_entry(hass, config_entry, created_switches.extend)

    pump_selects = [entity for entity in created_selects if entity._attr_name.startswith("Pump")]
    pump_switches = [entity for entity in created_switches if entity._attr_name.startswith("Pump")]

    assert [entity._attr_name for entity in pump_selects] == ["Pump A"]
    assert pump_selects[0].options == ["off", "auto", "on"]
    assert [entity._attr_name for entity in pump_switches] == ["Pump 1", "Pump 2"]


@pytest.mark.asyncio
async def test_pump_a_is_a_select_when_auto_supported():
    coordinator = _Coordinator(
        {
            const.SK_PUMPS: {
                "A": {
                    "hasSwitch": True,
                    "auto": True,
                    "speeds": -1,
                    "state": "auto",
                    "displayName": "Pump A",
                    "supportedStates": ["off", "auto", "on"],
                },
            },
            const.SK_SLEEP_TIMERS: {},
            const.SK_FILTRATION_RUNTIME: 0,
            const.SK_FILTRATION_CYCLE: 0,
            const.SK_TIMEOUT: 0,
        }
    )
    hass, config_entry = _hass_and_entry(coordinator)

    created_selects = []
    created_switches = []

    await select_module.async_setup_entry(hass, config_entry, created_selects.extend)
    await switch_module.async_setup_entry(hass, config_entry, created_switches.extend)

    assert not any(entity._attr_name == "Pump A" for entity in created_switches)
    pump_a = next(entity for entity in created_selects if entity._attr_name == "Pump A")
    assert pump_a.current_option == "auto"


@pytest.mark.asyncio
async def test_blower_is_switch_only():
    coordinator = _Coordinator(
        {
            const.SK_PUMPS: {},
            const.SK_SLEEP_TIMERS: {},
            const.SK_FILTRATION_RUNTIME: 0,
            const.SK_FILTRATION_CYCLE: 0,
            const.SK_TIMEOUT: 0,
            const.SK_BLOWER: {"state": "ramp", "speed": 3},
        }
    )
    hass, config_entry = _hass_and_entry(coordinator)

    created_numbers = []
    created_selects = []
    created_switches = []

    await number_module.async_setup_entry(hass, config_entry, created_numbers.extend)
    await select_module.async_setup_entry(hass, config_entry, created_selects.extend)
    await switch_module.async_setup_entry(hass, config_entry, created_switches.extend)

    blower_select = next(entity for entity in created_selects if entity._attr_name == "Blower Mode")
    assert blower_select.options == ["off", "ramp", "variable"]
    assert blower_select.current_option == "ramp"
    assert not any(entity._attr_name == "Blower" for entity in created_switches)

    blower_speed = next(
        entity for entity in created_numbers if entity._attr_name == "Blower Variable Speed"
    )
    assert blower_speed.available is False
    assert blower_speed.extra_state_attributes == {"active_when_mode": "variable"}
    assert getattr(blower_speed, "_attr_entity_category", None) is None


@pytest.mark.asyncio
async def test_blower_speed_available_only_in_variable_mode():
    coordinator = _Coordinator(
        {
            const.SK_PUMPS: {},
            const.SK_SLEEP_TIMERS: {},
            const.SK_FILTRATION_RUNTIME: 0,
            const.SK_FILTRATION_CYCLE: 0,
            const.SK_TIMEOUT: 0,
            const.SK_BLOWER: {"state": "variable", "speed": 5},
        }
    )
    hass, config_entry = _hass_and_entry(coordinator)

    created_numbers = []
    await number_module.async_setup_entry(hass, config_entry, created_numbers.extend)

    blower_speed = next(
        entity for entity in created_numbers if entity._attr_name == "Blower Variable Speed"
    )
    assert blower_speed.available is True
    assert blower_speed.native_value == 5
    assert getattr(blower_speed, "_attr_entity_category", None) is None
