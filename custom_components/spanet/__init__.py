"""The SpaNET integration."""

from __future__ import annotations

import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    DEVICE_ID,
    DOMAIN,
    RETIRED_ENTITY_NAMES_BY_DOMAIN,
    RETIRED_ENTITY_UNIQUE_IDS,
)
from .coordinator import Coordinator
from .runtime_data import SpaNetRuntimeData, get_entry_runtime_data
from .services import async_register_services, async_unregister_services
from .spanet import SpaNet, SpaNetAuthFailed, SpaNetConnectionError

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.TIME,
    Platform.LIGHT,
]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up SpaNET from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    domain_data = hass.data[DOMAIN]
    domain_data.setdefault(DEVICE_ID, str(uuid.uuid4()))

    session = aiohttp_client.async_get_clientsession(hass)
    spanet = SpaNet(session)

    entry_data = SpaNetRuntimeData(client=spanet)
    hass.data[DOMAIN][config_entry.entry_id] = entry_data
    config_entry.runtime_data = entry_data

    if "email" not in config_entry.data or "password" not in config_entry.data:
        await async_register_services(hass)
        return True

    try:
        await spanet.authenticate(
            config_entry.data["email"],
            config_entry.data["password"],
            domain_data[DEVICE_ID],
        )
    except SpaNetAuthFailed as exc:
        raise ConfigEntryAuthFailed("SpaNET authentication failed") from exc
    except SpaNetConnectionError as exc:
        raise ConfigEntryNotReady("SpaNET connection failed during setup") from exc

    for spa in spanet.get_available_spas():
        coordinator = Coordinator(hass, spanet, spa, config_entry)
        await coordinator.async_config_entry_first_refresh()

        device_registry = dr.async_get(hass)
        coordinator.device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, spa["macAddress"])},
            identifiers={(DOMAIN, spa["id"])},
            name=spa["name"],
        )
        entry_data.coordinators.append(coordinator)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    await _async_cleanup_removed_entities(hass, config_entry)
    await _async_reenable_entities(hass, config_entry)
    await async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        has_entries = any(
            key != DEVICE_ID and isinstance(value, (dict, SpaNetRuntimeData))
            for key, value in hass.data.get(DOMAIN, {}).items()
        )
        if not has_entries:
            await async_unregister_services(hass)
    return unload_ok


async def _async_reenable_entities(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Re-enable SpaNET entities disabled by prior device/integration defaults."""
    registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entry.platform != DOMAIN:
            continue
        if entry.disabled_by in {
            er.RegistryEntryDisabler.DEVICE,
            er.RegistryEntryDisabler.INTEGRATION,
        }:
            registry.async_update_entity(entry.entity_id, disabled_by=None)


async def _async_cleanup_removed_entities(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Remove stale SpaNET entities for platforms no longer exposed by the integration."""
    registry = er.async_get(hass)
    desired_pump_control_unique_ids = _desired_pump_control_unique_ids(hass, config_entry)
    for entry in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entry.platform != DOMAIN:
            continue
        unique_id = str(entry.unique_id or "")
        if unique_id in RETIRED_ENTITY_UNIQUE_IDS:
            registry.async_remove(entry.entity_id)
            continue
        if _is_stale_pump_control_entry(entry, desired_pump_control_unique_ids):
            registry.async_remove(entry.entity_id)
            continue
        original_name = str(getattr(entry, "original_name", "") or getattr(entry, "name", "") or "")
        if original_name in RETIRED_ENTITY_NAMES_BY_DOMAIN.get(entry.domain, set()):
            registry.async_remove(entry.entity_id)
            continue
        if _is_retired_sensor_binary_entry(entry):
            registry.async_remove(entry.entity_id)


def _desired_pump_control_unique_ids(hass: HomeAssistant, config_entry: ConfigEntry) -> set[str]:
    desired: set[str] = set()
    entry_data = get_entry_runtime_data(hass, config_entry)
    for coordinator in entry_data.coordinators:
        for key, pump in coordinator.state.get("pumps", {}).items():
            if not pump.get("hasSwitch", False):
                continue
            domain = "select" if pump.get("auto", False) else "switch"
            name = pump.get("displayName", f"Pump {key}")
            unique_id = f"{domain}.{_build_entity_key(coordinator.spa_id, name)}"
            desired.add(unique_id)
    return desired


def _is_stale_pump_control_entry(entry: er.RegistryEntry, desired_unique_ids: set[str]) -> bool:
    if entry.domain not in {"switch", "select"}:
        return False
    original_name = str(getattr(entry, "original_name", "") or getattr(entry, "name", "") or "")
    if not original_name.startswith("Pump "):
        return False
    return str(entry.unique_id or "") not in desired_unique_ids


def _is_retired_sensor_binary_entry(entry: er.RegistryEntry) -> bool:
    """Return True for legacy binary sensors that were incorrectly created on the sensor platform."""
    if entry.domain != Platform.SENSOR:
        return False
    original_name = str(getattr(entry, "original_name", "") or getattr(entry, "name", "") or "")
    if original_name in {"Heater", "Sanitise", "Sleeping"}:
        return True
    return original_name.startswith("Pump ")


def _build_entity_key(spa_id: str, name: str) -> str:
    raw = f"{spa_id}_{name}"
    return "".join(char for char in raw if char.isalnum() or char == "_")
