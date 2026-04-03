import importlib.util
from pathlib import Path

import pytest

SPANET_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "spanet" / "spanet.py"
SPEC = importlib.util.spec_from_file_location("spanet_module", SPANET_PATH)
SPANET = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(SPANET)

HttpClient = SPANET.HttpClient
SpaNetResponseError = SPANET.SpaNetResponseError
SpaPool = SPANET.SpaPool
TokenSource = SPANET.TokenSource


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
async def test_set_light_mode_payload():
    client = FakeClient()
    pool = SpaPool({"id": "99", "name": "Spa"}, client)

    await pool.set_light_mode(7, "rainbow")

    _, path, payload = client.calls[-1]
    assert path == "/Lights/SetLightMode/7"
    assert payload == {"deviceId": 99, "mode": "rainbow"}


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

    monkeypatch.setattr(SPANET.time, "time", lambda: 1000)
    monkeypatch.setattr(
        SPANET.jwt,
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
