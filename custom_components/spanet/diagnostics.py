"""Diagnostics support for SpaNET."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .runtime_data import get_entry_runtime_data

REDACT_CONFIG_KEYS = {"email", "password"}
REDACT_STATE_KEYS = {
    "apiId",
    "id",
    "access_token",
    "refresh_token",
    "macAddress",
}


def _redact_mapping(value: Any, redact_keys: set[str]) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in redact_keys:
                redacted[key] = "**REDACTED**"
            else:
                redacted[key] = _redact_mapping(item, redact_keys)
        return redacted
    if isinstance(value, list):
        return [_redact_mapping(item, redact_keys) for item in value]
    return value


def _serialize_rate_limit(client: Any) -> dict[str, Any]:
    rate_limit = getattr(client, "rate_limit", None)
    if not isinstance(rate_limit, Mapping):
        return {}

    result: dict[str, Any] = {}
    if "limit" in rate_limit:
        result["limit"] = rate_limit["limit"]
    if "remaining" in rate_limit:
        result["remaining"] = rate_limit["remaining"]
    reset_at = rate_limit.get("reset_at")
    if isinstance(reset_at, (int, float)):
        result["reset"] = datetime.fromtimestamp(reset_at, tz=timezone.utc).isoformat()
    return result


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry_data = get_entry_runtime_data(hass, config_entry)
    registry = er.async_get(hass)
    entities = [
        entry.entity_id
        for entry in er.async_entries_for_config_entry(registry, config_entry.entry_id)
        if entry.platform == DOMAIN
    ]

    coordinators = []
    for coordinator in entry_data.coordinators:
        coordinators.append(
            {
                "spa_id": coordinator.spa_id,
                "spa_name": coordinator.spa_name,
                "state": _redact_mapping(deepcopy(coordinator.state), REDACT_STATE_KEYS),
            }
        )

    return {
        "config_entry": {
            "entry_id": config_entry.entry_id,
            "title": config_entry.title,
            "data": _redact_mapping(dict(config_entry.data), REDACT_CONFIG_KEYS),
            "options": dict(config_entry.options),
        },
        "rate_limit": _serialize_rate_limit(entry_data.client),
        "entities": entities,
        "coordinators": coordinators,
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a single SpaNET device."""
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    identifiers = {identifier for identifier in device.identifiers if identifier[0] == DOMAIN}
    spa_ids = {identifier[1] for identifier in identifiers}
    diagnostics["device"] = {
        "id": device.id,
        "name": device.name,
        "identifiers": list(identifiers),
    }
    diagnostics["coordinators"] = [
        item for item in diagnostics["coordinators"] if item.get("spa_id") in spa_ids
    ]
    return diagnostics
