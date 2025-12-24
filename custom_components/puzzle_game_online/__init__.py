"""Puzzle Game Online integration for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig

from .const import (
    DOMAIN,
    VERSION,
    CONF_API_KEY,
    CONF_DISPLAY_NAME,
    PANEL_URL,
    PANEL_TITLE,
    PANEL_ICON,
    SERVICE_START_GAME,
    SERVICE_SUBMIT_ANSWER,
    SERVICE_REVEAL_LETTER,
    SERVICE_SKIP_WORD,
    SERVICE_REPEAT_CLUE,
    SERVICE_START_SPELLING,
    SERVICE_ADD_LETTER,
    SERVICE_FINISH_SPELLING,
    SERVICE_CANCEL_SPELLING,
    SERVICE_GIVE_UP,
    SERVICE_SET_SESSION,
    SERVICE_LISTENING_TIMEOUT,
    SERVICE_RESET_TIMEOUT,
)
from .api_client import PuzzleGameAPI
from .coordinator import PuzzleGameCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Puzzle Game Online from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize API client
    api = PuzzleGameAPI(entry.data.get(CONF_API_KEY))

    # Validate API connection by checking user stats (uses API key auth)
    try:
        await api.get_my_stats()
    except Exception as err:
        _LOGGER.error("Failed to connect to API: %s", err)
        await api.close()
        return False

    # Create coordinator
    coordinator = PuzzleGameCoordinator(hass, api)

    # Store references
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_setup_services(hass, coordinator)

    # Register frontend panel
    await _async_register_panel(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api"].close()

        # Remove panel if no more entries
        if not hass.data[DOMAIN]:
            frontend.async_remove_panel(hass, DOMAIN)

    return unload_ok


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the frontend panel."""
    # Get path to panel.js
    panel_path = Path(__file__).parent / "frontend" / "panel.js"

    if not panel_path.exists():
        _LOGGER.warning("Panel file not found: %s", panel_path)
        return

    # Register static path
    panel_url = f"/puzzle_game_online/panel-{VERSION}.js"

    await hass.http.async_register_static_paths([
        StaticPathConfig(panel_url, str(panel_path), cache_headers=True)
    ])

    # Register panel
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=DOMAIN,
        config={
            "_panel_custom": {
                "name": "puzzle-game-online-panel",
                "module_url": panel_url,
            }
        },
        require_admin=False,
    )


async def _async_setup_services(
    hass: HomeAssistant, coordinator: PuzzleGameCoordinator
) -> None:
    """Set up services."""

    async def handle_start_game(call: ServiceCall) -> None:
        """Handle start game service."""
        is_bonus = call.data.get("bonus", False)
        result = await coordinator.async_start_game(is_bonus)
        _fire_result_event(hass, "game_started", result)

    async def handle_submit_answer(call: ServiceCall) -> None:
        """Handle submit answer service."""
        answer = call.data.get("answer", "")
        result = await coordinator.async_submit_answer(answer)
        _fire_result_event(hass, "answer_submitted", result)

    async def handle_reveal_letter(call: ServiceCall) -> None:
        """Handle reveal letter service."""
        result = await coordinator.async_reveal_letter()
        _fire_result_event(hass, "letter_revealed", result)

    async def handle_skip_word(call: ServiceCall) -> None:
        """Handle skip word service."""
        result = coordinator.skip_word()
        _fire_result_event(hass, "word_skipped", result)

    async def handle_repeat_clue(call: ServiceCall) -> None:
        """Handle repeat clue service."""
        result = coordinator.repeat_clue()
        _fire_result_event(hass, "clue_repeated", result)

    async def handle_start_spelling(call: ServiceCall) -> None:
        """Handle start spelling service."""
        result = coordinator.start_spelling()
        _fire_result_event(hass, "spelling_started", result)

    async def handle_add_letter(call: ServiceCall) -> None:
        """Handle add letter service."""
        letter = call.data.get("letter", "")
        result = coordinator.add_letter(letter)
        _fire_result_event(hass, "letter_added", result)

    async def handle_finish_spelling(call: ServiceCall) -> None:
        """Handle finish spelling service."""
        text = call.data.get("text")
        result = await coordinator.async_finish_spelling(text)
        _fire_result_event(hass, "spelling_finished", result)

    async def handle_cancel_spelling(call: ServiceCall) -> None:
        """Handle cancel spelling service."""
        result = coordinator.cancel_spelling()
        _fire_result_event(hass, "spelling_cancelled", result)

    async def handle_give_up(call: ServiceCall) -> None:
        """Handle give up service."""
        result = await coordinator.async_give_up()
        _fire_result_event(hass, "game_ended", result)

    async def handle_set_session(call: ServiceCall) -> None:
        """Handle set session service."""
        coordinator.set_session(
            active=call.data.get("active", False),
            satellite=call.data.get("satellite"),
            view_assist_device=call.data.get("view_assist_device"),
        )

    async def handle_listening_timeout(call: ServiceCall) -> None:
        """Handle listening timeout service."""
        result = coordinator.handle_timeout()
        _fire_result_event(hass, "timeout", result)

    async def handle_reset_timeout(call: ServiceCall) -> None:
        """Handle reset timeout service."""
        coordinator.reset_timeout()

    # Register all services
    hass.services.async_register(
        DOMAIN, SERVICE_START_GAME, handle_start_game,
        schema=vol.Schema({vol.Optional("bonus", default=False): cv.boolean}),
    )

    hass.services.async_register(
        DOMAIN, SERVICE_SUBMIT_ANSWER, handle_submit_answer,
        schema=vol.Schema({vol.Required("answer"): cv.string}),
    )

    hass.services.async_register(
        DOMAIN, SERVICE_REVEAL_LETTER, handle_reveal_letter,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_SKIP_WORD, handle_skip_word,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_REPEAT_CLUE, handle_repeat_clue,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_START_SPELLING, handle_start_spelling,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_LETTER, handle_add_letter,
        schema=vol.Schema({vol.Required("letter"): cv.string}),
    )

    hass.services.async_register(
        DOMAIN, SERVICE_FINISH_SPELLING, handle_finish_spelling,
        schema=vol.Schema({vol.Optional("text"): cv.string}),
    )

    hass.services.async_register(
        DOMAIN, SERVICE_CANCEL_SPELLING, handle_cancel_spelling,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_GIVE_UP, handle_give_up,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_SESSION, handle_set_session,
        schema=vol.Schema({
            vol.Required("active"): cv.boolean,
            vol.Optional("satellite"): cv.string,
            vol.Optional("view_assist_device"): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN, SERVICE_LISTENING_TIMEOUT, handle_listening_timeout,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_RESET_TIMEOUT, handle_reset_timeout,
    )


def _fire_result_event(hass: HomeAssistant, event_type: str, data: dict[str, Any]) -> None:
    """Fire an event with result data."""
    hass.bus.async_fire(f"{DOMAIN}_{event_type}", data)
