"""Runtime data helpers for SpaNET config entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import Coordinator
    from .spanet import SpaNet


@dataclass
class SpaNetRuntimeData:
    """Runtime data stored on a SpaNET config entry."""

    client: "SpaNet | None"
    coordinators: list["Coordinator"] = field(default_factory=list)


def get_entry_runtime_data(hass: HomeAssistant, config_entry: ConfigEntry) -> SpaNetRuntimeData:
    """Return runtime data for a config entry."""

    runtime_data = getattr(config_entry, "runtime_data", None)
    if isinstance(runtime_data, SpaNetRuntimeData):
        return runtime_data

    legacy = hass.data.get(DOMAIN, {}).get(config_entry.entry_id)
    if isinstance(legacy, SpaNetRuntimeData):
        return legacy
    if isinstance(legacy, dict):
        return SpaNetRuntimeData(
            client=legacy.get("client"),
            coordinators=list(legacy.get("coordinators", [])),
        )
    return SpaNetRuntimeData(client=None)


def get_entry_coordinators(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> list["Coordinator"]:
    """Return coordinators for a config entry."""

    return get_entry_runtime_data(hass, config_entry).coordinators


def iter_runtime_data(hass: HomeAssistant):
    """Yield runtime data objects across loaded SpaNET entries."""

    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, SpaNetRuntimeData):
            yield entry_data
        elif isinstance(entry_data, dict):
            yield SpaNetRuntimeData(
                client=entry_data.get("client"),
                coordinators=list(entry_data.get("coordinators", [])),
            )
