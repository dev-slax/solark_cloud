import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL

from .const import DOMAIN, CONF_PLANT_ID, CONF_BASE_URL, DEFAULT_BASE_URL, DEFAULT_SCAN_INTERVAL, CONF_AUTH_MODE, AUTH_MODE_AUTO, AUTH_MODE_STRICT, AUTH_MODE_LEGACY, CONF_INVERT_GRID_SIGN
from .api import SolarkCloudClient

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_PLANT_ID): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_AUTH_MODE, default=AUTH_MODE_AUTO): vol.In([AUTH_MODE_AUTO, AUTH_MODE_STRICT, AUTH_MODE_LEGACY]),
        vol.Optional(CONF_INVERT_GRID_SIGN, default=False): bool,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = SolarkCloudClient(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_PLANT_ID],
                base_url=user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                auth_mode=user_input.get(CONF_AUTH_MODE, AUTH_MODE_AUTO),
            )
            try:
                # Use /plants like 0.2.0 which worked for you
                await client.get_plants()
                await client.close()
                title = f"Sol-Ark ({user_input[CONF_PLANT_ID]})"
                data = {
                    "username": user_input[CONF_USERNAME],
                    "password": user_input[CONF_PASSWORD],
                    "plant_id": user_input[CONF_PLANT_ID],
                    "base_url": user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                }
                options = {
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    CONF_AUTH_MODE: user_input.get(CONF_AUTH_MODE, AUTH_MODE_AUTO),
                    CONF_INVERT_GRID_SIGN: user_input.get(CONF_INVERT_GRID_SIGN, False),
                }
                return self.async_create_entry(title=title, data=data, options=options)
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        return await self.async_step_user()
