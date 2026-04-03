"""Service handlers for SpaNET."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

SERVICE_SET_LIGHT_MODE = "set_light_mode"
SERVICE_SET_LIGHT_COLOUR = "set_light_colour"
SERVICE_SET_LIGHT_SPEED = "set_light_speed"
SERVICE_SET_BLOWER_MODE = "set_blower_mode"
SERVICE_SET_BLOWER_SPEED = "set_blower_speed"


def _find_coordinator(hass: HomeAssistant, spa_id: str):
    domain_data = hass.data.get(DOMAIN, {})
    for entry_data in domain_data.values():
        if not isinstance(entry_data, dict):
            continue
        for coordinator in entry_data.get("coordinators", []):
            if coordinator.spa_id == str(spa_id):
                return coordinator
    return None


async def async_register_services(hass: HomeAssistant):
    if hass.services.has_service(DOMAIN, SERVICE_SET_LIGHT_MODE):
        return

    async def handle_set_light_mode(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.set_light_mode(call.data["mode"])

    async def handle_set_light_colour(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.set_light_colour(call.data["colour"])

    async def handle_set_light_speed(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.set_light_speed(call.data["speed"])

    async def handle_set_blower_mode(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.set_blower(call.data["mode"])

    async def handle_set_blower_speed(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.set_blower_speed(call.data["speed"])

    spa_id_required = vol.Schema({vol.Required("spa_id"): vol.Any(str, int)})

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LIGHT_MODE,
        handle_set_light_mode,
        schema=spa_id_required.extend({vol.Required("mode"): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LIGHT_COLOUR,
        handle_set_light_colour,
        schema=spa_id_required.extend({vol.Required("colour"): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LIGHT_SPEED,
        handle_set_light_speed,
        schema=spa_id_required.extend({vol.Required("speed"): vol.All(int, vol.Range(min=1, max=5))}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BLOWER_MODE,
        handle_set_blower_mode,
        schema=spa_id_required.extend(
            {vol.Required("mode"): vol.In(["off", "ramp", "variable"])}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BLOWER_SPEED,
        handle_set_blower_speed,
        schema=spa_id_required.extend({vol.Required("speed"): vol.All(int, vol.Range(min=1, max=5))}),
    )

async def async_unregister_services(hass: HomeAssistant):
    for service_name in (
        SERVICE_SET_LIGHT_MODE,
        SERVICE_SET_LIGHT_COLOUR,
        SERVICE_SET_LIGHT_SPEED,
        SERVICE_SET_BLOWER_MODE,
        SERVICE_SET_BLOWER_SPEED,
    ):
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)
