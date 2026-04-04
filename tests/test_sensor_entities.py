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
    components_sensor = sys.modules.setdefault(
        "homeassistant.components.sensor", types.ModuleType("homeassistant.components.sensor")
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

    class SensorEntity:
        pass

    class SensorDeviceClass:
        TEMPERATURE = "temperature"

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

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    components_sensor.SensorEntity = SensorEntity
    components_sensor.SensorDeviceClass = SensorDeviceClass
    config_entries.ConfigEntry = ConfigEntry
    const_module.UnitOfTemperature = SimpleNamespace(CELSIUS="C")
    core.HomeAssistant = HomeAssistant
    helpers_entity.DeviceInfo = DeviceInfo
    helpers_entity_platform.AddEntitiesCallback = object
    helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
    components.__path__ = getattr(components, "__path__", [])
    helpers.__path__ = getattr(helpers, "__path__", [])


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
sensor_module = _load("custom_components.spanet.sensor", "sensor.py")


class _Coordinator:
    def __init__(self):
        self.hass = SimpleNamespace()
        self.spa_name = "Morison Spa"
        self.spa_id = "1"
        self.state = {
            const.SK_WATERTEMP: 325,
            const.SK_SETTEMP: 330,
            const.SK_PUMPS: {
                "A": {"state": "auto", "displayName": "Pump A"},
                "1": {"state": "off", "displayName": "Pump 1"},
            },
        }

    def get_state(self, key, sub_key=None):
        obj = self.state
        path = key.split(".")
        if sub_key is not None:
            path.append(sub_key)
        for p in path:
            obj = obj[p]
        return obj


@pytest.mark.asyncio
async def test_sensor_entities_include_pump_a_mode():
    coordinator = _Coordinator()
    hass = SimpleNamespace(data={const.DOMAIN: {"entry-1": {"coordinators": [coordinator]}}})
    config_entry = SimpleNamespace(entry_id="entry-1", options={})

    created = []
    await sensor_module.async_setup_entry(hass, config_entry, created.extend)

    by_name = {entity._attr_name: entity for entity in created}
    assert by_name["Water Temperature"].native_value == 32.5
    assert by_name["Set Temperature"].native_value == 33.0
    assert by_name["Pump A Mode"].native_value == "auto"
