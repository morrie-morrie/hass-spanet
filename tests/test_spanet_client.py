import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPANET_DIR = ROOT / "custom_components" / "spanet"


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
    _ensure_package()
    spec = importlib.util.spec_from_file_location(module_name, SPANET_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


api_mappings = _load("custom_components.spanet.api_mappings", "api_mappings.py")
spanet_module = _load("custom_components.spanet.spanet", "spanet.py")

HttpClient = spanet_module.HttpClient
SpaNetResponseError = spanet_module.SpaNetResponseError
SpaPool = spanet_module.SpaPool
TokenSource = spanet_module.TokenSource
SpaNetDeviceOffline = spanet_module.SpaNetDeviceOffline


class FakeResponse:
    def __init__(self, status=200, headers=None, json_data=None, text_data="", url="http://test"):
        self.status = status
        self.headers = headers or {}
        self._json_data = json_data
        self._text_data = text_data
        self.url = url

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data


class FakeSession:
    def __init__(self):
        self.calls = []
        self.next_response = FakeResponse(headers={"Content-Type": "application/json"}, json_data={})

    async def post(self, url, data=None, headers=None):
        self.calls.append(("post", url, data, headers))
        return self.next_response

    async def put(self, url, data=None, headers=None):
        self.calls.append(("put", url, data, headers))
        return self.next_response

    async def get(self, url, headers=None):
        self.calls.append(("get", url, None, headers))
        return self.next_response

    async def delete(self, url, headers=None):
        self.calls.append(("delete", url, None, headers))
        return self.next_response


class FakeClient:
    def __init__(self):
        self.calls = []
        self.get_calls = []

    async def get(self, path, requires_json=True):
        self.calls.append(("get", path, None))
        self.get_calls.append(("get", path, requires_json))
        if path == "/SleepTimers/99":
            return [
                {
                    "id": 4,
                    "timerNumber": 1,
                    "timerName": "Weekday",
                    "startTime": "08:00",
                    "endTime": "10:00",
                    "daysHex": "1F",
                    "isEnabled": True,
                }
            ]
        return {}

    async def post(self, path, payload):
        self.calls.append(("post", path, payload))
        return {}

    async def put(self, path, payload):
        self.calls.append(("put", path, payload))
        return {}

    async def delete(self, path):
        self.calls.append(("delete", path, None))
        return {}


@pytest.mark.asyncio
async def test_sleep_timer_enabled_uses_app_shaped_partial_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sleep_timer_enabled(4, 1, False)

    _, path, payload = client.calls[-1]
    assert path == "/SleepTimers/4"
    assert payload == {"deviceId": "99", "timerNumber": 1, "isEnabled": False}


@pytest.mark.asyncio
async def test_sleep_timer_partial_updates_match_app_contract():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sleep_timer_start_time(4, 1, "21:00", True)
    _, path, payload = client.calls[-1]
    assert path == "/SleepTimers/4"
    assert payload == {
        "deviceId": "99",
        "timerNumber": 1,
        "startTime": "09:00 PM",
        "isEnabled": True,
    }

    await pool.set_sleep_timer_end_time(4, 1, "09:00", False)
    _, path, payload = client.calls[-1]
    assert path == "/SleepTimers/4"
    assert payload == {
        "deviceId": "99",
        "timerNumber": 1,
        "endTime": "09:00 AM",
        "isEnabled": False,
    }

    await pool.set_sleep_timer_days(4, 1, "7F", True)
    _, path, payload = client.calls[-1]
    assert path == "/SleepTimers/4"
    assert payload == {
        "deviceId": "99",
        "timerNumber": 1,
        "daysHex": "7F",
        "isEnabled": True,
    }


@pytest.mark.asyncio
async def test_set_sanitise_time_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sanitise_time("08:30")

    _, path, payload = client.calls[-1]
    assert path == "/Settings/Sanitise/99"
    assert payload == {"time": "08:30"}


@pytest.mark.asyncio
async def test_get_sanitise_time_allows_plain_text_response():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    result = await pool.get_sanitise_time()

    assert result == {}
    assert client.get_calls[-1] == ("get", "/Settings/Sanitise/99", False)


@pytest.mark.asyncio
async def test_set_sanitise_status_uses_body_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sanitise_status(True)

    _, path, payload = client.calls[-1]
    assert path == "/Settings/SanitiseStatus/99"
    assert payload == {"on": True}


@pytest.mark.asyncio
async def test_set_sanitise_status_stop_uses_body_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sanitise_status(False)

    _, path, payload = client.calls[-1]
    assert path == "/Settings/SanitiseStatus/99"
    assert payload == {"on": False}


@pytest.mark.asyncio
async def test_set_light_mode_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_light_mode(7, "colour")

    _, path, payload = client.calls[-1]
    assert path == "/Lights/SetLightMode/7"
    assert payload == {"deviceId": 99, "mode": "colour"}


@pytest.mark.asyncio
async def test_set_light_status_payload_matches_app_contract():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_light_status(7, True)

    _, path, payload = client.calls[-1]
    assert path == "/Lights/SetLightStatus/7"
    assert payload == {"deviceId": 99, "on": True}


@pytest.mark.asyncio
async def test_set_light_speed_payload_clamped_to_supported_range():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_light_speed(7, 99)

    _, path, payload = client.calls[-1]
    assert path == "/Lights/SetLightSpeed/7"
    assert payload == {"deviceId": 99, "speed": 5}


@pytest.mark.asyncio
async def test_set_light_brightness_payload_clamped_to_supported_range():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_light_brightness(7, 0)

    _, path, payload = client.calls[-1]
    assert path == "/Lights/SetLightBrightness/7"
    assert payload == {"deviceId": 99, "brightness": 1}


@pytest.mark.asyncio
async def test_set_heat_pump_payload_uses_explicit_contract_mapping():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_heat_pump("Cool")

    _, path, payload = client.calls[-1]
    assert path == "/Settings/SetHeatPumpMode/99"
    assert payload == {"mode": 3, "svElementBoost": False}


@pytest.mark.asyncio
async def test_set_element_boost_payload_matches_contract():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_element_boost(True)

    _, path, payload = client.calls[-1]
    assert path == "/Settings/SetElementBoost/99"
    assert payload == {"svElementBoost": True}


@pytest.mark.asyncio
async def test_set_power_save_payload_matches_contract():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_power_save(2)

    _, path, payload = client.calls[-1]
    assert path == "/Settings/PowerSave/99"
    assert payload == {"mode": 2, "startTime": "00:00", "endTime": "00:00"}


@pytest.mark.asyncio
async def test_set_pump_payload_matches_contract_mapping():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_pump("7", "auto")

    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/7"
    assert payload == {"deviceId": 99, "modeId": 3, "pumpVariableSpeed": 0}


@pytest.mark.asyncio
async def test_set_pump_on_payload_uses_live_confirmed_mode_id():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_pump("7", "on")

    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/7"
    assert payload == {"deviceId": 99, "modeId": 1, "pumpVariableSpeed": 0}


@pytest.mark.asyncio
async def test_set_pump_supports_explicit_state_map_override():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_pump("7", "on", {"on": {"modeId": 3, "pumpVariableSpeed": 0}})

    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/7"
    assert payload == {"deviceId": 99, "modeId": 3, "pumpVariableSpeed": 0}


@pytest.mark.asyncio
async def test_live_derived_pump_role_mappings_are_pinned():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_pump("7", "on", api_mappings.CIRCULATION_PUMP_STATE_TO_API)
    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/7"
    assert payload == {"deviceId": 99, "modeId": 1, "pumpVariableSpeed": 0}

    await pool.set_pump("8", "on", api_mappings.PUMP_ONE_STATE_TO_API)
    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/8"
    assert payload == {"deviceId": 99, "modeId": 1, "pumpVariableSpeed": 0}

    await pool.set_pump("9", "on", api_mappings.STANDARD_PUMP_STATE_TO_API)
    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/9"
    assert payload == {"deviceId": 99, "modeId": 1, "pumpVariableSpeed": 0}

    await pool.set_pump("7", "auto", api_mappings.CIRCULATION_PUMP_STATE_TO_API)
    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/7"
    assert payload == {"deviceId": 99, "modeId": 3, "pumpVariableSpeed": 0}

    await pool.set_pump("7", "off", api_mappings.CIRCULATION_PUMP_STATE_TO_API)
    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/7"
    assert payload == {"deviceId": 99, "modeId": 2, "pumpVariableSpeed": 0}


@pytest.mark.asyncio
async def test_set_blower_payload_matches_contract_mapping():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_blower("7", "ramp", 4)

    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetBlower/7"
    assert payload == {"deviceId": 99, "modeId": 3, "speed": 0}


@pytest.mark.asyncio
async def test_set_blower_variable_and_off_payload_match_live_contract():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_blower("7", "variable", 5)
    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetBlower/7"
    assert payload == {"deviceId": 99, "modeId": 2, "speed": 5}

    await pool.set_blower("7", "off", 1)
    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetBlower/7"
    assert payload == {"deviceId": 99, "modeId": 1, "speed": 0}


def test_api_mapping_helpers_cover_known_contract_values():
    assert api_mappings.operation_mode_from_api(1) == "Normal"
    assert api_mappings.power_save_from_api(3) == "High"
    assert api_mappings.heat_pump_from_api(4) == "Off"
    assert api_mappings.extract_time_string({"time": "08:30:00"}) == "08:30"
    assert api_mappings.extract_time_string({"startTime": "2026-04-03T22:00:00"}) == "22:00"


@pytest.mark.asyncio
async def test_http_client_raises_for_unexpected_json_shape():
    session = FakeSession()
    client = HttpClient(session)
    session.next_response = FakeResponse(
        headers={"Content-Type": "application/json"},
        json_data=("unexpected",),
        url="https://api.test/value",
    )

    with pytest.raises(SpaNetResponseError):
        await client.get("/value")


@pytest.mark.asyncio
async def test_http_client_raises_device_offline_for_202_location_header():
    session = FakeSession()
    client = HttpClient(session)
    session.next_response = FakeResponse(
        status=202,
        headers={"Location": "Device Offline"},
        text_data="",
        url="https://api.test/dashboard",
    )

    with pytest.raises(SpaNetDeviceOffline):
        await client.get("/dashboard")


@pytest.mark.asyncio
async def test_token_source_refreshes_when_token_is_near_expiry(monkeypatch):
    class RefreshClient:
        def __init__(self):
            self.called = 0

        async def post(self, path, payload):
            self.called += 1
            assert path == "/OAuth/Token"
            return {
                "access_token": "refreshed",
                "refresh_token": "refresh-new",
            }

    monkeypatch.setattr(spanet_module.time, "time", lambda: 1000)
    monkeypatch.setattr(
        spanet_module.jwt,
        "decode",
        lambda token, options, algorithms: {"exp": 1005 if token == "old" else 2000},
    )

    refresh_client = RefreshClient()
    source = TokenSource(
        refresh_client,
        {"access_token": "old", "refresh_token": "refresh-old"},
        "device-1",
    )

    token = await source.token()

    assert token == "refreshed"
    assert refresh_client.called == 1
