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
    components_binary_sensor = sys.modules.setdefault(
        "homeassistant.components.binary_sensor",
        types.ModuleType("homeassistant.components.binary_sensor"),
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

    class BinarySensorEntity:
        pass

    class BinarySensorDeviceClass:
        RUNNING = "running"
        CONNECTIVITY = "connectivity"

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

    class EntityCategory:
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    components_binary_sensor.BinarySensorEntity = BinarySensorEntity
    components_binary_sensor.BinarySensorDeviceClass = BinarySensorDeviceClass
    components_sensor.SensorEntity = SensorEntity
    components_sensor.SensorDeviceClass = SensorDeviceClass
    config_entries.ConfigEntry = ConfigEntry
    const_module.UnitOfTemperature = SimpleNamespace(CELSIUS="C")
    core.HomeAssistant = HomeAssistant
    helpers_entity.DeviceInfo = DeviceInfo
    helpers_entity.EntityCategory = EntityCategory
    helpers_entity_platform.AddEntitiesCallback = object
    helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
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
binary_sensor_module = _load("custom_components.spanet.binary_sensor", "binary_sensor.py")


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


@pytest.mark.asyncio
async def test_pump_binary_sensors_created_for_switch_pumps():
    coordinator = _Coordinator(
        {
            const.SK_WATERTEMP: 325,
            const.SK_SETTEMP: 330,
            const.SK_HEATER: 0,
            const.SK_SANITISE: 0,
            const.SK_SLEEPING: 0,
            const.SK_PUMPS: {
                "1": {"hasSwitch": True, "state": "auto"},
                "2": {"hasSwitch": True, "state": "off"},
            },
        }
    )
    hass = SimpleNamespace(data={const.DOMAIN: {"entry-1": {"coordinators": [coordinator]}}})
    config_entry = SimpleNamespace(entry_id="entry-1", options={})

    created = []
    await binary_sensor_module.async_setup_entry(hass, config_entry, created.extend)

    cloud = next(entity for entity in created if entity._attr_name == "Cloud Connected")
    assert cloud.is_on is None

    sanitise = next(entity for entity in created if entity._attr_name == "Sanitise Active")
    assert sanitise.is_on is False

    pump_entities = [entity for entity in created if entity._attr_name.startswith("Pump")]
    assert [entity._attr_name for entity in pump_entities] == ["Pump 1", "Pump 2"]
    assert all(entity.entity_id.startswith("binary_sensor.") for entity in pump_entities)

    pump_1 = next(entity for entity in pump_entities if entity._attr_name == "Pump 1")
    pump_2 = next(entity for entity in pump_entities if entity._attr_name == "Pump 2")
    assert pump_1.is_on is False
    assert pump_2.is_on is False
