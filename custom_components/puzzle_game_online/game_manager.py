"""Game manager for Puzzle Game Online."""
from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any

from .api_client import PuzzleGameAPI, PuzzleGameAPIError
from .const import WORDS_PER_PUZZLE, BASE_REVEALS

_LOGGER = logging.getLogger(__name__)


class GameState:
    """Represents the current game state."""

    def __init__(self) -> None:
        """Initialize game state."""
        self.game_id: str | None = None
        self.session_id: str | None = None
        self.puzzle_id: str | None = None
        self.puzzle_date: date | None = None

        # Puzzle data
        self.theme: str = ""
        self.words: list[str] = []
        self.clues: list[str] = []

        # Game progress
        self.phase: int = 1  # 1 = solving words, 2 = guessing theme
        self.current_word_index: int = 0
        self.score: int = 0
        self.reveals_remaining: int = BASE_REVEALS
        self.reveals_earned: int = 0

        # Tracking
        self.solved_words: list[int] = []  # Indices of solved words
        self.skipped_words: list[int] = []  # Indices of skipped words
        self.revealed_letters: dict[int, list[int]] = {}  # word_index -> letter positions
        self.theme_revealed_letters: list[int] = []

        # Status
        self.is_active: bool = False
        self.gave_up: bool = False
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

        # Last feedback
        self.last_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "game_id": self.game_id,
            "session_id": self.session_id,
            "puzzle_id": self.puzzle_id,
            "puzzle_date": self.puzzle_date.isoformat() if self.puzzle_date else None,
            "theme": self.theme,
            "words": self.words,
            "clues": self.clues,
            "phase": self.phase,
            "current_word_index": self.current_word_index,
            "score": self.score,
            "reveals_remaining": self.reveals_remaining,
            "reveals_earned": self.reveals_earned,
            "solved_words": self.solved_words,
            "skipped_words": self.skipped_words,
            "revealed_letters": self.revealed_letters,
            "theme_revealed_letters": self.theme_revealed_letters,
            "is_active": self.is_active,
            "gave_up": self.gave_up,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_message": self.last_message,
        }

    def reset(self) -> None:
        """Reset the game state."""
        self.__init__()


