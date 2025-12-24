"""API client for Puzzle Game Online."""
from __future__ import annotations

import logging
from typing import Any
import urllib.parse

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

    @property
    def api_key(self) -> str | None:
        """Return the API key."""
        return self._api_key

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
            self._session = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
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
                    error_detail = result.get("detail", str(result))
                    raise PuzzleGameAPIError(f"API error: {error_detail}")

                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("API request failed: %s", err)
            raise PuzzleGameAPIError(f"Connection error: {err}") from err

    # ==================== Authentication ====================

    async def register_device(
        self,
        username: str,
        email: str,
        display_name: str | None = None,
        device_info: dict | None = None,
    ) -> dict[str, Any]:
        """
        Register a new device/user with the API.

        Args:
            username: Unique username (3-30 chars, alphanumeric + underscore)
            email: User's email address
            display_name: Optional display name for leaderboards
            device_info: Optional device information

        Returns:
            {api_key, user_id, username, message}
        """
        data = {
            "username": username,
            "email": email,
        }
        if display_name:
            data["display_name"] = display_name
        if device_info:
            data["device_info"] = device_info

        result = await self._request("POST", "/auth/register-device", data=data)
        # Store the API key for future requests
        self._api_key = result.get("api_key")
        return result

    async def get_current_user(self) -> dict[str, Any]:
        """Get the current authenticated user's info."""
        return await self._request("GET", "/auth/me")

    # ==================== Puzzles ====================

    async def get_daily_puzzle(self, puzzle_date: str | None = None) -> dict[str, Any]:
        """
        Get today's daily puzzle (or a specific date).

        Args:
            puzzle_date: Optional date string (YYYY-MM-DD)

        Returns:
            {id, puzzle_date, difficulty, is_bonus, words: [{clue, length}]}
        """
        params = {}
        if puzzle_date:
            params["puzzle_date"] = puzzle_date
        return await self._request("GET", "/puzzle/daily", params=params)

    async def get_bonus_puzzle(self) -> dict[str, Any]:
        """
        Get a random unplayed bonus puzzle.

        Returns:
            {id, puzzle_date, difficulty, is_bonus, words: [{clue, length}]}
        """
        return await self._request("GET", "/puzzle/bonus")

    async def get_puzzle_by_id(self, puzzle_id: str) -> dict[str, Any]:
        """Get a specific puzzle by ID."""
        return await self._request("GET", f"/puzzle/{puzzle_id}")

    async def start_game(self, puzzle_id: str) -> dict[str, Any]:
        """
        Start a new game session for a puzzle.

        Returns:
            {session_id, puzzle_id, status, reveals_available, solved_words, theme_solved}
        """
        return await self._request("POST", f"/puzzle/{puzzle_id}/start")

    async def get_session_status(self, puzzle_id: str) -> dict[str, Any]:
        """
        Get the current session status for a puzzle.

        Returns:
            {session_id, puzzle_id, status, reveals_used, reveals_available,
             revealed_letters, solved_words, theme_solved}
        """
        return await self._request("GET", f"/puzzle/{puzzle_id}/session")

    async def check_word(
        self, puzzle_id: str, word_index: int, answer: str
    ) -> dict[str, Any]:
        """
        Check if an answer is correct for a specific word.

        Args:
            puzzle_id: The puzzle ID
            word_index: Index of the word (0-4)
            answer: The answer to check

        Returns:
            {correct, words_solved?, reveals_earned?, attempts_remaining?, already_solved?}
        """
        # URL encode the answer to handle spaces and special characters
        encoded_answer = urllib.parse.quote(answer, safe='')
        return await self._request(
            "GET", f"/puzzle/{puzzle_id}/check/{word_index}/{encoded_answer}"
        )

    async def check_theme(self, puzzle_id: str, answer: str) -> dict[str, Any]:
        """
        Check if the theme guess is correct.

        Args:
            puzzle_id: The puzzle ID
            answer: The theme guess

        Returns:
            {correct, attempts_remaining?, already_solved?}
        """
        encoded_answer = urllib.parse.quote(answer, safe='')
        return await self._request("GET", f"/puzzle/{puzzle_id}/check-theme/{encoded_answer}")

    async def reveal_letter(
        self, puzzle_id: str, word_index: int, letter_index: int
    ) -> dict[str, Any]:
        """
        Reveal a single letter from a word.

        Args:
            puzzle_id: The puzzle ID
            word_index: Index of the word (0-4)
            letter_index: Index of the letter to reveal

        Returns:
            {letter, index, reveals_used, reveals_remaining, already_revealed?}
        """
        return await self._request(
            "GET",
            f"/puzzle/{puzzle_id}/reveal/{word_index}",
            params={"letter_index": letter_index},
        )

    # ==================== Scores ====================

    async def submit_score(
        self,
        puzzle_id: str,
        word_results: list[dict],
        time_seconds: int,
        theme_correct: bool | None = None,
        wager_percent: int = 0,
    ) -> dict[str, Any]:
        """
        Submit a completed game score.

        Args:
            puzzle_id: The puzzle ID
            word_results: List of {solved: bool, reveals_used: int} for each of 5 words
            time_seconds: Total time taken
            theme_correct: Whether the theme was guessed correctly
            wager_percent: Percentage of score to wager (0-100)

        Returns:
            {game_id, final_score, word_score, reveals_bonus, time_bonus,
             wager_result, rank, percentile, total_players}
        """
        data = {
            "puzzle_id": puzzle_id,
            "word_results": word_results,
            "time_seconds": time_seconds,
            "client_version": "1.0.0",
        }
        if theme_correct is not None:
            data["theme_correct"] = theme_correct
        if wager_percent > 0:
            data["wager_percent"] = wager_percent

        return await self._request("POST", "/score/submit", data=data)

    async def get_my_score(self, puzzle_id: str) -> dict[str, Any]:
        """Get my score for a specific puzzle."""
        return await self._request("GET", f"/score/puzzle/{puzzle_id}")

    # ==================== Leaderboard ====================

    async def get_leaderboard(
        self, period: str = "daily", limit: int = 100
    ) -> dict[str, Any]:
        """
        Get the leaderboard for a specific period.

        Args:
            period: daily, weekly, monthly, alltime
            limit: Maximum entries to return

        Returns:
            {period, entries: [{rank, user_id, username, display_name, score, ...}],
             total_players, your_rank?, your_percentile?}
        """
        return await self._request(
            "GET", f"/leaderboard/{period}", params={"limit": limit}
        )

    # ==================== User ====================

    async def get_my_stats(self) -> dict[str, Any]:
        """
        Get the current user's statistics.

        Returns:
            {games_played, total_score, avg_score, best_score, worst_score,
             perfect_games, total_words_solved, total_themes_correct,
             avg_time_seconds, fastest_time_seconds, current_streak, longest_streak, ...}
        """
        return await self._request("GET", "/user/stats")

    async def get_my_history(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """
        Get the current user's game history.

        Args:
            limit: Maximum games to return
            offset: Offset for pagination

        Returns:
            {games: [{id, puzzle_date, final_score, words_solved, theme_correct,
                      time_seconds, completed_at}], total, limit, offset}
        """
        return await self._request(
            "GET", "/user/history", params={"limit": limit, "offset": offset}
        )

    async def update_profile(
        self,
        display_name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        """
        Update the current user's profile.

        Returns:
            {id, username, email, display_name}
        """
        params = {}
        if display_name is not None:
            params["display_name"] = display_name
        if email is not None:
            params["email"] = email
        return await self._request("PATCH", "/user/profile", params=params)

    async def get_user_profile(self, username: str) -> dict[str, Any]:
        """Get a user's public profile."""
        return await self._request("GET", f"/user/{username}")

    # ==================== Health Check ====================

    async def check_health(self) -> bool:
        """Check if the API is healthy."""
        try:
            session = await self._get_session()
            async with session.get(f"{API_BASE_URL}/health") as response:
                return response.status == 200
        except Exception:
            return False
