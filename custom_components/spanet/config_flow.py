"""Config flow for spanet integration."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import ACCOUNT_UNIQUE_ID_PREFIX, DOMAIN
from .spanet import SpaNet, SpaNetAuthFailed

_LOGGER = logging.getLogger(__name__)


def _normalize_email(email: str) -> str:
    return str(email).strip().lower()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for spanet."""

    VERSION = 1
    STEP_USER_DATA_SCHEMA = vol.Schema(
        {
            vol.Required("email"): str,
            vol.Required("password"): str,
        }
    )


    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=ConfigFlow.STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await ConfigFlow.validate_input(self.hass, user_input)
        except SpaNetAuthFailed:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(info["unique_id"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=info["title"],
                data={
                    **user_input,
                    "email": info["email"],
                },
            )

        return self.async_show_form(
            step_id="user", data_schema=ConfigFlow.STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        self.reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        assert self.reauth_entry is not None

        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=self.add_suggested_values_to_schema(
                    ConfigFlow.STEP_USER_DATA_SCHEMA,
                    {"email": self.reauth_entry.data.get("email", "")},
                ),
            )

        errors = {}
        expected_email = _normalize_email(self.reauth_entry.data.get("email", ""))
        submitted_email = _normalize_email(user_input["email"])
        if submitted_email != expected_email:
            errors["base"] = "wrong_account"
        else:
            try:
                info = await ConfigFlow.validate_input(self.hass, user_input)
            except SpaNetAuthFailed:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self.reauth_entry,
                    data={
                        **self.reauth_entry.data,
                        "email": info["email"],
                        "password": user_input["password"],
                    },
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                ConfigFlow.STEP_USER_DATA_SCHEMA,
                {"email": self.reauth_entry.data.get("email", "")},
            ),
            errors=errors,
        )

    @staticmethod
    async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input allows us to connect.

        Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
        """

        session = aiohttp_client.async_get_clientsession(hass)
        spanet = SpaNet(session)
        email = _normalize_email(data["email"])
        _LOGGER.debug("Validating SpaNET credentials for %s", email)
        await spanet.authenticate(email, data["password"], str(uuid.uuid4()))
        return {
            "title": "SpaNET",
            "email": email,
            "unique_id": f"{ACCOUNT_UNIQUE_ID_PREFIX}{email}",
        }

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

class OptionsFlowHandler(config_entries.OptionsFlow):
    SETTINGS_SCHEMA = vol.Schema(
        {
            vol.Required("enable_heat_pump", default=False): bool,
        }
    )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self.async_step_settings(user_input)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="settings",
            data_schema=self.add_suggested_values_to_schema(
                OptionsFlowHandler.SETTINGS_SCHEMA, self.config_entry.options
            )
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(
                    ConfigFlow.STEP_USER_DATA_SCHEMA,
                    {"email": self.config_entry.data.get("email", "")},
                ),
            )

        errors = {}
        try:
            info = await ConfigFlow.validate_input(self.hass, user_input)
        except SpaNetAuthFailed:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during reconfigure")
            errors["base"] = "unknown"
        else:
            return self.async_update_reload_and_abort(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    "email": info["email"],
                    "password": user_input["password"],
                },
                reason="reconfigure_successful",
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                ConfigFlow.STEP_USER_DATA_SCHEMA,
                {"email": self.config_entry.data.get("email", "")},
            ),
            errors=errors,
        )
