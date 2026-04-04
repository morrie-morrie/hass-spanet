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
    components_switch = sys.modules.setdefault(
        "homeassistant.components.switch", types.ModuleType("homeassistant.components.switch")
    )
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
    )
    const_module = sys.modules.setdefault(
        "homeassistant.const", types.ModuleType("homeassistant.const")
    )
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    exceptions_module = sys.modules.setdefault(
        "homeassistant.exceptions", types.ModuleType("homeassistant.exceptions")
    )
    data_entry_flow = sys.modules.setdefault(
        "homeassistant.data_entry_flow", types.ModuleType("homeassistant.data_entry_flow")
    )
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
    helpers_aiohttp = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    helpers_entity_registry = sys.modules.setdefault(
        "homeassistant.helpers.entity_registry",
        types.ModuleType("homeassistant.helpers.entity_registry"),
    )
    helpers_device_registry = sys.modules.setdefault(
        "homeassistant.helpers.device_registry",
        types.ModuleType("homeassistant.helpers.device_registry"),
    )
    voluptuous = sys.modules.setdefault("voluptuous", types.ModuleType("voluptuous"))
    async_timeout = sys.modules.setdefault("async_timeout", types.ModuleType("async_timeout"))

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            return None

        def __init__(self):
            self.hass = None
            self._unique_id = None
            self._configured_unique_ids = set()

        async def async_set_unique_id(self, unique_id):
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            if self._unique_id in self._configured_unique_ids:
                raise AbortFlow("already_configured")

        def async_show_form(self, step_id, data_schema=None, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "errors": errors or {},
            }

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def add_suggested_values_to_schema(self, schema, options):
            return schema

        def async_update_reload_and_abort(self, entry, data=None, data_updates=None, reason=None):
            return {
                "type": "abort",
                "reason": reason,
                "entry": entry,
                "data_updates": data if data is not None else data_updates,
            }

    class OptionsFlow:
        def __init__(self):
            self.config_entry = None

        def add_suggested_values_to_schema(self, schema, options):
            return schema

        def async_create_entry(self, data):
            return {"type": "create_entry", "data": data}

        def async_show_form(self, step_id, data_schema=None):
            return {"type": "form", "step_id": step_id}

        def async_update_reload_and_abort(self, entry, data=None, reason=None):
            return {
                "type": "abort",
                "reason": reason,
                "entry": entry,
                "data_updates": data,
            }

    class ConfigEntry:
        def __init__(self, entry_id="entry-1", title="SpaNET", data=None, options=None):
            self.entry_id = entry_id
            self.title = title
            self.data = data or {}
            self.options = options or {}

    class HomeAssistant:
        def __init__(self):
            self.data = {}
            self.config_entries = SimpleNamespace(async_get_entry=lambda entry_id: None)

    class ServiceCall:
        def __init__(self, data=None):
            self.data = data or {}

    class AbortFlow(Exception):
        pass

    class ConfigEntryAuthFailed(Exception):
        pass

    class FlowResult(dict):
        pass

    def callback(func):
        return func

    class DeviceEntry:
        def __init__(self, id="device-1", name="Spa", identifiers=None):
            self.id = id
            self.name = name
            self.identifiers = identifiers or set()

    class DeviceInfo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class EntityCategory:
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    class SwitchEntity:
        pass

    class SwitchDeviceClass:
        SWITCH = "switch"

    class Platform:
        BINARY_SENSOR = "binary_sensor"
        SENSOR = "sensor"
        CLIMATE = "climate"
        SWITCH = "switch"
        BUTTON = "button"
        SELECT = "select"
        NUMBER = "number"
        TIME = "time"
        LIGHT = "light"

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class DataUpdateCoordinator:
        def __init__(self, hass, logger, name=None, update_interval=None):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval

        async def async_request_refresh(self):
            return None

        async def async_config_entry_first_refresh(self):
            return None

    class UpdateFailed(Exception):
        pass

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

    def _optional(key, default=None):
        return key

    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigEntry = ConfigEntry
    config_entries.AbortFlow = AbortFlow
    const_module.Platform = Platform
    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall
    core.callback = callback
    exceptions_module.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    data_entry_flow.FlowResult = FlowResult
    helpers_aiohttp.async_get_clientsession = lambda hass: object()
    components_switch.SwitchEntity = SwitchEntity
    components_switch.SwitchDeviceClass = SwitchDeviceClass
    helpers_device_registry.DeviceEntry = DeviceEntry
    helpers_entity.DeviceInfo = DeviceInfo
    helpers_entity.EntityCategory = EntityCategory
    helpers_entity_platform.AddEntitiesCallback = object
    helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
    helpers_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    helpers_update_coordinator.UpdateFailed = UpdateFailed
    homeassistant.__path__ = getattr(homeassistant, "__path__", [])
    components.__path__ = getattr(components, "__path__", [])
    helpers.__path__ = getattr(helpers, "__path__", [])
    voluptuous.Schema = _Schema
    voluptuous.Required = _required
    voluptuous.Optional = _optional
    voluptuous.Any = lambda *args, **kwargs: _identity
    voluptuous.In = lambda *args, **kwargs: _identity
    voluptuous.All = lambda *args, **kwargs: _identity
    voluptuous.Range = lambda *args, **kwargs: _identity

    class _Timeout:
        def __init__(self, _seconds):
            self._seconds = _seconds

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async_timeout.timeout = lambda seconds: _Timeout(seconds)

    def _async_get(_hass=None):
        return SimpleNamespace(entries=[])

    def _async_entries_for_config_entry(registry, entry_id):
        return getattr(registry, "entries", [])

    helpers_entity_registry.async_get = _async_get
    helpers_entity_registry.async_entries_for_config_entry = _async_entries_for_config_entry


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
spanet_module = _load("custom_components.spanet.spanet", "spanet.py")
config_flow_module = _load("custom_components.spanet.config_flow", "config_flow.py")
diagnostics_module = _load("custom_components.spanet.diagnostics", "diagnostics.py")
init_module = _load("custom_components.spanet.__init__", "__init__.py")


