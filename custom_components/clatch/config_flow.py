"""Config flow: ввод токена и profile_id через UI Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import ClatchApiClient, ClatchApiError, ClatchAuthError
from .const import CONF_PROFILE_ID, DEFAULT_NAME, DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("name", default=DEFAULT_NAME): str,
        vol.Required("token"): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(CONF_PROFILE_ID): str,
    }
)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    session = async_get_clientsession(hass)
    client = ClatchApiClient(session, data["token"], data[CONF_PROFILE_ID])
    await client.async_validate()


class ClatchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_PROFILE_ID])
            self._abort_if_unique_id_configured()
            try:
                await _validate_input(self.hass, user_input)
            except ClatchAuthError:
                errors["base"] = "invalid_auth"
            except ClatchApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Неожиданная ошибка в config flow Clatch")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=user_input["name"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return ClatchOptionsFlow()


class ClatchOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            "scan_interval_minutes", DEFAULT_SCAN_INTERVAL_MINUTES
        )
        schema = vol.Schema(
            {
                vol.Required("scan_interval_minutes", default=current): vol.All(
                    int, vol.Range(min=15, max=1440)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
