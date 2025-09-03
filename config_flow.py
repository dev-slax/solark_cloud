
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_PLANT_ID, CONF_BASE_URL, DEFAULT_BASE_URL

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_PLANT_ID): str,
    vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # In a first version we don't validate remotely to avoid blocking UI
            return self.async_create_entry(title="Sol-Ark (Cloud)", data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            data = self.config_entry.data.copy()
            data.update(user_input)
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data={})

        defaults = {
            CONF_PLANT_ID: self.config_entry.data.get(CONF_PLANT_ID, ""),
            CONF_BASE_URL: self.config_entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        }
        schema = vol.Schema({
            vol.Optional(CONF_PLANT_ID, default=defaults[CONF_PLANT_ID]): str,
            vol.Optional(CONF_BASE_URL, default=defaults[CONF_BASE_URL]): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
