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
    components_button = sys.modules.setdefault(
        "homeassistant.components.button", types.ModuleType("homeassistant.components.button")
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

    class ButtonEntity:
        pass

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

    components_button.ButtonEntity = ButtonEntity
    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    helpers_entity.DeviceInfo = DeviceInfo
    helpers_entity.EntityCategory = EntityCategory
    helpers_entity_platform.AddEntitiesCallback = object
    helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
    components.__path__ = getattr(components, "__path__", [])
    helpers.__path__ = getattr(helpers, "__path__", [])

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
    spec = importlib.util.spec_from_file_location(module_name, SPANET_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


const = _load("custom_components.spanet.const", "const.py")
_load("custom_components.spanet.entity", "entity.py")
button_module = _load("custom_components.spanet.button", "button.py")
coordinator_module = _load("custom_components.spanet.coordinator", "coordinator.py")


@pytest.mark.asyncio
async def test_sanitise_button_created_without_status_gate():
    class _Coordinator:
        def __init__(self):
            self.hass = SimpleNamespace()
            self.spa_name = "My Spa"
            self.spa_id = "1"
            self.state = {}
            self.called = 0

        async def trigger_sanitise(self):
            self.called += 1

    coordinator = _Coordinator()
    hass = SimpleNamespace(data={const.DOMAIN: {"entry-1": {"coordinators": [coordinator]}}})
    config_entry = SimpleNamespace(entry_id="entry-1", options={})

    created = []
    await button_module.async_setup_entry(hass, config_entry, created.extend)

    button = next(entity for entity in created if entity._attr_name == "Run Sanitise")
    await button.async_press()
    assert coordinator.called == 1


@pytest.mark.asyncio
async def test_sanitise_off_request_is_ignored():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=None,
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )

    class _Spa:
        def __init__(self):
            self.calls = 0

        async def set_sanitise_status(self, _on):
            self.calls += 1

        async def get_sanitise_status(self):
            return False

    spa = _Spa()
    coordinator.spa = spa
    coordinator.state = {const.SK_SANITISE_STATUS: "off"}

    await coordinator.set_sanitiser("off")

    assert spa.calls == 0
    assert coordinator.state[const.SK_SANITISE_STATUS] == "off"
