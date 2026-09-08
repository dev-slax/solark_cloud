from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolarkApiError, SolarkAuthError, SolarkCloudClient
from .const import (
    AUTH_MODE_AUTO,
    AUTH_MODES,
    CONF_AUTH_MODE,
    CONF_INVERT_GRID_SIGN,
    CONF_PLANT_ID,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KNOWN_API_URLS,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PORTAL_URL,
)


def _user_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_PLANT_ID): str,
            vol.Optional(
                CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
            ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            vol.Optional(CONF_AUTH_MODE, default=AUTH_MODE_AUTO): vol.In(AUTH_MODES),
            vol.Optional(CONF_INVERT_GRID_SIGN, default=False): bool,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(
        self,
        username: str,
        password: str,
        plant_id: str,
        auth_mode: str,
    ) -> None:
        client = SolarkCloudClient(
            username,
            password,
            plant_id,
            async_get_clientsession(self.hass),
            api_url=DEFAULT_API_URL,
            origin_url=PORTAL_URL,
            fallback_urls=KNOWN_API_URLS,
            auth_mode=auth_mode,
        )
        # This validates both credentials and the exact Plant ID users entered.
        await client.get_flow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            plant_id = str(user_input[CONF_PLANT_ID]).strip()
            username = str(user_input[CONF_USERNAME]).strip()
            password = str(user_input[CONF_PASSWORD])
            auth_mode = user_input.get(CONF_AUTH_MODE, AUTH_MODE_AUTO)

            if not plant_id or not username or not password:
                errors["base"] = "invalid_input"
            else:
                try:
                    await self._validate(username, password, plant_id, auth_mode)
                except SolarkAuthError:
                    errors["base"] = "invalid_auth"
                except (SolarkApiError, aiohttp.ClientError, TimeoutError):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(plant_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Sol-Ark ({plant_id})",
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_PLANT_ID: plant_id,
                        },
                        options={
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                            CONF_AUTH_MODE: auth_mode,
                            CONF_INVERT_GRID_SIGN: bool(
                                user_input.get(CONF_INVERT_GRID_SIGN, False)
                            ),
                        },
                    )

        return self.async_show_form(
            step_id="user", data_schema=_user_schema(), errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            username = str(user_input[CONF_USERNAME]).strip()
            password = str(user_input[CONF_PASSWORD])
            plant_id = str(entry.data[CONF_PLANT_ID])
            auth_mode = entry.options.get(CONF_AUTH_MODE, AUTH_MODE_AUTO)

            try:
                await self._validate(username, password, plant_id, auth_mode)
            except SolarkAuthError:
                errors["base"] = "invalid_auth"
            except (SolarkApiError, aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                if entry.unique_id is not None:
                    await self.async_set_unique_id(plant_id)
                    self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=entry.data.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
