import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPANET_DIR = ROOT / "custom_components" / "spanet"


def _install_homeassistant_stubs():
    if "homeassistant" in sys.modules:
        return

    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    components_switch = types.ModuleType("homeassistant.components.switch")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    helpers_entity = types.ModuleType("homeassistant.helpers.entity")
    helpers_entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    helpers_update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class SwitchEntity:
        pass

    class SwitchDeviceClass:
        SWITCH = "switch"

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

    components_switch.SwitchEntity = SwitchEntity
    components_switch.SwitchDeviceClass = SwitchDeviceClass
    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    helpers_entity.DeviceInfo = DeviceInfo
    helpers_entity.EntityCategory = EntityCategory
    helpers_entity_platform.AddEntitiesCallback = object
    helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
    helpers_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    helpers_update_coordinator.UpdateFailed = UpdateFailed

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.switch"] = components_switch
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.entity"] = helpers_entity
    sys.modules["homeassistant.helpers.entity_platform"] = helpers_entity_platform
    sys.modules["homeassistant.helpers.update_coordinator"] = helpers_update_coordinator

    if "async_timeout" not in sys.modules:
        async_timeout = types.ModuleType("async_timeout")

        class _Timeout:
            def __init__(self, _seconds):
                self._seconds = _seconds

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        def timeout(seconds):
            return _Timeout(seconds)

        async_timeout.timeout = timeout
        sys.modules["async_timeout"] = async_timeout


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
    spec = importlib.util.spec_from_file_location(
        module_name,
        SPANET_DIR / filename,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


const = _load("custom_components.spanet.const", "const.py")
_load("custom_components.spanet.scheduler", "scheduler.py")
_load("custom_components.spanet.spanet", "spanet.py")
_load("custom_components.spanet.entity", "entity.py")
coordinator_module = _load("custom_components.spanet.coordinator", "coordinator.py")
switch_module = _load("custom_components.spanet.switch", "switch.py")


class _FakeSpa:
    def __init__(self):
        self.calls = []

    async def set_element_boost(self, on):
        self.calls.append(on)


class _FakeFailSpa:
    def __init__(self, err_cls):
        self.calls = 0
        self._err_cls = err_cls

    async def set_element_boost(self, on):
        self.calls += 1

        class _Resp:
            status = 500

        raise self._err_cls(_Resp(), "boom")


@pytest.mark.asyncio
async def test_element_boost_switch_only_created_when_heat_pump_option_enabled():
    class _Coordinator:
        def __init__(self):
            self.hass = SimpleNamespace()
            self.spa_name = "My Spa"
            self.spa_id = "1"
            self.state = {
                const.SK_PUMPS: {},
                const.SK_SLEEP_TIMERS: {},
                const.SK_ELEMENT_BOOST_SUPPORTED: False,
                const.SK_ELEMENT_BOOST: None,
            }

        def get_state(self, key, sub_key=None):
            obj = self.state
            path = key.split(".")
            if sub_key is not None:
                path.append(sub_key)
            for p in path:
                obj = obj[p]
            return obj

        async def set_lights(self, value):
            return None

        async def set_sanitiser(self, value):
            return None

        async def set_element_boost(self, value):
            return None

    coordinator = _Coordinator()
    hass = SimpleNamespace(
        data={
            const.DOMAIN: {
                "entry-1": {"coordinators": [coordinator]},
            }
        }
    )
    config_entry = SimpleNamespace(entry_id="entry-1", options={})

    created = []

    def _add_entities(entities):
        created.extend(entities)

    await switch_module.async_setup_entry(hass, config_entry, _add_entities)
    assert not any(e for e in created if e._attr_name.endswith("Element Boost"))

    config_entry.options["enable_heat_pump"] = True
    created.clear()
    await switch_module.async_setup_entry(hass, config_entry, _add_entities)

    element = next(e for e in created if e._attr_name.endswith("Element Boost"))
    assert element.entity_id == "switch.myspa_ElementBoost"
    assert element._attr_unique_id == "switch.1_ElementBoost"
    assert element.available is False


@pytest.mark.asyncio
async def test_element_boost_supported_updates_after_success():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    spa = _FakeSpa()
    coordinator.spa = spa
    coordinator.state = {
        const.SK_ELEMENT_BOOST_SUPPORTED: True,
        const.SK_ELEMENT_BOOST: "off",
    }

    await coordinator.set_element_boost("on")

    assert spa.calls == [True]
    assert coordinator.state[const.SK_ELEMENT_BOOST] == "on"


@pytest.mark.asyncio
async def test_element_boost_unsupported_short_circuits():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    spa = _FakeSpa()
    coordinator.spa = spa
    coordinator.state = {
        const.SK_ELEMENT_BOOST_SUPPORTED: False,
        const.SK_ELEMENT_BOOST: None,
    }

    await coordinator.set_element_boost("on")

    assert spa.calls == []
    assert coordinator.state[const.SK_ELEMENT_BOOST] is None


@pytest.mark.asyncio
async def test_element_boost_api_error_does_not_crash_or_update_state():
    err_cls = coordinator_module.SpaNetApiError
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.spa = _FakeFailSpa(err_cls)
    coordinator.state = {
        const.SK_ELEMENT_BOOST_SUPPORTED: True,
        const.SK_ELEMENT_BOOST: "off",
    }

    await coordinator.set_element_boost("on")

    assert coordinator.state[const.SK_ELEMENT_BOOST] == "off"


@pytest.mark.asyncio
async def test_update_information_sets_element_boost_capability_supported_and_unsupported():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.state = {}

    async def _supported():
        return {
            "information": {
                "settingsSummary": {
                    "operationMode": "Normal",
                    "powersaveTimer": {"mode": 1},
                    "hpElementBoost": "1",
                    "sleepTimers": [],
                }
            }
        }

    async def _unsupported():
        return {
            "information": {
                "settingsSummary": {
                    "operationMode": "Normal",
                    "powersaveTimer": {"mode": 1},
                    "sleepTimers": [],
                }
            }
        }

    coordinator.spa = SimpleNamespace(get_information=_supported)
    await coordinator.update_information()
    assert coordinator.state[const.SK_ELEMENT_BOOST_SUPPORTED] is True
    assert coordinator.state[const.SK_ELEMENT_BOOST] == "on"

    coordinator.spa = SimpleNamespace(get_information=_unsupported)
    await coordinator.update_information()
    assert coordinator.state[const.SK_ELEMENT_BOOST_SUPPORTED] is False


@pytest.mark.asyncio
async def test_update_pumps_keeps_runtime_capability_driven_entities():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.state = {}

    async def _get_pumps():
        return {
            "pumpAndBlower": {
                "pumps": [
                    {
                        "id": 11,
                        "pumpNumber": 1,
                        "hasAuto": True,
                        "pumpSpeed": 2,
                        "canSwitchOn": True,
                        "pumpStatus": "auto",
                    },
                    {
                        "id": 12,
                        "pumpNumber": 2,
                        "hasAuto": False,
                        "pumpSpeed": 1,
                        "canSwitchOn": True,
                        "pumpStatus": "off",
                    },
                ],
                "blower": {
                    "id": 13,
                    "blowerStatus": "ramp",
                    "blowerVariableSpeed": 4,
                },
            }
        }

    coordinator.spa = SimpleNamespace(get_pumps=_get_pumps)
    await coordinator.update_pumps()

    assert coordinator.state[const.SK_PUMPS]["1"]["auto"] is True
    assert coordinator.state[const.SK_PUMPS]["1"]["hasSwitch"] is True
    assert coordinator.state[const.SK_PUMPS]["1"]["state"] == "auto"
    assert coordinator.state[const.SK_PUMPS]["2"]["state"] == "off"
    assert coordinator.state[const.SK_BLOWER]["state"] == "ramp"
    assert coordinator.state[const.SK_BLOWER]["speed"] == 4


@pytest.mark.asyncio
async def test_update_pumps_ignores_circulation_pump_and_uses_blower_variable_speed():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.state = {}

    async def _get_pumps():
        return {
            "pumpAndBlower": {
                "pumps": [
                    {
                        "id": 10,
                        "pumpNumber": -1,
                        "hasAuto": True,
                        "pumpSpeed": -1,
                        "isCirc": True,
                        "canSwitchOn": True,
                        "pumpStatus": "auto",
                    },
                    {
                        "id": 12,
                        "pumpNumber": 1,
                        "hasAuto": False,
                        "pumpSpeed": 1,
                        "canSwitchOn": True,
                        "pumpStatus": "off",
                    },
                ],
                "blower": {
                    "id": 13,
                    "blowerStatus": "off",
                    "blowerVariableSpeed": 5,
                },
            }
        }

    coordinator.spa = SimpleNamespace(get_pumps=_get_pumps)
    await coordinator.update_pumps()

    assert "-1" not in coordinator.state[const.SK_PUMPS]
    assert coordinator.state[const.SK_PUMPS]["1"]["state"] == "off"
    assert coordinator.state[const.SK_BLOWER]["speed"] == 5


@pytest.mark.asyncio
async def test_update_pumps_treats_vari_status_as_on():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.state = {}

    async def _get_pumps():
        return {
            "pumpAndBlower": {
                "pumps": [
                    {
                        "id": 12,
                        "pumpNumber": 1,
                        "hasAuto": False,
                        "pumpSpeed": 1,
                        "canSwitchOn": True,
                        "pumpStatus": "vari",
                    }
                ],
                "blower": {},
            }
        }

    coordinator.spa = SimpleNamespace(get_pumps=_get_pumps)
    await coordinator.update_pumps()

    assert coordinator.state[const.SK_PUMPS]["1"]["state"] == "on"


@pytest.mark.asyncio
async def test_update_pumps_models_pump_a_and_pump_one_separately():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.state = {}

    async def _get_pumps():
        return {
            "pumpAndBlower": {
                "pumps": [
                    {
                        "id": 10,
                        "pumpNumber": -1,
                        "hasAuto": True,
                        "pumpSpeed": -1,
                        "isCirc": True,
                        "canSwitchOn": True,
                        "pumpStatus": "auto",
                    },
                    {
                        "id": 11,
                        "pumpNumber": 1,
                        "hasAuto": False,
                        "pumpSpeed": 1,
                        "isCirc": False,
                        "canSwitchOn": True,
                        "pumpStatus": "auto",
                    },
                    {
                        "id": 12,
                        "pumpNumber": 2,
                        "hasAuto": False,
                        "pumpSpeed": 1,
                        "isCirc": False,
                        "canSwitchOn": True,
                        "pumpStatus": "on",
                    },
                ],
                "blower": {},
            }
        }

    coordinator.spa = SimpleNamespace(get_pumps=_get_pumps)
    await coordinator.update_pumps()

    assert coordinator.state[const.SK_PUMPS]["A"]["displayName"] == "Pump A"
    assert coordinator.state[const.SK_PUMPS]["A"]["supportedStates"] == ["off", "auto", "on"]
    assert coordinator.state[const.SK_PUMPS]["A"]["state"] == "auto"

    assert coordinator.state[const.SK_PUMPS]["1"]["supportedStates"] == ["off", "auto", "on"]
    assert coordinator.state[const.SK_PUMPS]["1"]["state"] == "auto"

    assert coordinator.state[const.SK_PUMPS]["2"]["supportedStates"] == ["off", "on"]
    assert coordinator.state[const.SK_PUMPS]["2"]["state"] == "on"


@pytest.mark.asyncio
async def test_update_lights_normalizes_lowercase_animation_modes():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.state = {}

    async def _get_light_details():
        return {
            "lightId": 6156,
            "lightMode": "fade",
            "lightColour": "white",
            "lightBrightness": 4,
            "lightSpeed": 5,
            "lightOn": False,
        }

    coordinator.spa = SimpleNamespace(get_light_details=_get_light_details)
    await coordinator.update_lights()

    assert coordinator.state[const.SK_LIGHTS]["mode"] == "Fade"
    assert coordinator.state[const.SK_LIGHT_PROFILE] == "Animated"
    assert coordinator.state[const.SK_LIGHT_ANIMATION] == "Fade"


@pytest.mark.asyncio
async def test_update_settings_prefers_authoritative_api_mode_endpoints():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={"enable_heat_pump": True}),
    )
    coordinator.state = {}

    coordinator.spa = SimpleNamespace(
        get_filtration=lambda: {"totalRuntime": 3, "inBetweenCycles": 12},
        get_timeout=lambda: 30,
        get_sanitise_time=lambda: "08:30",
        get_power_save=lambda: {"mode": 2},
        get_operation_mode=lambda: 3,
        get_heat_pump=lambda: {"mode": 4},
    )

    async def _awaitable(value):
        return value

    coordinator.spa = SimpleNamespace(
        get_filtration=lambda: _awaitable({"totalRuntime": 3, "inBetweenCycles": 12}),
        get_timeout=lambda: _awaitable(30),
        get_sanitise_time=lambda: _awaitable("08:30"),
        get_power_save=lambda: _awaitable({"mode": 2}),
        get_operation_mode=lambda: _awaitable(3),
        get_heat_pump=lambda: _awaitable({"mode": 4}),
    )

    await coordinator.update_settings()

    assert coordinator.state[const.SK_FILTRATION_RUNTIME] == 3
    assert coordinator.state[const.SK_FILTRATION_CYCLE] == 12
    assert coordinator.state[const.SK_POWER_SAVE] == "Low"
    assert coordinator.state[const.SK_OPERATION_MODE] == "Away"
    assert coordinator.state[const.SK_HEAT_PUMP] == "Off"
