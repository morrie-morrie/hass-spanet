import importlib.util
import sys
import time
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
spanet_module = _load("custom_components.spanet.spanet", "spanet.py")
coordinator_module = _load("custom_components.spanet.coordinator", "coordinator.py")


class _Spa:
    async def get_settings_details(self):
        return {
            "operationMode": "ECON",
            "heatPumpMode": "HEAT",
            "powersaveMode": "HIGH",
            "sanitiseTime": "14:00",
            "timeout": "20",
            "filtration": "4 | 3",
            "showRunTimers": False,
            "sleepTimers": "2",
        }

    async def get_filtration(self):
        return {"totalRuntime": 4, "inBetweenCycles": 3}

    async def get_timeout(self):
        return 20

    async def get_sanitise_time(self):
        return {"time": "08:30:00"}

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

    async def set_timeout(self, value):
        self.timeout_value = value

    async def set_filtration(self, total_runtime: int, in_between_cycles: int):
        self.filtration_value = (total_runtime, in_between_cycles)

    async def update_sleep_timer(
        self,
        timer_id: int,
        timer_number: int,
        timer_name: str,
        start_time: str,
        end_time: str,
        days_hex: str,
        is_enabled: bool,
    ):
        self.updated_timer = {
            "timer_id": timer_id,
            "timer_number": timer_number,
            "timer_name": timer_name,
            "start_time": start_time,
            "end_time": end_time,
            "days_hex": days_hex,
            "is_enabled": is_enabled,
        }

    async def set_sleep_timer_enabled(self, timer_id: int, timer_number: int, enabled: bool):
        self.sleep_timer_enabled = {
            "timer_id": timer_id,
            "timer_number": timer_number,
            "enabled": enabled,
        }

    async def set_sleep_timer_start_time(
        self, timer_id: int, timer_number: int, start_time: str, is_enabled: bool
    ):
        self.sleep_timer_start = {
            "timer_id": timer_id,
            "timer_number": timer_number,
            "start_time": start_time,
            "is_enabled": is_enabled,
        }

    async def set_sleep_timer_end_time(
        self, timer_id: int, timer_number: int, end_time: str, is_enabled: bool
    ):
        self.sleep_timer_end = {
            "timer_id": timer_id,
            "timer_number": timer_number,
            "end_time": end_time,
            "is_enabled": is_enabled,
        }

    async def set_sleep_timer_days(
        self, timer_id: int, timer_number: int, days_hex: str, is_enabled: bool
    ):
        self.sleep_timer_days = {
            "timer_id": timer_id,
            "timer_number": timer_number,
            "days_hex": days_hex,
            "is_enabled": is_enabled,
        }


@pytest.mark.asyncio
async def test_offline_api_marks_cloud_connectivity_false():
    class _Resp:
        status = 202
        headers = {"Location": "Device Offline"}

    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=SimpleNamespace(),
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )

    class _OfflineSpa:
        async def get_dashboard(self):
            raise spanet_module.SpaNetDeviceOffline(_Resp(), "")

    coordinator.spa = _OfflineSpa()

    with pytest.raises(coordinator_module.UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.state[const.SK_CLOUD_CONNECTED] is False
    assert coordinator.tasks[0].next_tick > int(time.time())
    assert coordinator.tasks[4].next_tick > int(time.time())


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
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["show"] is False
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["allowHeating"] is False
    assert coordinator.state[const.SK_SETTINGS_DETAILS]["operationMode"] == "ECON"
    assert coordinator.state[const.SK_FILTRATION_RUNTIME] == 4
    assert coordinator.state[const.SK_FILTRATION_CYCLE] == 3
    assert coordinator.state[const.SK_SETTINGS_DETAILS]["filtration"] == "4 | 3"


@pytest.mark.asyncio
async def test_update_dashboard_prefers_sanitise_on_flag_over_status_text():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=SimpleNamespace(),
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )

    class _SpaWithDashboard:
        async def get_dashboard(self):
            return {
                "setTemperature": 33,
                "currentTemperature": 32.5,
                "statusList": ["Heating"],
                "sanitiseOn": True,
            }

    coordinator.spa = _SpaWithDashboard()
    await coordinator.update_dashboard()

    assert coordinator.state[const.SK_SANITISE] == 1


@pytest.mark.asyncio
async def test_update_dashboard_falls_back_to_status_list_when_sanitise_flag_missing():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=SimpleNamespace(),
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )

    class _SpaWithDashboard:
        async def get_dashboard(self):
            return {
                "setTemperature": 33,
                "currentTemperature": 32.5,
                "statusList": ["Sanitise Cycle: 19:24"],
            }

    coordinator.spa = _SpaWithDashboard()
    await coordinator.update_dashboard()

    assert coordinator.state[const.SK_SANITISE] == 1


@pytest.mark.asyncio
async def test_settings_writes_queue_immediate_settings_refresh_without_full_refresh():
    coordinator = coordinator_module.Coordinator(
        hass=SimpleNamespace(),
        spanet=SimpleNamespace(),
        spa_config={"id": "1", "name": "Spa"},
        config_entry=SimpleNamespace(options={}),
    )
    coordinator.spa = _Spa()
    coordinator.state = {
        const.SK_FILTRATION_RUNTIME: 3,
        const.SK_FILTRATION_CYCLE: 12,
        const.SK_TIMEOUT: 20,
        const.SK_SLEEP_TIMERS: {
            "1": {
                "apiId": 11,
                "number": 1,
                "name": "Timer 1",
                "startTime": "22:00",
                "endTime": "08:30",
                "daysHex": "7F",
                "isEnabled": True,
                "state": "on",
            }
        },
    }

    notifications = {"count": 0}
    coordinator.async_update_listeners = lambda: notifications.__setitem__("count", notifications["count"] + 1)

    await coordinator.set_timeout(30)
    assert coordinator.tasks[4].next_tick <= int(time.time())

    coordinator.tasks[4].next_tick = 999
    await coordinator.set_sleep_timer("1", "off")
    assert coordinator.tasks[4].next_tick <= int(time.time())
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["state"] == "off"
    assert coordinator.spa.sleep_timer_enabled == {"timer_id": 11, "timer_number": 1, "enabled": False}

    coordinator.tasks[4].next_tick = 999
    await coordinator.set_sleep_timer_on_time("1", "21:00")
    assert coordinator.tasks[4].next_tick <= int(time.time())
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["startTime"] == "21:00"
    assert coordinator.spa.sleep_timer_start == {
        "timer_id": 11,
        "timer_number": 1,
        "start_time": "21:00",
        "is_enabled": False,
    }

    coordinator.tasks[4].next_tick = 999
    await coordinator.set_sleep_timer_day_profile("1", "Week Days")
    assert coordinator.tasks[4].next_tick <= int(time.time())
    assert coordinator.state[const.SK_SLEEP_TIMERS]["1"]["dayProfile"] == "Week Days"
    assert coordinator.spa.sleep_timer_days == {
        "timer_id": 11,
        "timer_number": 1,
        "days_hex": "1F",
        "is_enabled": False,
    }

    assert notifications["count"] == 4
