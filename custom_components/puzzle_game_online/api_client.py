"""API client for Puzzle Game Online."""
from __future__ import annotations

import logging
from typing import Any
from datetime import date

import aiohttp
from aiohttp import ClientTimeout

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class PuzzleGameAPIError(Exception):
    """Base exception for API errors."""
    pass


class PuzzleGameAuthError(PuzzleGameAPIError):
    """Authentication error."""
    pass


class PuzzleGameAPI:
    """API client for Puzzle Game Online."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._user_id: str | None = None
        self._username: str | None = None

    @property
    def api_key(self) -> str | None:
        """Return the API key."""
        return self._api_key

    @property
    def user_id(self) -> str | None:
        """Return the user ID."""
        return self._user_id

    @property
    def username(self) -> str | None:
        """Return the username."""
        return self._username

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=API_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the API session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make an API request."""
        session = await self._get_session()
        url = f"{API_BASE_URL}{endpoint}"
        headers = self._get_headers()

        try:
            async with session.request(
                method, url, json=data, params=params, headers=headers
            ) as response:
                if response.status == 401:
                    raise PuzzleGameAuthError("Invalid or expired API key")
                if response.status == 403:
                    raise PuzzleGameAuthError("Access forbidden")

                result = await response.json()

                if response.status >= 400:
                    error_detail = result.get("detail", "Unknown error")
                    raise PuzzleGameAPIError(f"API error: {error_detail}")

                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("API request failed: %s", err)
            raise PuzzleGameAPIError(f"Connection error: {err}") from err

    # ==================== Device Registration ====================

    async def register_device(self, device_name: str) -> dict[str, Any]:
        """Register a new device and get API key."""
        result = await self._request(
            "POST",
            "/auth/register-device",
            data={"device_name": device_name},
        )
        self._api_key = result.get("api_key")
        self._user_id = result.get("user", {}).get("id")
        self._username = result.get("user", {}).get("username")
        return result

    async def set_display_name(self, display_name: str) -> dict[str, Any]:
        """Set the user's display name."""
        result = await self._request(
            "PUT",
            "/users/me",
            data={"display_name": display_name},
        )
        self._username = result.get("display_name") or result.get("username")
        return result

    async def get_current_user(self) -> dict[str, Any]:
        """Get current user info."""
        result = await self._request("GET", "/users/me")
        self._user_id = result.get("id")
        self._username = result.get("display_name") or result.get("username")
        return result

    # ==================== Puzzles ====================

    async def get_daily_puzzle(self, puzzle_date: date | None = None) -> dict[str, Any]:
        """Get today's puzzle."""
        params = {}
        if puzzle_date:
            params["date"] = puzzle_date.isoformat()
        return await self._request("GET", "/puzzles/today", params=params)

    async def get_puzzle_by_id(self, puzzle_id: str) -> dict[str, Any]:
        """Get a specific puzzle by ID."""
        return await self._request("GET", f"/puzzles/{puzzle_id}")

    # ==================== Game Sessions ====================

    async def start_game(self, puzzle_id: str) -> dict[str, Any]:
        """Start a new game session."""
        return await self._request(
            "POST",
            f"/puzzles/{puzzle_id}/start",
        )

    async def check_word(
        self, puzzle_id: str, session_id: str, word_index: int, answer: str
    ) -> dict[str, Any]:
        """Check a word answer."""
        return await self._request(
            "POST",
            f"/puzzles/{puzzle_id}/check",
            data={
                "session_id": session_id,
                "word_index": word_index,
                "answer": answer,
            },
        )

    async def check_theme(
        self, puzzle_id: str, session_id: str, theme_guess: str
    ) -> dict[str, Any]:
        """Check the theme guess."""
        return await self._request(
            "POST",
            f"/puzzles/{puzzle_id}/check-theme",
            data={
                "session_id": session_id,
                "theme_guess": theme_guess,
            },
        )

    async def reveal_letter(
        self, puzzle_id: str, session_id: str, word_index: int
    ) -> dict[str, Any]:
        """Reveal a letter for a word."""
        return await self._request(
            "POST",
            f"/puzzles/{puzzle_id}/reveal",
            data={
                "session_id": session_id,
                "word_index": word_index,
            },
        )

    async def submit_score(
        self,
        puzzle_id: str,
        session_id: str,
        final_score: int,
        time_seconds: int,
        words_solved: int,
        theme_correct: bool,
        wager_amount: int = 0,
    ) -> dict[str, Any]:
        """Submit the final game score."""
        return await self._request(
            "POST",
            "/scores/submit",
            data={
                "puzzle_id": puzzle_id,
                "session_id": session_id,
                "final_score": final_score,
                "time_seconds": time_seconds,
                "words_solved": words_solved,
                "theme_correct": theme_correct,
                "wager_amount": wager_amount,
            },
        )

    # ==================== Leaderboard & Stats ====================

    async def get_leaderboard(
        self,
        period: str = "daily",
        puzzle_date: date | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get leaderboard data."""
        params = {"period": period, "limit": limit}
        if puzzle_date:
            params["date"] = puzzle_date.isoformat()
        return await self._request("GET", "/leaderboard", params=params)

    async def get_my_stats(self) -> dict[str, Any]:
        """Get current user's statistics."""
        return await self._request("GET", "/users/me/stats")

    async def get_my_games(self, limit: int = 10) -> dict[str, Any]:
        """Get current user's recent games."""
        return await self._request(
            "GET", "/users/me/games", params={"limit": limit}
        )

    # ==================== Health Check ====================

    async def check_health(self) -> bool:
        """Check if the API is healthy."""
        try:
            result = await self._request("GET", "/health")
            return result.get("status") == "healthy"
        except Exception:
            return False