@pytest.mark.asyncio
async def test_validate_input_normalizes_email_and_never_returns_password(monkeypatch):
    captured = {}

    class _FakeSpaNet:
        def __init__(self, _session):
            pass

        async def authenticate(self, email, password, device_id):
            captured["email"] = email
            captured["password"] = password
            captured["device_id"] = device_id

    monkeypatch.setattr(config_flow_module, "SpaNet", _FakeSpaNet)

    result = await config_flow_module.ConfigFlow.validate_input(
        SimpleNamespace(),
        {"email": " Test@Example.Com ", "password": "secret"},
    )

    assert captured["email"] == "test@example.com"
    assert captured["password"] == "secret"
    assert result["title"] == "SpaNET"
    assert result["unique_id"] == f"{const.ACCOUNT_UNIQUE_ID_PREFIX}test@example.com"
    assert "password" not in result


@pytest.mark.asyncio
async def test_config_flow_aborts_when_unique_id_already_configured(monkeypatch):
    async def _validate_input(_hass, _user_input):
        return {
            "title": "SpaNET",
            "unique_id": f"{const.ACCOUNT_UNIQUE_ID_PREFIX}test@example.com",
        }

    monkeypatch.setattr(config_flow_module.ConfigFlow, "validate_input", staticmethod(_validate_input))

    flow = config_flow_module.ConfigFlow()
    flow.hass = SimpleNamespace()
    flow._configured_unique_ids = {f"{const.ACCOUNT_UNIQUE_ID_PREFIX}test@example.com"}

    with pytest.raises(Exception) as exc:
        await flow.async_step_user({"email": "test@example.com", "password": "secret"})

    assert str(exc.value) == "already_configured"


@pytest.mark.asyncio
async def test_diagnostics_redacts_sensitive_fields(monkeypatch):
    class _Registry:
        def __init__(self):
            self.entries = [
                SimpleNamespace(platform=const.DOMAIN, entity_id="switch.spa_pump1"),
            ]

    registry = _Registry()
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers.entity_registry"],
        "async_get",
        lambda hass: registry,
    )

    config_entry = SimpleNamespace(
        entry_id="entry-1",
        title="SpaNET",
        data={"email": "user@example.com", "password": "secret"},
        options={"enable_heat_pump": True},
    )
    coordinator = SimpleNamespace(
        spa_id="1",
        spa_name="Spa",
        state={
            "apiId": "123",
            "elementBoost": "off",
            "macAddress": "AA:BB",
            "settingsDetails": {
                "operationMode": "ECON",
                "timeout": "20",
                "spanetAccount": "Andrew Morison",
            },
            "sleepTimers": {
                "1": {
                    "state": "on",
                    "show": True,
                    "allowHeating": False,
                }
            },
        },
    )
    hass = SimpleNamespace(
        data={const.DOMAIN: {"entry-1": {"coordinators": [coordinator]}}},
    )

    diagnostics = await diagnostics_module.async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["config_entry"]["data"]["email"] == "**REDACTED**"
    assert diagnostics["config_entry"]["data"]["password"] == "**REDACTED**"
    assert diagnostics["coordinators"][0]["state"]["apiId"] == "**REDACTED**"
    assert diagnostics["coordinators"][0]["state"]["macAddress"] == "**REDACTED**"
    assert diagnostics["coordinators"][0]["state"]["settingsDetails"]["operationMode"] == "ECON"
    assert diagnostics["coordinators"][0]["state"]["settingsDetails"]["timeout"] == "20"
    assert diagnostics["coordinators"][0]["state"]["sleepTimers"]["1"]["show"] is True
    assert diagnostics["coordinators"][0]["state"]["sleepTimers"]["1"]["allowHeating"] is False
    assert diagnostics["entities"] == ["switch.spa_pump1"]


