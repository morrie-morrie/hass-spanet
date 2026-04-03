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
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    voluptuous = sys.modules.setdefault("voluptuous", types.ModuleType("voluptuous"))

    class HomeAssistant:
        def __init__(self):
            self.data = {}

    class ServiceCall:
        def __init__(self, data=None):
            self.data = data or {}

    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall
    homeassistant.__path__ = getattr(homeassistant, "__path__", [])

    class _Schema:
        def __init__(self, schema):
            self.schema = schema

        def extend(self, extra):
            merged = dict(self.schema)
            merged.update(extra)
            return _Schema(merged)

    def _identity(value):
        return value

    def _required(key, default=None):
        return key

    voluptuous.Schema = _Schema
    voluptuous.Required = _required
    voluptuous.Optional = _required
    voluptuous.Any = lambda *args, **kwargs: _identity
    voluptuous.In = lambda *args, **kwargs: _identity
    voluptuous.All = lambda *args, **kwargs: _identity
    voluptuous.Range = lambda *args, **kwargs: _identity


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
services_module = _load("custom_components.spanet.services", "services.py")


class _Services:
    def __init__(self):
        self._handlers = {}

    def has_service(self, domain, service):
        return (domain, service) in self._handlers

    def async_register(self, domain, service, handler, schema=None):
        self._handlers[(domain, service)] = handler

    def async_remove(self, domain, service):
        self._handlers.pop((domain, service), None)

    async def call(self, domain, service, data):
        await self._handlers[(domain, service)](SimpleNamespace(data=data))


@pytest.mark.asyncio
async def test_sleep_timer_services_are_registered_and_forward_to_coordinator():
    calls = []

    class _Coordinator:
        spa_id = "1"

        async def create_sleep_timer(self, **kwargs):
            calls.append(("create", kwargs))

        async def update_sleep_timer(self, **kwargs):
            calls.append(("update", kwargs))

        async def delete_sleep_timer(self, timer_id):
            calls.append(("delete", timer_id))

    hass = SimpleNamespace(
        data={const.DOMAIN: {"entry-1": {"coordinators": [_Coordinator()]}}},
        services=_Services(),
    )

    await services_module.async_register_services(hass)

    await hass.services.call(
        const.DOMAIN,
        services_module.SERVICE_CREATE_SLEEP_TIMER,
        {
            "spa_id": "1",
            "timer_number": 2,
            "timer_name": "Timer 2",
            "start_time": "22:00",
            "end_time": "07:00",
            "days_hex": "60",
            "is_enabled": True,
        },
    )
    await hass.services.call(
        const.DOMAIN,
        services_module.SERVICE_UPDATE_SLEEP_TIMER,
        {
            "spa_id": "1",
            "timer_id": 12,
            "timer_number": 2,
            "timer_name": "Timer 2",
            "start_time": "22:30",
            "end_time": "07:30",
            "days_hex": "60",
            "is_enabled": False,
        },
    )
    await hass.services.call(
        const.DOMAIN,
        services_module.SERVICE_DELETE_SLEEP_TIMER,
        {"spa_id": "1", "timer_id": 12},
    )

    assert calls[0] == (
        "create",
        {
            "timer_number": 2,
            "timer_name": "Timer 2",
            "start_time": "22:00",
            "end_time": "07:00",
            "days_hex": "60",
            "is_enabled": True,
        },
    )
    assert calls[1] == (
        "update",
        {
            "timer_id": 12,
            "timer_number": 2,
            "timer_name": "Timer 2",
            "start_time": "22:30",
            "end_time": "07:30",
            "days_hex": "60",
            "is_enabled": False,
        },
    )
    assert calls[2] == ("delete", 12)
