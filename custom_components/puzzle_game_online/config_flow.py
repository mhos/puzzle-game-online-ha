"""Config flow for Puzzle Game Online integration."""
from __future__ import annotations

import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_DISPLAY_NAME,
    CONF_USER_ID,
)
from .api_client import PuzzleGameAPI, PuzzleGameAPIError, PuzzleGameAuthError

_LOGGER = logging.getLogger(__name__)


class PuzzleGameOnlineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Puzzle Game Online."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._user_id: str | None = None
        self._username: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - device registration."""
        errors: dict[str, str] = {}

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            display_name = user_input.get(CONF_DISPLAY_NAME, "").strip()
            if not display_name:
                errors[CONF_DISPLAY_NAME] = "display_name_required"
            else:
                # Register device with API
                api = PuzzleGameAPI()
                try:
                    # Generate a unique device name
                    device_name = f"HomeAssistant-{socket.gethostname()}"

                    # Register device
                    result = await api.register_device(device_name)
                    self._api_key = result.get("api_key")
                    self._user_id = result.get("user", {}).get("id")

                    # Set display name
                    await api.set_display_name(display_name)
                    self._username = display_name

                    await api.close()

                    # Create the config entry
                    return self.async_create_entry(
                        title=f"Puzzle Game ({display_name})",
                        data={
                            CONF_API_KEY: self._api_key,
                            CONF_USER_ID: self._user_id,
                            CONF_DISPLAY_NAME: display_name,
                        },
                    )
                except PuzzleGameAPIError as err:
                    _LOGGER.error("Failed to register device: %s", err)
                    errors["base"] = "cannot_connect"
                finally:
                    await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DISPLAY_NAME): str,
            }),
            errors=errors,
            description_placeholders={
                "api_url": "puzzleapi.techshit.xyz",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PuzzleGameOnlineOptionsFlow:
        """Get the options flow for this handler."""
        return PuzzleGameOnlineOptionsFlow(config_entry)


class PuzzleGameOnlineOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Puzzle Game Online."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            new_display_name = user_input.get(CONF_DISPLAY_NAME, "").strip()

            if not new_display_name:
                errors[CONF_DISPLAY_NAME] = "display_name_required"
            else:
                # Update display name via API
                api = PuzzleGameAPI(self.config_entry.data.get(CONF_API_KEY))
                try:
                    await api.set_display_name(new_display_name)
                    await api.close()

                    # Update config entry
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_DISPLAY_NAME] = new_display_name

                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=new_data,
                        title=f"Puzzle Game ({new_display_name})",
                    )

                    return self.async_create_entry(title="", data={})
                except PuzzleGameAPIError as err:
                    _LOGGER.error("Failed to update display name: %s", err)
                    errors["base"] = "cannot_connect"
                finally:
                    await api.close()

        current_display_name = self.config_entry.data.get(CONF_DISPLAY_NAME, "")

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_DISPLAY_NAME,
                    default=current_display_name
                ): str,
            }),
            errors=errors,
        )