class GameManager:
    """Manages puzzle game logic with online API."""

    def __init__(self, api: PuzzleGameAPI) -> None:
        """Initialize the game manager."""
        self._api = api
        self.state = GameState()

        # Voice session tracking
        self.session_active: bool = False
        self.active_satellite: str | None = None
        self.view_assist_device: str | None = None

        # Spelling mode
        self.spelling_mode: bool = False
        self.spelling_buffer: list[str] = []

        # Timeout tracking
        self.timeout_count: int = 0

    async def start_game(self, is_bonus: bool = False) -> dict[str, Any]:
        """Start a new game."""
        try:
            # Get today's puzzle
            puzzle_data = await self._api.get_daily_puzzle()
            puzzle_id = puzzle_data.get("id")

            if not puzzle_id:
                return {"success": False, "message": "No puzzle available today"}

            # Start a game session
            session_data = await self._api.start_game(puzzle_id)

            # Initialize game state
            self.state.reset()
            self.state.game_id = session_data.get("game_id")
            self.state.session_id = session_data.get("session_id")
            self.state.puzzle_id = puzzle_id
            self.state.puzzle_date = date.today()

            # Store puzzle data
            self.state.theme = puzzle_data.get("theme", "")
            self.state.words = [w.get("word", "") for w in puzzle_data.get("words", [])]
            self.state.clues = [w.get("clue", "") for w in puzzle_data.get("words", [])]

            # Set initial reveals from session
            self.state.reveals_remaining = session_data.get("reveals_remaining", BASE_REVEALS)

            # Mark as active
            self.state.is_active = True
            self.state.started_at = datetime.now()
            self.state.phase = 1
            self.state.current_word_index = 0

            # Build initial message
            first_clue = self.state.clues[0] if self.state.clues else "No clue available"
            message = f"Let's play! Word 1 of 5. {first_clue}"
            self.state.last_message = message

            return {
                "success": True,
                "message": message,
                "blanks": self.get_current_blanks(),
                "clue": first_clue,
            }

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to start game: %s", err)
            return {"success": False, "message": f"Failed to start game: {err}"}

    async def submit_answer(self, answer: str) -> dict[str, Any]:
        """Submit an answer for the current word or theme."""
        if not self.state.is_active:
            return {"success": False, "message": "No active game"}

        answer = answer.strip().upper()

        if self.state.phase == 1:
            return await self._submit_word_answer(answer)
        else:
            return await self._submit_theme_answer(answer)

    async def _submit_word_answer(self, answer: str) -> dict[str, Any]:
        """Submit a word answer."""
        word_index = self.state.current_word_index

        try:
            result = await self._api.check_word(
                self.state.puzzle_id,
                self.state.session_id,
                word_index,
                answer,
            )

            is_correct = result.get("correct", False)

            if is_correct:
                # Update state
                self.state.solved_words.append(word_index)
                points = result.get("points_earned", 10)
                self.state.score += points
                self.state.reveals_remaining = result.get("reveals_remaining", self.state.reveals_remaining)
                self.state.reveals_earned += 1

                # Check if all words solved
                if len(self.state.solved_words) >= WORDS_PER_PUZZLE:
                    return await self._transition_to_phase2()

                # Move to next unsolved word
                next_word = self._find_next_unsolved_word()
                if next_word is not None:
                    self.state.current_word_index = next_word
                    clue = self.state.clues[next_word]
                    message = f"Correct! {points} points. Word {next_word + 1} of 5. {clue}"
                    self.state.last_message = message
                    return {
                        "success": True,
                        "correct": True,
                        "message": message,
                        "blanks": self.get_current_blanks(),
                        "clue": clue,
                        "score": self.state.score,
                    }
                else:
                    return await self._transition_to_phase2()
            else:
                # Wrong answer
                attempts_remaining = result.get("attempts_remaining")
                message = f"Not quite. Try again!"
                if attempts_remaining is not None and attempts_remaining <= 5:
                    message += f" ({attempts_remaining} attempts left)"
                self.state.last_message = message
                return {
                    "success": True,
                    "correct": False,
                    "message": message,
                    "blanks": self.get_current_blanks(),
                    "clue": self.state.clues[word_index],
                }

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to check word: %s", err)
            return {"success": False, "message": f"Error checking answer: {err}"}

    async def _submit_theme_answer(self, answer: str) -> dict[str, Any]:
        """Submit a theme answer."""
        try:
            result = await self._api.check_theme(
                self.state.puzzle_id,
                self.state.session_id,
                answer,
            )

            is_correct = result.get("correct", False)

            if is_correct:
                bonus = result.get("bonus_points", 20)
                self.state.score += bonus
                return await self._end_game(
                    theme_correct=True,
                    message=f"Correct! The theme was {self.state.theme}. Bonus {bonus} points! Final score: {self.state.score}",
                )
            else:
                attempts_remaining = result.get("attempts_remaining")
                message = f"Not the theme. Try again!"
                if attempts_remaining is not None and attempts_remaining <= 3:
                    message += f" ({attempts_remaining} attempts left)"
                self.state.last_message = message
                return {
                    "success": True,
                    "correct": False,
                    "message": message,
                    "blanks": self.get_theme_blanks(),
                }

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to check theme: %s", err)
            return {"success": False, "message": f"Error checking theme: {err}"}

    async def _transition_to_phase2(self) -> dict[str, Any]:
        """Transition to theme guessing phase."""
        self.state.phase = 2
        self.state.current_word_index = -1

        # Reveal first letter of theme as hint
        if self.state.theme:
            self.state.theme_revealed_letters = [0]

        solved_words = [self.state.words[i] for i in self.state.solved_words]
        message = f"All words solved! Now guess the theme that connects: {', '.join(solved_words)}"
        self.state.last_message = message

        return {
            "success": True,
            "correct": True,
            "message": message,
            "phase": 2,
            "blanks": self.get_theme_blanks(),
            "solved_words": solved_words,
            "score": self.state.score,
        }

    async def _end_game(
        self, theme_correct: bool = False, message: str = ""
    ) -> dict[str, Any]:
        """End the game and submit score."""
        self.state.is_active = False
        self.state.completed_at = datetime.now()

        # Calculate time
        time_seconds = 0
        if self.state.started_at:
            delta = self.state.completed_at - self.state.started_at
            time_seconds = int(delta.total_seconds())

        # Submit score to API
        try:
            await self._api.submit_score(
                puzzle_id=self.state.puzzle_id,
                session_id=self.state.session_id,
                final_score=self.state.score,
                time_seconds=time_seconds,
                words_solved=len(self.state.solved_words),
                theme_correct=theme_correct,
            )
        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to submit score: %s", err)

        self.state.last_message = message

        return {
            "success": True,
            "game_over": True,
            "message": message,
            "final_score": self.state.score,
            "theme": self.state.theme,
            "theme_correct": theme_correct,
        }

    async def reveal_letter(self) -> dict[str, Any]:
        """Reveal a letter for the current word."""
        if not self.state.is_active:
            return {"success": False, "message": "No active game"}

        if self.state.reveals_remaining <= 0:
            return {"success": False, "message": "No reveals remaining"}

        word_index = self.state.current_word_index if self.state.phase == 1 else -1

        try:
            result = await self._api.reveal_letter(
                self.state.puzzle_id,
                self.state.session_id,
                word_index,
            )

            if result.get("success"):
                letter = result.get("letter", "?")
                position = result.get("position", 0)
                self.state.reveals_remaining = result.get("reveals_remaining", self.state.reveals_remaining - 1)

                # Track revealed letter locally
                if self.state.phase == 1:
                    if word_index not in self.state.revealed_letters:
                        self.state.revealed_letters[word_index] = []
                    self.state.revealed_letters[word_index].append(position)
                else:
                    self.state.theme_revealed_letters.append(position)

                blanks = self.get_current_blanks() if self.state.phase == 1 else self.get_theme_blanks()
                message = f"Revealed letter {letter}. {self.state.reveals_remaining} reveals left."
                self.state.last_message = message

                return {
                    "success": True,
                    "message": message,
                    "letter": letter,
                    "blanks": blanks,
                    "reveals_remaining": self.state.reveals_remaining,
                }
            else:
                return {"success": False, "message": result.get("message", "Cannot reveal")}

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to reveal letter: %s", err)
            return {"success": False, "message": f"Error revealing letter: {err}"}

    def skip_word(self) -> dict[str, Any]:
        """Skip the current word."""
        if not self.state.is_active or self.state.phase != 1:
            return {"success": False, "message": "Cannot skip now"}

        word_index = self.state.current_word_index
        if word_index not in self.state.skipped_words:
            self.state.skipped_words.append(word_index)

        # Find next word
        next_word = self._find_next_unsolved_word()
        if next_word is not None:
            self.state.current_word_index = next_word
            clue = self.state.clues[next_word]
            message = f"Skipped. Word {next_word + 1} of 5. {clue}"
            self.state.last_message = message
            return {
                "success": True,
                "message": message,
                "blanks": self.get_current_blanks(),
                "clue": clue,
            }
        else:
            # All words either solved or skipped - go back to first skipped
            if self.state.skipped_words:
                self.state.current_word_index = self.state.skipped_words[0]
                clue = self.state.clues[self.state.current_word_index]
                message = f"Back to word {self.state.current_word_index + 1}. {clue}"
                self.state.last_message = message
                return {
                    "success": True,
                    "message": message,
                    "blanks": self.get_current_blanks(),
                    "clue": clue,
                }
            return {"success": False, "message": "No more words to skip to"}

    def get_current_clue(self) -> str:
        """Get the current clue."""
        if self.state.phase == 1 and self.state.clues:
            idx = self.state.current_word_index
            if 0 <= idx < len(self.state.clues):
                return self.state.clues[idx]
        return "Guess the theme!"

    def get_current_blanks(self) -> str:
        """Get the current word as blanks with revealed letters."""
        if self.state.phase != 1 or not self.state.words:
            return self.get_theme_blanks()

        idx = self.state.current_word_index
        if not (0 <= idx < len(self.state.words)):
            return ""

        word = self.state.words[idx]
        revealed = self.state.revealed_letters.get(idx, [])

        blanks = []
        for i, char in enumerate(word):
            if char == " ":
                blanks.append(" ")
            elif i in revealed:
                blanks.append(char)
            else:
                blanks.append("_")

        return " ".join(blanks)

    def get_theme_blanks(self) -> str:
        """Get the theme as blanks with revealed letters."""
        if not self.state.theme:
            return ""

        blanks = []
        for i, char in enumerate(self.state.theme):
            if char == " ":
                blanks.append(" ")
            elif i in self.state.theme_revealed_letters:
                blanks.append(char)
            else:
                blanks.append("_")

        return " ".join(blanks)

    def _find_next_unsolved_word(self) -> int | None:
        """Find the next unsolved, unskipped word."""
        current = self.state.current_word_index

        # Look forward from current position
        for i in range(current + 1, WORDS_PER_PUZZLE):
            if i not in self.state.solved_words and i not in self.state.skipped_words:
                return i

        # Wrap around to beginning
        for i in range(0, current):
            if i not in self.state.solved_words and i not in self.state.skipped_words:
                return i

        # Check skipped words
        for i in self.state.skipped_words:
            if i not in self.state.solved_words:
                return i

        return None

    async def give_up(self) -> dict[str, Any]:
        """Give up the current game."""
        if not self.state.is_active:
            return {"success": False, "message": "No active game"}

        self.state.gave_up = True

        # Reveal all answers
        words_str = ", ".join(self.state.words)
        message = f"Game over. The words were: {words_str}. The theme was: {self.state.theme}. Final score: {self.state.score}"

        return await self._end_game(theme_correct=False, message=message)

    # ==================== Spelling Mode ====================

    def start_spelling(self) -> dict[str, Any]:
        """Enter spelling mode."""
        self.spelling_mode = True
        self.spelling_buffer = []
        message = "Spelling mode. Say each letter, then say 'done' when finished."
        self.state.last_message = message
        return {"success": True, "message": message}

    def add_letter(self, letter: str) -> dict[str, Any]:
        """Add a letter to the spelling buffer."""
        letter = letter.strip().upper()
        if len(letter) == 1 and letter.isalpha():
            self.spelling_buffer.append(letter)
            spelled = " ".join(self.spelling_buffer)
            message = f"Spelled so far: {spelled}"
            self.state.last_message = message
            return {"success": True, "message": message, "buffer": self.spelling_buffer}
        return {"success": False, "message": "Invalid letter"}

    async def finish_spelling(self, text: str | None = None) -> dict[str, Any]:
        """Finish spelling and submit the word."""
        if text:
            # Parse letters from spoken text
            self.spelling_buffer = [c.upper() for c in text if c.isalpha()]

        if not self.spelling_buffer:
            return {"success": False, "message": "Nothing spelled"}

        word = "".join(self.spelling_buffer)
        self.spelling_mode = False
        self.spelling_buffer = []

        return await self.submit_answer(word)

    def cancel_spelling(self) -> dict[str, Any]:
        """Cancel spelling mode."""
        self.spelling_mode = False
        self.spelling_buffer = []
        clue = self.get_current_clue()
        message = f"Spelling cancelled. {clue}"
        self.state.last_message = message
        return {"success": True, "message": message}

    # ==================== Session Management ====================

    def set_session(
        self,
        active: bool,
        satellite: str | None = None,
        view_assist_device: str | None = None,
    ) -> None:
        """Set voice session state."""
        self.session_active = active
        self.active_satellite = satellite
        self.view_assist_device = view_assist_device
        self.timeout_count = 0

    def handle_timeout(self) -> dict[str, Any]:
        """Handle listening timeout."""
        self.timeout_count += 1

        if self.timeout_count >= 3:
            message = "I'll wait. Say your answer when ready."
        elif self.timeout_count == 2:
            message = "Take your time."
        else:
            message = "Still thinking?"

        self.state.last_message = message
        return {"message": message, "timeout_count": self.timeout_count}

    def reset_timeout(self) -> None:
        """Reset timeout counter."""
        self.timeout_count = 0
