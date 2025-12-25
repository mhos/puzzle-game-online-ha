"""Config flow for Puzzle Game Online integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_USERNAME,
    CONF_EMAIL,
    CONF_DISPLAY_NAME,
    CONF_USER_ID,
)
from .api_client import PuzzleGameAPI, PuzzleGameAPIError

_LOGGER = logging.getLogger(__name__)

# Username validation: 3-30 chars, alphanumeric + underscore
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


def validate_username(username: str) -> str | None:
    """Validate username format. Returns error key or None if valid."""
    if not username:
        return "username_required"
    if len(username) < 3:
        return "username_too_short"
    if len(username) > 30:
        return "username_too_long"
    if not USERNAME_PATTERN.match(username):
        return "username_invalid_chars"
    return None


def validate_email(email: str) -> str | None:
    """Validate email format. Returns error key or None if valid."""
    if not email:
        return "email_required"
    # Basic email validation
    if "@" not in email or "." not in email.split("@")[-1]:
        return "email_invalid"
    return None


def validate_api_key(api_key: str) -> str | None:
    """Validate API key format. Returns error key or None if valid."""
    if not api_key:
        return "api_key_required"
    if not api_key.startswith("pzl_"):
        return "api_key_invalid"
    return None


class PuzzleGameOnlineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Puzzle Game Online."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._user_id: str | None = None
        self._username: str | None = None
        self._email: str | None = None
        self._display_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - choose setup method."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            if user_input.get("setup_method") == "existing":
                return await self.async_step_existing()
            else:
                return await self.async_step_register()

        return self.async_show_menu(
            step_id="user",
            menu_options=["register", "existing"],
        )

    async def async_step_register(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle new account registration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip().lower()
            email = user_input.get(CONF_EMAIL, "").strip().lower()
            display_name = user_input.get(CONF_DISPLAY_NAME, "").strip()

            # Validate inputs
            username_error = validate_username(username)
            if username_error:
                errors[CONF_USERNAME] = username_error

            email_error = validate_email(email)
            if email_error:
                errors[CONF_EMAIL] = email_error

            # Use username as display name if not provided
            if not display_name:
                display_name = username

            if not errors:
                # Store for potential use in recovery step
                self._username = username
                self._email = email
                self._display_name = display_name

                # Register device with API
                api = PuzzleGameAPI()
                try:
                    # Get device info
                    device_info = {
                        "platform": "home_assistant",
                        "version": "1.0.0",
                    }

                    # Register device
                    result = await api.register_device(
                        username=username,
                        email=email,
                        display_name=display_name,
                        device_info=device_info,
                    )

                    self._api_key = result.get("api_key")
                    self._user_id = result.get("user_id")
                    self._username = result.get("username")

                    await api.close()

                    # Create the config entry
                    return self.async_create_entry(
                        title=f"Puzzle Game ({display_name})",
                        data={
                            CONF_API_KEY: self._api_key,
                            CONF_USER_ID: str(self._user_id),
                            CONF_USERNAME: self._username,
                            CONF_EMAIL: email,
                            CONF_DISPLAY_NAME: display_name,
                        },
                    )
                except PuzzleGameAPIError as err:
                    error_msg = str(err)
                    _LOGGER.error("Failed to register device: %s", error_msg)

                    # Check for "already registered" error - offer recovery
                    if "already registered" in error_msg.lower():
                        await api.close()
                        return await self.async_step_recover()
                    else:
                        errors["base"] = "cannot_connect"
                except Exception as err:
                    _LOGGER.exception("Unexpected error during registration: %s", err)
                    errors["base"] = "cannot_connect"
                finally:
                    await api.close()

        return self.async_show_form(
            step_id="register",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_EMAIL): str,
                vol.Optional(CONF_DISPLAY_NAME, default=""): str,
            }),
            errors=errors,
            description_placeholders={
                "api_url": "puzzleapi.techshit.xyz",
            },
        )

    async def async_step_existing(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle setup with existing API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, "").strip()

            # Validate API key format
            api_key_error = validate_api_key(api_key)
            if api_key_error:
                errors[CONF_API_KEY] = api_key_error
            else:
                # Try to validate the API key and get user info
                api = PuzzleGameAPI(api_key)
                try:
                    stats = await api.get_my_stats()
                    await api.close()

                    # Extract user info from stats response
                    username = stats.get("username", "")
                    display_name = stats.get("display_name", username)

                    # API key is valid, create the entry
                    return self.async_create_entry(
                        title=f"Puzzle Game ({display_name})",
                        data={
                            CONF_API_KEY: api_key,
                            CONF_USER_ID: "",
                            CONF_USERNAME: username,
                            CONF_EMAIL: "",
                            CONF_DISPLAY_NAME: display_name,
                        },
                    )
                except PuzzleGameAPIError as err:
                    _LOGGER.error("Invalid API key: %s", err)
                    errors[CONF_API_KEY] = "api_key_invalid"
                except Exception as err:
                    _LOGGER.exception("Error validating API key: %s", err)
                    errors["base"] = "cannot_connect"
                finally:
                    await api.close()

        return self.async_show_form(
            step_id="existing",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
        )

    async def async_step_recover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle recovery step - enter existing API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, "").strip()

            # Validate API key format
            api_key_error = validate_api_key(api_key)
            if api_key_error:
                errors[CONF_API_KEY] = api_key_error
            else:
                # Try to validate the API key
                api = PuzzleGameAPI(api_key)
                try:
                    stats = await api.get_my_stats()
                    await api.close()

                    # API key is valid, create the entry
                    return self.async_create_entry(
                        title=f"Puzzle Game ({self._display_name or self._username})",
                        data={
                            CONF_API_KEY: api_key,
                            CONF_USER_ID: "",  # We don't have this from recovery
                            CONF_USERNAME: self._username or "",
                            CONF_EMAIL: self._email or "",
                            CONF_DISPLAY_NAME: self._display_name or self._username or "",
                        },
                    )
                except PuzzleGameAPIError as err:
                    _LOGGER.error("Invalid API key: %s", err)
                    errors[CONF_API_KEY] = "api_key_invalid"
                except Exception as err:
                    _LOGGER.exception("Error validating API key: %s", err)
                    errors["base"] = "cannot_connect"
                finally:
                    await api.close()

        return self.async_show_form(
            step_id="recover",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "username": self._username or "your account",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PuzzleGameOnlineOptionsFlow:
        """Get the options flow for this handler."""
        return PuzzleGameOnlineOptionsFlow()


class PuzzleGameOnlineOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Puzzle Game Online."""

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
                    await api.update_profile(display_name=new_display_name)
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
        current_api_key = self.config_entry.data.get(CONF_API_KEY, "")

        # Show current API key (masked) and display name
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_DISPLAY_NAME,
                    default=current_display_name
                ): str,
            }),
            errors=errors,
            description_placeholders={
                "api_key": current_api_key,
            },
        )
