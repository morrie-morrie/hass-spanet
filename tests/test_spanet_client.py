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

    async def get(self, path):
        self.calls.append(("get", path, None))
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
async def test_sleep_timer_enabled_uses_is_enabled_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sleep_timer_enabled(4, False)

    _, path, payload = client.calls[-1]
    assert path == "/SleepTimers/4"
    assert payload["isEnabled"] is False
    assert payload["deviceId"] == 99


@pytest.mark.asyncio
async def test_set_sanitise_time_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sanitise_time("08:30")

    _, path, payload = client.calls[-1]
    assert path == "/Settings/Sanitise/99"
    assert payload == {"time": "08:30"}


@pytest.mark.asyncio
async def test_set_sanitise_status_uses_query_flag():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_sanitise_status(True)

    _, path, payload = client.calls[-1]
    assert path == "/Settings/SanitiseStatus/99?on=true"
    assert payload == {}


@pytest.mark.asyncio
async def test_set_light_mode_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_light_mode(7, "rainbow")

    _, path, payload = client.calls[-1]
    assert path == "/Lights/SetLightMode/7"
    assert payload == {"deviceId": 99, "mode": "rainbow"}


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
async def test_set_lock_mode_payload_matches_contract():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_lock_mode(1)

    _, path, payload = client.calls[-1]
    assert path == "/Settings/Lock/99"
    assert payload == {"lockMode": 1}


@pytest.mark.asyncio
async def test_set_pump_payload_matches_contract_mapping():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_pump("7", "auto")

    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetPump/7"
    assert payload == {"deviceId": 99, "modeId": 3, "pumpVariableSpeed": 0}


@pytest.mark.asyncio
async def test_set_blower_payload_matches_contract_mapping():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_blower("7", "ramp", 4)

    _, path, payload = client.calls[-1]
    assert path == "/PumpsAndBlower/SetBlower/7"
    assert payload == {"deviceId": 99, "modeId": 3, "speed": 4}


def test_api_mapping_helpers_cover_known_contract_values():
    assert api_mappings.operation_mode_from_api(1) == "Normal"
    assert api_mappings.power_save_from_api(3) == "High"
    assert api_mappings.heat_pump_from_api(4) == "Off"
    assert api_mappings.lock_mode_from_api(1) == "on"


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
