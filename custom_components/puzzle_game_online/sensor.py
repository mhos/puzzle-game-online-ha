"""Sensor platform for Puzzle Game Online."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_NAME,
    ATTR_GAME_ID,
    ATTR_SESSION_ID,
    ATTR_PHASE,
    ATTR_WORD_NUMBER,
    ATTR_SCORE,
    ATTR_REVEALS,
    ATTR_BLANKS,
    ATTR_CLUE,
    ATTR_SOLVED_WORDS,
    ATTR_IS_ACTIVE,
    ATTR_LAST_MESSAGE,
    ATTR_THEME_REVEALED,
    ATTR_SESSION_ACTIVE,
    ATTR_ACTIVE_SATELLITE,
    ATTR_VIEW_ASSIST_DEVICE,
    ATTR_SPELLING_MODE,
    ATTR_SPELLING_BUFFER,
)
from .coordinator import PuzzleGameCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: PuzzleGameCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([PuzzleGameSensor(coordinator, entry)])


class PuzzleGameSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for Puzzle Game Online."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: PuzzleGameCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_game_state"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": SENSOR_NAME,
            "manufacturer": "Puzzle Game Online",
            "model": "Game State",
        }

    @property
    def native_value(self) -> str:
        """Return the current clue or status."""
        state = self.coordinator.game_state
        if state.get("is_active"):
            return state.get("clue", "Playing...")
        return "Ready to play"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        state = self.coordinator.game_state
        return {
            ATTR_GAME_ID: state.get("game_id"),
            ATTR_SESSION_ID: state.get("session_id"),
            ATTR_PHASE: state.get("phase"),
            ATTR_WORD_NUMBER: state.get("word_number"),
            ATTR_SCORE: state.get("score"),
            ATTR_REVEALS: state.get("reveals"),
            ATTR_BLANKS: state.get("blanks"),
            ATTR_CLUE: state.get("clue"),
            ATTR_SOLVED_WORDS: state.get("solved_words"),
            "solved_word_indices": state.get("solved_word_indices"),
            ATTR_IS_ACTIVE: state.get("is_active"),
            ATTR_LAST_MESSAGE: state.get("last_message"),
            ATTR_THEME_REVEALED: state.get("theme_revealed"),
            ATTR_SESSION_ACTIVE: state.get("session_active"),
            ATTR_ACTIVE_SATELLITE: state.get("active_satellite"),
            ATTR_VIEW_ASSIST_DEVICE: state.get("view_assist_device"),
            ATTR_SPELLING_MODE: state.get("spelling_mode"),
            ATTR_SPELLING_BUFFER: state.get("spelling_buffer"),
        }

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self.coordinator.game_state.get("is_active"):
            return "mdi:puzzle"
        return "mdi:puzzle-outline"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
