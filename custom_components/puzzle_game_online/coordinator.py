"""Coordinator for Puzzle Game Online integration."""
from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_state_change_event

from .api_client import PuzzleGameAPI
from .game_manager import GameManager
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PuzzleGameCoordinator(DataUpdateCoordinator):
    """Coordinator for managing puzzle game state."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PuzzleGameAPI,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # We update manually
        )
        self.api = api
        self.game_manager = GameManager(api)
        self._update_listeners: list[Callable[[], None]] = []
        self._stt_unsub: Callable[[], None] | None = None

    @property
    def is_game_active(self) -> bool:
        """Return if a game is currently active."""
        return self.game_manager.state.is_active

    @property
    def game_state(self) -> dict[str, Any]:
        """Return the current game state."""
        state = self.game_manager.state
        reveals_remaining = state.reveals_available - state.reveals_used

        # Get solved word displays
        solved_words_display = []
        for i in state.solved_words:
            if i in state.word_displays:
                solved_words_display.append(state.word_displays[i])

        return {
            "session_id": state.session_id,
            "puzzle_id": state.puzzle_id,
            "phase": state.phase,
            "word_number": state.current_word_index + 1 if state.phase == 1 else 6,
            "score": state.final_score or 0,
            "reveals": reveals_remaining,
            "blanks": self.game_manager.get_current_blanks() if state.phase == 1 else "",
            "clue": self.game_manager.get_current_clue(),
            "solved_words": solved_words_display,
            "solved_word_indices": state.solved_words,
            "is_active": state.is_active,
            "last_message": state.last_message,
            "theme_revealed": state.theme if not state.is_active else None,
            "wager_percent": state.wager_percent,
            "session_active": self.game_manager.session_active,
            "active_satellite": self.game_manager.active_satellite,
            "view_assist_device": self.game_manager.view_assist_device,
            "spelling_mode": self.game_manager.spelling_mode,
            "spelling_buffer": self.game_manager.spelling_buffer,
        }

    async def async_start_game(self, is_bonus: bool = False) -> dict[str, Any]:
        """Start a new game."""
        result = await self.game_manager.start_game(is_bonus)
        await self._notify_update()
        return result

    async def async_submit_answer(self, answer: str) -> dict[str, Any]:
        """Submit an answer."""
        result = await self.game_manager.submit_answer(answer)
        await self._notify_update()
        return result

    async def async_reveal_letter(self) -> dict[str, Any]:
        """Reveal a letter."""
        result = await self.game_manager.reveal_letter()
        await self._notify_update()
        return result

    def skip_word(self) -> dict[str, Any]:
        """Skip the current word."""
        result = self.game_manager.skip_word()
        self.hass.async_create_task(self._notify_update())
        return result

    def repeat_clue(self) -> dict[str, Any]:
        """Get the current clue for repeating."""
        clue = self.game_manager.get_current_clue()
        blanks = self.game_manager.get_current_blanks()
        return {
            "success": True,
            "message": clue,
            "clue": clue,
            "blanks": blanks,
        }

    def start_spelling(self) -> dict[str, Any]:
        """Enter spelling mode."""
        result = self.game_manager.start_spelling()
        self.hass.async_create_task(self._notify_update())
        return result

    def add_letter(self, letter: str) -> dict[str, Any]:
        """Add a letter in spelling mode."""
        result = self.game_manager.add_letter(letter)
        self.hass.async_create_task(self._notify_update())
        return result

    async def async_finish_spelling(self, text: str | None = None) -> dict[str, Any]:
        """Finish spelling and submit."""
        result = await self.game_manager.finish_spelling(text)
        await self._notify_update()
        return result

    def cancel_spelling(self) -> dict[str, Any]:
        """Cancel spelling mode."""
        result = self.game_manager.cancel_spelling()
        self.hass.async_create_task(self._notify_update())
        return result

    async def async_give_up(self) -> dict[str, Any]:
        """Give up the current game."""
        result = await self.game_manager.give_up()
        await self._notify_update()
        return result

    def set_wager(self, percent: int) -> dict[str, Any]:
        """Set the wager percentage."""
        result = self.game_manager.set_wager(percent)
        self.hass.async_create_task(self._notify_update())
        return result

    def set_session(
        self,
        active: bool,
        satellite: str | None = None,
        view_assist_device: str | None = None,
    ) -> None:
        """Set session state."""
        self.game_manager.set_session(active, satellite, view_assist_device)

        if active and satellite:
            # Derive STT sensor from satellite name and start watching
            device_name = satellite.split('.')[1] if '.' in satellite else satellite
            stt_sensor = f"sensor.{device_name}_stt"
            self._start_stt_watch(stt_sensor)
        elif not active:
            # Stop watching STT when session ends
            self._stop_stt_watch()

        self.hass.async_create_task(self._notify_update())

    def _start_stt_watch(self, stt_sensor: str) -> None:
        """Start watching the STT sensor for changes."""
        # Stop any existing watch first
        self._stop_stt_watch()

        @callback
        def _stt_state_changed(event: Event) -> None:
            """Handle STT sensor state change."""
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")

            if new_state is None:
                return

            new_value = new_state.state
            old_value = old_state.state if old_state else ""

            # Only fire event if there's actual speech content and it changed
            if new_value and len(new_value) > 0 and new_value != old_value:
                # Fire custom event for the blueprint to catch
                self.hass.bus.async_fire(f"{DOMAIN}_speech", {
                    "entity_id": stt_sensor,
                    "text": new_value,
                    "old_text": old_value,
                })
                _LOGGER.info("Fired %s_speech event: %s", DOMAIN, new_value)

        self._stt_unsub = async_track_state_change_event(
            self.hass, [stt_sensor], _stt_state_changed
        )
        _LOGGER.info("Started watching STT sensor: %s", stt_sensor)

    def _stop_stt_watch(self) -> None:
        """Stop watching the STT sensor."""
        if self._stt_unsub:
            self._stt_unsub()
            self._stt_unsub = None
            _LOGGER.info("Stopped watching STT sensor")

    def handle_timeout(self) -> dict[str, Any]:
        """Handle listening timeout."""
        result = self.game_manager.handle_timeout()
        self.hass.async_create_task(self._notify_update())
        return result

    def reset_timeout(self) -> None:
        """Reset timeout counter."""
        self.game_manager.reset_timeout()

    # ==================== Stats & Leaderboard ====================

    async def async_get_leaderboard(
        self, period: str = "daily", limit: int = 20
    ) -> dict[str, Any]:
        """Get leaderboard data."""
        return await self.api.get_leaderboard(period=period, limit=limit)

    async def async_get_my_stats(self) -> dict[str, Any]:
        """Get current user's stats."""
        return await self.api.get_my_stats()

    async def async_get_my_games(self, limit: int = 10) -> dict[str, Any]:
        """Get user's recent games."""
        return await self.api.get_my_games(limit=limit)

    async def async_get_user_info(self) -> dict[str, Any]:
        """Get current user info."""
        return await self.api.get_current_user()

    # ==================== Update Notifications ====================

    @callback
    def add_update_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Add a listener for state updates."""
        self._update_listeners.append(listener)

        @callback
        def remove_listener() -> None:
            self._update_listeners.remove(listener)

        return remove_listener

    async def _notify_update(self) -> None:
        """Notify all listeners of state update."""
        self.async_set_updated_data(self.game_state)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        return self.game_state