@pytest.mark.asyncio
async def test_reauth_updates_existing_entry(monkeypatch):
    async def _validate_input(_hass, _user_input):
        return {
            "title": "SpaNET",
            "email": "test@example.com",
            "unique_id": f"{const.ACCOUNT_UNIQUE_ID_PREFIX}test@example.com",
        }

    monkeypatch.setattr(config_flow_module.ConfigFlow, "validate_input", staticmethod(_validate_input))

    entry = SimpleNamespace(data={"email": "test@example.com", "password": "old"})
    flow = config_flow_module.ConfigFlow()
    flow.hass = SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry))
    flow.context = {"entry_id": "entry-1"}

    await flow.async_step_reauth({})
    result = await flow.async_step_reauth_confirm(
        {"email": "test@example.com", "password": "new-secret"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    assert result["data_updates"]["password"] == "new-secret"


@pytest.mark.asyncio
async def test_reauth_rejects_different_account(monkeypatch):
    async def _validate_input(_hass, _user_input):
        raise AssertionError("validate_input should not be called for wrong account")

    monkeypatch.setattr(config_flow_module.ConfigFlow, "validate_input", staticmethod(_validate_input))

    entry = SimpleNamespace(data={"email": "test@example.com", "password": "old"})
    flow = config_flow_module.ConfigFlow()
    flow.hass = SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry))
    flow.context = {"entry_id": "entry-1"}

    await flow.async_step_reauth({})
    result = await flow.async_step_reauth_confirm(
        {"email": "other@example.com", "password": "new-secret"}
    )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "wrong_account"


@pytest.mark.asyncio
async def test_reconfigure_updates_credentials(monkeypatch):
    async def _validate_input(_hass, _user_input):
        return {
            "title": "SpaNET",
            "email": "new@example.com",
            "unique_id": f"{const.ACCOUNT_UNIQUE_ID_PREFIX}new@example.com",
        }

    monkeypatch.setattr(config_flow_module.ConfigFlow, "validate_input", staticmethod(_validate_input))

    flow = config_flow_module.OptionsFlowHandler()
    flow.hass = SimpleNamespace()
    flow.config_entry = SimpleNamespace(data={"email": "old@example.com", "password": "old"})

    result = await flow.async_step_reconfigure(
        {"email": "new@example.com", "password": "new-secret"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    assert result["data_updates"]["email"] == "new@example.com"
    assert result["data_updates"]["password"] == "new-secret"


@pytest.mark.asyncio
async def test_setup_entry_raises_auth_failed_for_bad_credentials(monkeypatch):
    class _FakeSpaNet:
        def __init__(self, _session):
            pass

        async def authenticate(self, _email, _password, _device_id):
            raise spanet_module.SpaNetAuthFailed()

    monkeypatch.setattr(init_module, "SpaNet", _FakeSpaNet)
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers.aiohttp_client"],
        "async_get_clientsession",
        lambda hass: object(),
    )

    hass = SimpleNamespace(data={}, config_entries=SimpleNamespace())
    config_entry = SimpleNamespace(
        entry_id="entry-1",
        data={"email": "test@example.com", "password": "secret"},
    )

    with pytest.raises(sys.modules["homeassistant.exceptions"].ConfigEntryAuthFailed):
        await init_module.async_setup_entry(hass, config_entry)


def test_legacy_sensor_binary_entries_are_identified_for_cleanup():
    retired_pump = SimpleNamespace(domain="sensor", original_name="Pump 2", name=None)
    retired_heater = SimpleNamespace(domain="sensor", original_name="Heater", name=None)
    active_temp = SimpleNamespace(domain="sensor", original_name="Water Temperature", name=None)

    assert init_module._is_retired_sensor_binary_entry(retired_pump) is True
    assert init_module._is_retired_sensor_binary_entry(retired_heater) is True
    assert init_module._is_retired_sensor_binary_entry(active_temp) is False


def test_retired_entity_names_cover_old_date_time_variants():
    assert "DateTime" in const.RETIRED_ENTITY_NAMES_BY_DOMAIN["datetime"]
    assert "Date/Time" in const.RETIRED_ENTITY_NAMES_BY_DOMAIN["datetime"]
