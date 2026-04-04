"""SpaNET API client."""

import json
import logging
import time

import jwt

try:
    from .api_mappings import (
        BLOWER_STATE_TO_API,
        HEAT_PUMP_API_BY_LABEL,
        PUMP_STATE_TO_API,
    )
except ImportError:
    from api_mappings import (  # type: ignore
        BLOWER_STATE_TO_API,
        HEAT_PUMP_API_BY_LABEL,
        PUMP_STATE_TO_API,
    )

logger = logging.getLogger(__name__)

BASE_URL = "https://app.spanet.net.au/api"


class SpaNetException(Exception):
    """Base SpaNet Exception."""


class SpaNetAuthFailed(SpaNetException):
    """SpaNet authentication failed."""


class SpaNetPoolUnknown(SpaNetException):
    """SpaPool not found."""


class SpaNetApiError(SpaNetException):
    """SpaNet API error."""

    def __init__(self, response, body):
        self.response = response
        super().__init__(f"API Error {response.status}: {body}")


class SpaNetDeviceOffline(SpaNetApiError):
    """SpaNET device is offline according to the cloud API."""


class SpaNetResponseError(SpaNetException):
    """SpaNet response error."""

    def __init__(self, response, message):
        self.response = response
        super().__init__(message)


class SpaPool:
    def __init__(self, config, client):
        self.config = config
        self.client = client

    @property
    def id(self):
        return self.config["id"]

    @property
    def name(self):
        return self.config["name"]

    async def get_dashboard(self):
        return await self.client.get(f"/Dashboard/{self.id}")

    async def set_temperature(self, temp: int):
        return await self.client.put(f"/Dashboard/{self.id}", {"temperature": temp})

    async def get_information(self):
        return await self.client.get(f"/Information/{self.id}")

    async def get_pumps(self):
        return await self.client.get(f"/PumpsAndBlower/Get/{self.id}")

    async def set_pump(self, pump_id: str, state: str, state_map: dict | None = None):
        state = str(state).lower()
        mapping = state_map or PUMP_STATE_TO_API
        payload = mapping.get(state)
        if payload is None:
            logger.warning("Unknown modeId for pump state %s", state)
            return None

        return await self.client.put(
            f"/PumpsAndBlower/SetPump/{pump_id}",
            {
                "deviceId": int(self.id),
                "modeId": payload["modeId"],
                "pumpVariableSpeed": payload["pumpVariableSpeed"],
            },
        )

    async def set_blower(self, blower_id: str, state: str, speed: int):
        state = str(state).lower()
        payload = BLOWER_STATE_TO_API.get(state)
        if payload is None:
            logger.warning("Unknown blower state %s", state)
            return None

        return await self.client.put(
            f"/PumpsAndBlower/SetBlower/{blower_id}",
            {
                "deviceId": int(self.id),
                "modeId": payload["modeId"],
                "speed": max(1, min(5, int(speed))),
            },
        )

    async def get_operation_mode(self):
        return await self.client.get(f"/Settings/OperationMode/{self.id}")

    async def set_operation_mode(self, mode: int):
        return await self.client.put(f"/Settings/OperationMode/{self.id}", {"mode": mode})

    async def get_power_save(self):
        return await self.client.get(f"/Settings/PowerSave/{self.id}")

    async def set_power_save(self, mode: int):
        return await self.client.put(
            f"/Settings/PowerSave/{self.id}",
            {"mode": mode, "startTime": "00:00", "endTime": "00:00"},
        )

    async def get_sleep_timer(self):
        return await self.client.get(f"/SleepTimers/{self.id}")

    async def set_sleep_timer_enabled(self, timer_id: int, enabled: bool):
        timer = await self.client.get(f"/SleepTimers/{self.id}")
        match = next((t for t in timer if int(t.get("id")) == int(timer_id)), None)
        if match is None:
            raise SpaNetException(f"Sleep timer {timer_id} not found")
        return await self.update_sleep_timer(
            timer_id=int(timer_id),
            timer_number=int(match.get("timerNumber")),
            timer_name=str(match.get("timerName")),
            start_time=str(match.get("startTime")),
            end_time=str(match.get("endTime")),
            days_hex=str(match.get("daysHex")),
            is_enabled=enabled,
        )

    async def create_sleep_timer(
        self,
        timer_number: int,
        timer_name: str,
        start_time: str,
        end_time: str,
        days_hex: str,
        is_enabled: bool,
    ):
        return await self.client.post(
            "/SleepTimers",
            {
                "deviceId": int(self.id),
                "timerNumber": int(timer_number),
                "timerName": timer_name,
                "startTime": start_time,
                "endTime": end_time,
                "daysHex": days_hex,
                "isEnabled": bool(is_enabled),
            },
        )

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
        return await self.client.put(
            f"/SleepTimers/{timer_id}",
            {
                "deviceId": int(self.id),
                "timerNumber": int(timer_number),
                "timerName": timer_name,
                "startTime": start_time,
                "endTime": end_time,
                "daysHex": days_hex,
                "isEnabled": bool(is_enabled),
            },
        )

    async def delete_sleep_timer(self, timer_id: int):
        return await self.client.delete(f"/SleepTimers/{timer_id}")

    async def get_heat_pump(self):
        return await self.client.get(f"/Settings/HeatPumpMode/{self.id}")

    async def set_heat_pump(self, mode: str):
        api_mode = HEAT_PUMP_API_BY_LABEL[mode]
        return await self.client.put(
            f"/Settings/SetHeatPumpMode/{self.id}",
            {"mode": api_mode, "svElementBoost": False},
        )

    async def set_element_boost(self, on: bool):
        return await self.client.put(
            f"/Settings/SetElementBoost/{self.id}",
            {"svElementBoost": bool(on)},
        )

    async def get_sanitise_time(self):
        return await self.client.get(f"/Settings/Sanitise/{self.id}", requires_json=False)

    async def set_sanitise_time(self, value: str):
        return await self.client.put(f"/Settings/Sanitise/{self.id}", {"time": value})

    async def set_sanitise_status(self, on: bool):
        attempts = [
            (f"/Settings/SanitiseStatus/{self.id}?on={str(bool(on)).lower()}", {}),
            (f"/Settings/SanitiseStatus/{self.id}?on={1 if on else 0}", {}),
            (f"/Settings/SanitiseStatus/{self.id}?on={str(bool(on))}", {}),
            (f"/Settings/SanitiseStatus/{self.id}?on={str(bool(on)).lower()}", {"on": bool(on)}),
        ]
        last_error = None
        for path, payload in attempts:
            try:
                return await self.client.put(path, payload)
            except SpaNetApiError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        return None

    async def get_light_details(self):
        return await self.client.get(f"/Lights/GetLightDetails/{self.id}")

    async def set_light_status(self, light_id: int, on: bool):
        return await self.client.put(
            f"/Lights/SetLightStatus/{int(light_id)}",
            {"deviceId": int(self.id), "on": bool(on)},
        )

    async def set_light_mode(self, light_id: int, mode: str):
        return await self.client.put(
            f"/Lights/SetLightMode/{int(light_id)}",
            {"deviceId": int(self.id), "mode": mode},
        )

    async def set_light_colour(self, light_id: int, colour: str):
        return await self.client.put(
            f"/Lights/SetLightColour/{int(light_id)}",
            {"deviceId": int(self.id), "colour": colour},
        )

    async def set_light_brightness(self, light_id: int, brightness: int):
        return await self.client.put(
            f"/Lights/SetLightBrightness/{int(light_id)}",
            {"deviceId": int(self.id), "brightness": max(1, min(5, int(brightness)))},
        )

    async def set_light_speed(self, light_id: int, speed: int):
        return await self.client.put(
            f"/Lights/SetLightSpeed/{int(light_id)}",
            {"deviceId": int(self.id), "speed": max(1, min(5, int(speed)))},
        )

    async def get_filtration(self):
        return await self.client.get(f"/Settings/Filtration/{self.id}")

    async def set_filtration(self, total_runtime: int, in_between_cycles: int):
        return await self.client.put(
            f"/Settings/Filtration/{self.id}",
            {"totalRuntime": int(total_runtime), "inBetweenCycles": int(in_between_cycles)},
        )

    async def get_timeout(self):
        return await self.client.get(f"/Settings/Timeout/{self.id}")

    async def set_timeout(self, timeout: int):
        return await self.client.put(f"/Settings/Timeout/{self.id}", {"timeout": int(timeout)})


