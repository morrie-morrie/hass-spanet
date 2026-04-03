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
    helpers = sys.modules.setdefault(
        "homeassistant.helpers", types.ModuleType("homeassistant.helpers")
    )
    helpers_update_coordinator = sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator",
        types.ModuleType("homeassistant.helpers.update_coordinator"),
    )
    async_timeout = sys.modules.setdefault("async_timeout", types.ModuleType("async_timeout"))

    class DataUpdateCoordinator:
        def __init__(self, hass, logger, name=None, update_interval=None):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval

        async def async_request_refresh(self):
            return None

    class UpdateFailed(Exception):
        pass

    helpers_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    helpers_update_coordinator.UpdateFailed = UpdateFailed
    helpers.__path__ = getattr(helpers, "__path__", [])
    homeassistant.__path__ = getattr(homeassistant, "__path__", [])

    class _Timeout:
        def __init__(self, _seconds):
            self._seconds = _seconds

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async_timeout.timeout = lambda seconds: _Timeout(seconds)


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
_load("custom_components.spanet.api_mappings", "api_mappings.py")
_load("custom_components.spanet.scheduler", "scheduler.py")
_load("custom_components.spanet.spanet", "spanet.py")
coordinator_module = _load("custom_components.spanet.coordinator", "coordinator.py")


class _Spa:
    async def get_filtration(self):
        return {"totalRuntime": 3, "inBetweenCycles": 12}

    async def get_lock_mode(self):
        return 0

    async def get_timeout(self):
        return 20

    async def get_sanitise_time(self):
        return {"time": "08:30:00"}

    async def get_sanitise_status(self):
        return False

    async def get_date_time(self):
        return "2026-04-03T14:05:00"

    async def get_support_mode(self):
        return "off"

    async def get_power_save(self):
        return {"mode": 3}

    async def get_operation_mode(self):
        return 1

    async def get_sleep_timer(self):
        return [
            {
                "id": 11,
                "timerNumber": 1,
                "timerName": "Timer 1",
                "startTime": "22:00:00",
                "endTime": "08:30:00",
                "daysHex": "7F",
                "isEnabled": True,
            },
            {
                "id": 12,
                "timerNumber": 2,
                "timerName": "Timer 2",
                "startTime": "22:00:00",
                "endTime": "07:00:00",
                "daysHex": "60",
                "isEnabled": False,
            },
        ]


@pytest.mark.asyncio
async def test_update_settings_uses_sleep_timer_endpoint_and_normalizes_times():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=SimpleNamespace(),
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.spa = _Spa()

    await coordinator.update_settings()

    assert coordinator.state[const.SK_SANITISE_TIME] == "08:30"
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["startTime"] == "22:00"
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["endTime"] == "08:30"
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["state"] == "on"
    assert coordinator.state[const.SK_SLEEP_TIMERS]["2"]["endTime"] == "07:00"
    assert coordinator.state[const.SK_SLEEP_TIMERS]["2"]["state"] == "off"
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["dayProfile"] == "Every Day"
    assert coordinator.state[const.SK_SLEEP_TIMERS]["2"]["dayProfile"] == "Weekends"
