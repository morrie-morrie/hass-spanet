"""Service handlers for SpaNET."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

SERVICE_SET_LIGHT_MODE = "set_light_mode"
SERVICE_SET_LIGHT_COLOUR = "set_light_colour"
SERVICE_CREATE_SLEEP_TIMER = "create_sleep_timer"
SERVICE_UPDATE_SLEEP_TIMER = "update_sleep_timer"
SERVICE_DELETE_SLEEP_TIMER = "delete_sleep_timer"
SERVICE_SET_SANITISE_STATUS = "set_sanitise_status"


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

    async def handle_create_sleep_timer(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.create_sleep_timer(
            timer_number=call.data["timer_number"],
            timer_name=call.data["timer_name"],
            start_time=call.data["start_time"],
            end_time=call.data["end_time"],
            days_hex=call.data["days_hex"],
            is_enabled=call.data.get("is_enabled", True),
        )

    async def handle_update_sleep_timer(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.update_sleep_timer(
            timer_id=call.data["timer_id"],
            timer_number=call.data["timer_number"],
            timer_name=call.data["timer_name"],
            start_time=call.data["start_time"],
            end_time=call.data["end_time"],
            days_hex=call.data["days_hex"],
            is_enabled=call.data.get("is_enabled", True),
        )

    async def handle_delete_sleep_timer(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.delete_sleep_timer(call.data["timer_id"])

    async def handle_set_sanitise_status(call: ServiceCall):
        coordinator = _find_coordinator(hass, str(call.data["spa_id"]))
        if coordinator is None:
            raise ValueError(f"Spa id {call.data['spa_id']} not found")
        await coordinator.set_sanitiser("on" if call.data["on"] else "off")

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
        SERVICE_CREATE_SLEEP_TIMER,
        handle_create_sleep_timer,
        schema=spa_id_required.extend(
            {
                vol.Required("timer_number"): int,
                vol.Required("timer_name"): str,
                vol.Required("start_time"): str,
                vol.Required("end_time"): str,
                vol.Required("days_hex"): str,
                vol.Optional("is_enabled", default=True): bool,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_SLEEP_TIMER,
        handle_update_sleep_timer,
        schema=spa_id_required.extend(
            {
                vol.Required("timer_id"): int,
                vol.Required("timer_number"): int,
                vol.Required("timer_name"): str,
                vol.Required("start_time"): str,
                vol.Required("end_time"): str,
                vol.Required("days_hex"): str,
                vol.Optional("is_enabled", default=True): bool,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_SLEEP_TIMER,
        handle_delete_sleep_timer,
        schema=spa_id_required.extend({vol.Required("timer_id"): int}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SANITISE_STATUS,
        handle_set_sanitise_status,
        schema=spa_id_required.extend({vol.Required("on"): bool}),
    )


async def async_unregister_services(hass: HomeAssistant):
    for service_name in (
        SERVICE_SET_LIGHT_MODE,
        SERVICE_SET_LIGHT_COLOUR,
        SERVICE_CREATE_SLEEP_TIMER,
        SERVICE_UPDATE_SLEEP_TIMER,
        SERVICE_DELETE_SLEEP_TIMER,
        SERVICE_SET_SANITISE_STATUS,
    ):
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)