class SpaNet:
    def __init__(self, aio_session):
        self.session = aio_session
        self.spa_configs = []
        self.client = None
        self.token_source = None

    async def authenticate(self, email, password, device_id):
        login_params = {
            "email": email,
            "password": password,
            "userDeviceId": device_id,
            "language": "en_AU",
        }

        client = HttpClient(self.session)
        try:
            login_data = await client.post("/Login/Authenticate", login_params)
            if "access_token" not in login_data:
                raise SpaNetAuthFailed()
        except Exception as exc:
            raise SpaNetAuthFailed(exc) from exc

        self.token_source = TokenSource(client, login_data, device_id)
        self.client = HttpClient(self.session, self.token_source)
        device_data = await self.client.get("/Devices")

        self.spa_configs = [
            {
                "id": str(config["id"]),
                "name": config["name"],
                "macAddress": config["macAddress"],
            }
            for config in device_data["devices"]
        ]

    def get_available_spas(self):
        return self.spa_configs

    async def get_spa(self, spa_id):
        spa_config = next((spa for spa in self.spa_configs if str(spa["id"]) == spa_id), None)
        if not spa_config:
            raise SpaNetPoolUnknown()
        return SpaPool(spa_config, self.client)


class HttpClient:
    def __init__(self, session, token_source=None):
        self.session = session
        self.token_source = token_source

    async def post(self, path, payload):
        response = await self.session.post(
            BASE_URL + path,
            data=json.dumps(payload),
            headers=await self.build_headers(),
        )
        return await self.check_response(response)

    async def put(self, path, payload):
        response = await self.session.put(
            BASE_URL + path,
            data=json.dumps(payload),
            headers=await self.build_headers(),
        )
        return await self.check_response(response)

    async def delete(self, path):
        response = await self.session.delete(BASE_URL + path, headers=await self.build_headers())
        return await self.check_response(response)

    async def get(self, path, requires_json=True):
        response = await self.session.get(BASE_URL + path, headers=await self.build_headers())
        return await self.check_response(response, requires_json)

    async def build_headers(self):
        headers = {
            "User-Agent": "SpaNET/5 CFNetwork/1498.700.2 Darwin/23.6.0",
            "Content-Type": "application/json",
        }
        if self.token_source is not None:
            headers["Authorization"] = "Bearer " + (await self.token_source.token())
        return headers

    async def check_response(self, response, requires_json=False):
        if response.status > 299:
            await self.raise_api_error(response)

        is_json = response.headers.get("Content-Type", "").startswith("application/json")
        if not is_json and requires_json:
            await self.raise_api_error(response)

        if is_json:
            data = await response.json()
            if isinstance(data, (dict, list, int, float, str, bool)) or data is None:
                return data
            raise SpaNetResponseError(
                response,
                f"Request to {response.url} received unexpected {type(data).__name__} response: {data}",
            )

        return await response.text()

    async def raise_api_error(self, response):
        body = await response.text()
        location = str(response.headers.get("Location", "")).strip().lower()
        if response.status == 202 and location == "device offline":
            raise SpaNetDeviceOffline(response, body)
        raise SpaNetApiError(response, body)


class TokenSource:
    def __init__(self, client, token, device_id):
        self.token_data = {"device_id": device_id}
        self.client = client
        self.update(token)

    def update(self, token):
        decoded = jwt.decode(
            token["access_token"],
            options={"verify_signature": False},
            algorithms=["HS256"],
        )
        self.token_data.update(token)
        self.token_data["expires_at"] = decoded["exp"]

    async def token(self):
        expire_threshold = int(time.time()) + 60
        if self.token_data["expires_at"] > expire_threshold:
            return self.token_data["access_token"]

        response = await self.client.post(
            "/OAuth/Token",
            {
                "refreshToken": self.token_data["refresh_token"],
                "userDeviceId": self.token_data["device_id"],
            },
        )
        self.update(response)
        logger.debug("Token refreshed")
        return self.token_data["access_token"]
