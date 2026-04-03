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
    components_number = sys.modules.setdefault(
        "homeassistant.components.number", types.ModuleType("homeassistant.components.number")
    )
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
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

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    components_select.SelectEntity = SelectEntity
    components_number.NumberEntity = NumberEntity
    components_number.NumberMode = NumberMode
    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    helpers_entity.DeviceInfo = DeviceInfo
    helpers_entity.EntityCategory = EntityCategory
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
select_module = _load("custom_components.spanet.select", "select.py")
number_module = _load("custom_components.spanet.number", "number.py")


class _Coordinator:
    def __init__(self):
        self.hass = SimpleNamespace()
        self.spa_name = "Morison Spa"
        self.spa_id = "1"
        self.state = {
            const.SK_OPERATION_MODE: "Normal",
            const.SK_POWER_SAVE: "High",
            const.SK_FILTRATION_CYCLE: 12,
            const.SK_FILTRATION_RUNTIME: 3,
            const.SK_TIMEOUT: 20,
            const.SK_SLEEP_TIMERS: {},
        }

    def get_state(self, key, sub_key=None):
        obj = self.state
        path = key.split(".")
        if sub_key is not None:
            path.append(sub_key)
        for p in path:
            obj = obj[p]
        return obj

    async def set_operation_mode(self, _value):
        return None

    async def set_power_save(self, _value):
        return None

    async def set_filtration_cycle(self, _value):
        return None

    async def set_filtration_runtime(self, _value):
        return None

    async def set_timeout(self, _value):
        return None


@pytest.mark.asyncio
async def test_configuration_values_are_selects_not_numbers():
    coordinator = _Coordinator()
    hass = SimpleNamespace(data={const.DOMAIN: {"entry-1": {"coordinators": [coordinator]}}})
    config_entry = SimpleNamespace(entry_id="entry-1", options={})

    created_selects = []
    created_numbers = []

    await select_module.async_setup_entry(hass, config_entry, created_selects.extend)
    await number_module.async_setup_entry(hass, config_entry, created_numbers.extend)

    assert created_numbers == []

    by_name = {entity._attr_name: entity for entity in created_selects}
    assert by_name["Filtration Cycle Gap"].options == [str(value) for value in range(1, 25)]
    assert by_name["Filtration Runtime"].options == ["1", "2", "3", "4", "6", "8", "12", "24"]
    assert by_name["Timeout"].options == [str(value) for value in range(1, 61)]
    assert by_name["Filtration Cycle Gap"].current_option == "12"
    assert by_name["Filtration Runtime"].current_option == "3"
    assert by_name["Timeout"].current_option == "20"
