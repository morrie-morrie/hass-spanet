"""The SpaNET integration."""

from __future__ import annotations

import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr

from .const import DEVICE_ID, DOMAIN
from .coordinator import Coordinator
from .services import async_register_services, async_unregister_services
from .spanet import SpaNet

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TIME,
    Platform.DATETIME,
    Platform.LIGHT,
]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up SpaNET from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    domain_data = hass.data[DOMAIN]
    domain_data.setdefault(DEVICE_ID, str(uuid.uuid4()))

    session = aiohttp_client.async_get_clientsession(hass)
    spanet = SpaNet(session)

    entry_data = {"client": spanet, "coordinators": []}
    hass.data[DOMAIN][config_entry.entry_id] = entry_data

    if "email" not in config_entry.data or "password" not in config_entry.data:
        await async_register_services(hass)
        return True

    await spanet.authenticate(
        config_entry.data["email"],
        config_entry.data["password"],
        domain_data[DEVICE_ID],
    )

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
        entry_data["coordinators"].append(coordinator)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    await async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        has_entries = any(
            key != DEVICE_ID and isinstance(value, dict)
            for key, value in hass.data.get(DOMAIN, {}).items()
        )
        if not has_entries:
            await async_unregister_services(hass)
    return unload_ok
