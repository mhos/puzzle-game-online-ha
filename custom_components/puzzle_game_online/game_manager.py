"""Game manager for Puzzle Game Online."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from .api_client import PuzzleGameAPI, PuzzleGameAPIError
from .const import WORDS_PER_PUZZLE, BASE_REVEALS

_LOGGER = logging.getLogger(__name__)


class GameState:
    """Represents the current game state."""

    def __init__(self) -> None:
        """Initialize game state."""
        self.puzzle_id: str | None = None
        self.session_id: str | None = None
        self.is_bonus: bool = False

        # Puzzle data (from API - no answers)
        self.words_data: list[dict] = []  # [{clue, length}]
        self.theme: str = ""  # Only revealed at end
        self.theme_display: str = ""  # Blanks pattern for theme (e.g., "_ _ _ _ _   _ _ _ _ _")
        self.theme_length: int = 0  # Total letters in theme
        self.theme_word_count: int = 1  # Number of words in theme

        # Game progress
        self.phase: int = 1  # 1 = solving words, 2 = guessing theme
        self.current_word_index: int = 0
        self.reveals_available: int = BASE_REVEALS
        self.reveals_used: int = 0

        # Wager (points-based, not percentage)
        self.wager_amount: int = 0  # Points wagered
        self.current_score: int = 0  # Estimated score before wager (for max wager calculation)

        # Tracking (mirrored from server)
        self.solved_words: list[int] = []  # Indices of solved words
        self.skipped_words: list[int] = []  # Indices of skipped words
        self.revealed_letters: dict[int, list[int]] = {}  # word_index -> letter positions
        self.word_displays: dict[int, str] = {}  # word_index -> display string (e.g., "A _ _ L E")
        self.theme_solved: bool = False

        # Status
        self.is_active: bool = False
        self.gave_up: bool = False
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

        # Score (tracked server-side but we keep local copy)
        self.words_solved_count: int = 0
        self.final_score: int | None = None

        # Last feedback
        self.last_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for sensor attributes."""
        return {
            "puzzle_id": self.puzzle_id,
            "session_id": self.session_id,
            "is_bonus": self.is_bonus,
            "phase": self.phase,
            "current_word_index": self.current_word_index,
            "words_count": len(self.words_data),
            "reveals_available": self.reveals_available,
            "reveals_used": self.reveals_used,
            "solved_words": self.solved_words,
            "solved_count": len(self.solved_words),
            "skipped_words": self.skipped_words,
            "theme_solved": self.theme_solved,
            "is_active": self.is_active,
            "gave_up": self.gave_up,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "final_score": self.final_score,
            "last_message": self.last_message,
            "wager_amount": self.wager_amount,
            "current_score": self.current_score,
            "theme_display": self.theme_display,
            "theme_length": self.theme_length,
            "theme_word_count": self.theme_word_count,
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
            # Get puzzle from API
            if is_bonus:
                puzzle_data = await self._api.get_bonus_puzzle()
            else:
                puzzle_data = await self._api.get_daily_puzzle()

            puzzle_id = puzzle_data.get("id")
            if not puzzle_id:
                return {"success": False, "message": "No puzzle available"}

            # Start a game session on the server
            try:
                session_data = await self._api.start_game(str(puzzle_id))
            except PuzzleGameAPIError as err:
                error_msg = str(err)
                if "already completed" in error_msg.lower():
                    return {"success": False, "message": "You've already played today's puzzle! Try a bonus game."}
                raise

            # Initialize game state
            self.state.reset()
            self.state.puzzle_id = str(puzzle_id)
            self.state.session_id = session_data.get("session_id")
            self.state.is_bonus = is_bonus

            # Store puzzle data (clues and lengths only - no answers)
            self.state.words_data = puzzle_data.get("words", [])

            # Store theme info for blanks display
            self.state.theme_display = puzzle_data.get("theme_display", "")
            self.state.theme_length = puzzle_data.get("theme_length", 0)
            self.state.theme_word_count = puzzle_data.get("theme_word_count", 1)

            # Initialize word displays with blanks
            for i, word_data in enumerate(self.state.words_data):
                length = word_data.get("length", 5)
                self.state.word_displays[i] = " ".join(["_"] * length)

            # Set reveals from session
            self.state.reveals_available = session_data.get("reveals_available", BASE_REVEALS)
            self.state.solved_words = session_data.get("solved_words", [])
            self.state.theme_solved = session_data.get("theme_solved", False)

            # Restore solved word displays from session (for continuing paused games)
            solved_word_answers = session_data.get("solved_word_answers", {})
            for word_idx_str, answer in solved_word_answers.items():
                word_idx = int(word_idx_str)
                self.state.word_displays[word_idx] = answer

            # Mark as active
            self.state.is_active = True
            self.state.started_at = datetime.now()
            self.state.phase = 1
            self.state.current_word_index = 0

            # Build initial message
            first_clue = self._get_clue(0)
            game_type = "bonus puzzle" if is_bonus else "daily puzzle"
            message = f"Let's play the {game_type}! Word 1 of 5. {first_clue}"
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

    def _normalize_answer(self, answer: str) -> str:
        """Normalize an answer to handle spelled-out words from STT.

        Converts patterns like:
        - "T-A-S-T-E" -> "TASTE"
        - "T A S T E" -> "TASTE"
        - "T. A. S. T. E." -> "TASTE"
        - "tango alpha sierra tango echo" -> "TASTE" (NATO phonetic)
        """
        answer = answer.strip().upper()

        # NATO phonetic alphabet mapping
        nato_alphabet = {
            "ALPHA": "A", "ALFA": "A", "BRAVO": "B", "CHARLIE": "C",
            "DELTA": "D", "ECHO": "E", "FOXTROT": "F", "GOLF": "G",
            "HOTEL": "H", "INDIA": "I", "JULIET": "J", "JULIETT": "J",
            "KILO": "K", "LIMA": "L", "MIKE": "M", "NOVEMBER": "N",
            "OSCAR": "O", "PAPA": "P", "QUEBEC": "Q", "ROMEO": "R",
            "SIERRA": "S", "TANGO": "T", "UNIFORM": "U", "VICTOR": "V",
            "WHISKEY": "W", "WHISKY": "W", "XRAY": "X", "X-RAY": "X",
            "YANKEE": "Y", "ZULU": "Z",
        }

        # Check if it looks like NATO phonetic (multiple words, each is a NATO word)
        words = answer.split()
        if len(words) > 1:
            nato_result = []
            is_nato = True
            for word in words:
                word_clean = word.strip(".,!?")
                if word_clean in nato_alphabet:
                    nato_result.append(nato_alphabet[word_clean])
                elif len(word_clean) == 1 and word_clean.isalpha():
                    # Single letter is okay too
                    nato_result.append(word_clean)
                else:
                    is_nato = False
                    break
            if is_nato and nato_result:
                return "".join(nato_result)

        # Check for spelled-out pattern: single letters separated by dashes, spaces, or dots
        # Pattern: "S-I-G-H-T" or "S I G H T" or "S.I.G.H.T"
        # First, normalize separators to spaces
        normalized = answer.replace("-", " ").replace(".", " ")
        parts = normalized.split()

        # If all parts are single letters, join them
        if len(parts) > 1 and all(len(p) == 1 and p.isalpha() for p in parts):
            return "".join(parts)

        # Return original (already uppercased and stripped)
        return answer

    async def submit_answer(self, answer: str) -> dict[str, Any]:
        """Submit an answer for the current word or theme."""
        if not self.state.is_active:
            return {"success": False, "message": "No active game"}

        # Normalize the answer to handle spelled-out words
        answer = self._normalize_answer(answer)
        _LOGGER.debug("Normalized answer: %s", answer)

        if self.state.phase == 1:
            return await self._submit_word_answer(answer)
        elif self.state.phase == 2:
            # Phase 2 is wager - answers should go through set_wager instead
            return {"success": False, "message": "Please set your wager first. Say 'wager 50 percent' or 'no wager'."}
        else:
            return await self._submit_theme_answer(answer)

    async def _submit_word_answer(self, answer: str) -> dict[str, Any]:
        """Submit a word answer."""
        word_index = self.state.current_word_index

        try:
            result = await self._api.check_word(
                self.state.puzzle_id,
                word_index,
                answer,
            )

            is_correct = result.get("correct", False)
            already_solved = result.get("already_solved", False)

            if is_correct:
                if not already_solved:
                    # Update state
                    if word_index not in self.state.solved_words:
                        self.state.solved_words.append(word_index)

                    # Update reveals based on words solved (earn 1 reveal per word)
                    self.state.reveals_available = BASE_REVEALS + len(self.state.solved_words)

                    # Update word display to show the correct answer
                    self.state.word_displays[word_index] = answer.upper()

                # Check if all words solved
                if len(self.state.solved_words) >= WORDS_PER_PUZZLE:
                    return await self._transition_to_phase2()

                # Move to next unsolved word
                next_word = self._find_next_unsolved_word()
                if next_word is not None:
                    self.state.current_word_index = next_word
                    clue = self._get_clue(next_word)
                    words_solved = len(self.state.solved_words)
                    message = f"Correct! {words_solved} of 5 words solved. Word {next_word + 1}. {clue}"
                    self.state.last_message = message
                    return {
                        "success": True,
                        "correct": True,
                        "message": message,
                        "blanks": self.get_current_blanks(),
                        "clue": clue,
                    }
                else:
                    return await self._transition_to_phase2()
            else:
                # Wrong answer
                attempts_remaining = result.get("attempts_remaining")
                message = "Not quite. Try again!"
                if attempts_remaining is not None and attempts_remaining <= 5:
                    message += f" ({attempts_remaining} attempts left)"
                self.state.last_message = message
                return {
                    "success": True,
                    "correct": False,
                    "message": message,
                    "blanks": self.get_current_blanks(),
                    "clue": self._get_clue(word_index),
                }

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to check word: %s", err)
            return {"success": False, "message": f"Error checking answer: {err}"}

    async def _submit_theme_answer(self, answer: str) -> dict[str, Any]:
        """Submit a theme answer."""
        try:
            result = await self._api.check_theme(self.state.puzzle_id, answer)

            is_correct = result.get("correct", False)
            already_solved = result.get("already_solved", False)

            if is_correct:
                self.state.theme_solved = True
                self.state.theme = answer.upper()  # Store the correct theme
                return await self._end_game(
                    theme_correct=True,
                    message=f"Correct! The theme was {answer.upper()}! Game complete!",
                )
            else:
                attempts_remaining = result.get("attempts_remaining")
                message = "Not the theme. Try again!"
                if attempts_remaining is not None and attempts_remaining <= 3:
                    message += f" ({attempts_remaining} attempts left)"
                self.state.last_message = message
                return {
                    "success": True,
                    "correct": False,
                    "message": message,
                }

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to check theme: %s", err)
            return {"success": False, "message": f"Error checking theme: {err}"}

    def _calculate_current_score(self) -> int:
        """Calculate estimated score based on words solved and reveals used."""
        # Scoring per word based on reveals used:
        # 0 reveals = 20 points, 1 reveal = 15, 2 reveals = 10, 3+ reveals = 5
        score = 0
        for word_idx in self.state.solved_words:
            reveals_used = len(self.state.revealed_letters.get(word_idx, []))
            if reveals_used == 0:
                score += 20
            elif reveals_used == 1:
                score += 15
            elif reveals_used == 2:
                score += 10
            else:
                score += 5

        # Add reveal bonus (5 points per unused reveal)
        unused_reveals = self.state.reveals_available - self.state.reveals_used
        score += unused_reveals * 5

        return score

    async def _transition_to_phase2(self) -> dict[str, Any]:
        """Transition to wager phase after all words solved."""
        self.state.phase = 2
        self.state.current_word_index = -1

        # Calculate current score for wager max
        self.state.current_score = self._calculate_current_score()

        # Get the solved words for display
        solved_word_names = [
            self.state.word_displays.get(i, "???")
            for i in sorted(self.state.solved_words)
        ]

        score = self.state.current_score
        message = (
            f"All 5 words solved! Your score so far is {score} points. "
            f"Time to make your wager! You can bet anywhere from 0 to {score} points on guessing the theme. "
            f"If you guess correctly, you win your wager. If you're wrong, you lose it. "
            f"Say 'wager' followed by a number, 'no wager' to play it safe, or 'all in' to risk all {score} points!"
        )
        self.state.last_message = message

        return {
            "success": True,
            "correct": True,
            "message": message,
            "phase": 2,
            "solved_words": solved_word_names,
            "current_score": self.state.current_score,
        }

    def set_wager(self, points: int) -> dict[str, Any]:
        """Set the wager amount in points and transition to theme phase."""
        if not self.state.is_active:
            return {"success": False, "message": "No active game"}

        if self.state.phase != 2:
            return {"success": False, "message": "Can only set wager after solving all words"}

        # Clamp to valid range (0 to current score)
        max_wager = self.state.current_score
        points = max(0, min(max_wager, points))
        self.state.wager_amount = points

        # Transition to theme phase
        self.state.phase = 3

        # Get the solved words for display
        solved_word_names = [
            self.state.word_displays.get(i, "???")
            for i in sorted(self.state.solved_words)
        ]

        if points == 0:
            wager_msg = "No wager. You'll keep your current score no matter what."
        elif points == max_wager:
            wager_msg = f"All in with {points} points! Get it right to double up, wrong and you lose it all!"
        else:
            wager_msg = f"Wagering {points} points. Get it right to win {points} more, wrong and you lose {points}."

        # Build theme hint
        theme_hint = ""
        if self.state.theme_word_count > 1:
            theme_hint = f" The theme is {self.state.theme_word_count} words, {self.state.theme_length} letters total."
        else:
            theme_hint = f" The theme is {self.state.theme_length} letters."

        message = f"{wager_msg}{theme_hint} What's the theme?"
        self.state.last_message = message

        return {
            "success": True,
            "message": message,
            "phase": 3,
            "wager_amount": points,
            "max_wager": max_wager,
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

        # Build word_results for score submission
        word_results = []
        for i in range(WORDS_PER_PUZZLE):
            solved = i in self.state.solved_words
            reveals_used = len(self.state.revealed_letters.get(i, []))
            word_results.append({"solved": solved, "reveals_used": reveals_used})

        # Submit score to API
        # API uses wager_percent - convert our points to percentage of current score
        if self.state.current_score > 0:
            wager_percent = int((self.state.wager_amount / self.state.current_score) * 100)
        else:
            wager_percent = 0
        wager_percent = min(100, wager_percent)

        try:
            score_result = await self._api.submit_score(
                puzzle_id=self.state.puzzle_id,
                word_results=word_results,
                time_seconds=time_seconds,
                theme_correct=theme_correct,
                wager_percent=wager_percent,
            )
            self.state.final_score = score_result.get("final_score")
            rank = score_result.get("rank")
            total = score_result.get("total_players")
            wager_result = score_result.get("wager_result", 0)

            # Build score breakdown message
            score_parts = []
            if score_result.get("word_score"):
                score_parts.append(f"{score_result['word_score']} from words")
            if score_result.get("reveals_bonus"):
                score_parts.append(f"{score_result['reveals_bonus']} reveal bonus")
            if score_result.get("time_bonus"):
                score_parts.append(f"{score_result['time_bonus']} time bonus")

            # Add wager result to message if there was a wager
            if self.state.wager_amount > 0 and wager_result != 0:
                if wager_result > 0:
                    score_parts.append(f"+{wager_result} wager won")
                else:
                    score_parts.append(f"{wager_result} wager lost")

            if score_parts:
                message += f" Score breakdown: {', '.join(score_parts)}."

            message += f" Final score: {self.state.final_score}."

            if rank and total:
                message += f" Rank: {rank} of {total}."

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to submit score: %s", err)

        self.state.last_message = message

        return {
            "success": True,
            "game_over": True,
            "message": message,
            "final_score": self.state.final_score,
            "theme_correct": theme_correct,
        }

    async def reveal_letter(self) -> dict[str, Any]:
        """Reveal a letter for the current word."""
        if not self.state.is_active:
            return {"success": False, "message": "No active game"}

        if self.state.phase != 1:
            return {"success": False, "message": "Can only reveal during word phase"}

        if self.state.reveals_available <= self.state.reveals_used:
            return {"success": False, "message": "No reveals remaining"}

        word_index = self.state.current_word_index
        word_data = self.state.words_data[word_index] if word_index < len(self.state.words_data) else None
        if not word_data:
            return {"success": False, "message": "Invalid word"}

        word_length = word_data.get("length", 5)
        revealed = self.state.revealed_letters.get(word_index, [])

        # Find an unrevealed letter position
        available_positions = [i for i in range(word_length) if i not in revealed]
        if not available_positions:
            return {"success": False, "message": "All letters already revealed"}

        # Pick a random unrevealed position
        letter_index = random.choice(available_positions)

        try:
            result = await self._api.reveal_letter(
                self.state.puzzle_id,
                word_index,
                letter_index,
            )

            letter = result.get("letter", "?")
            actual_index = result.get("index", letter_index)
            self.state.reveals_used = result.get("reveals_used", self.state.reveals_used + 1)
            self.state.reveals_available = BASE_REVEALS + len(self.state.solved_words)

            # Track revealed letter locally
            if word_index not in self.state.revealed_letters:
                self.state.revealed_letters[word_index] = []
            if actual_index not in self.state.revealed_letters[word_index]:
                self.state.revealed_letters[word_index].append(actual_index)

            # Update word display
            self._update_word_display(word_index, actual_index, letter)

            remaining = self.state.reveals_available - self.state.reveals_used
            message = f"Revealed letter {letter}. {remaining} reveals left."
            self.state.last_message = message

            return {
                "success": True,
                "message": message,
                "letter": letter,
                "blanks": self.get_current_blanks(),
                "reveals_remaining": remaining,
            }

        except PuzzleGameAPIError as err:
            _LOGGER.error("Failed to reveal letter: %s", err)
            return {"success": False, "message": f"Error revealing letter: {err}"}

    def _update_word_display(self, word_index: int, position: int, letter: str) -> None:
        """Update the word display with a revealed letter."""
        current_display = self.state.word_displays.get(word_index, "")
        chars = current_display.split(" ")

        if position < len(chars):
            chars[position] = letter.upper()
            self.state.word_displays[word_index] = " ".join(chars)

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
            clue = self._get_clue(next_word)
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
                first_skipped = min(self.state.skipped_words)
                self.state.current_word_index = first_skipped
                clue = self._get_clue(first_skipped)
                message = f"Back to word {first_skipped + 1}. {clue}"
                self.state.last_message = message
                return {
                    "success": True,
                    "message": message,
                    "blanks": self.get_current_blanks(),
                    "clue": clue,
                }
            return {"success": False, "message": "No more words to skip to"}

    def repeat_clue(self) -> dict[str, Any]:
        """Repeat the current clue."""
        if not self.state.is_active:
            return {"success": False, "message": "No active game"}

        clue = self.get_current_clue()
        self.state.last_message = clue
        return {"success": True, "message": clue, "clue": clue}

    def _get_clue(self, word_index: int) -> str:
        """Get the clue for a word index."""
        if 0 <= word_index < len(self.state.words_data):
            return self.state.words_data[word_index].get("clue", "No clue")
        return "No clue"

    def get_current_clue(self) -> str:
        """Get the current clue."""
        if self.state.phase == 1:
            return self._get_clue(self.state.current_word_index)
        return "Guess the theme that connects all the words!"

    def get_current_blanks(self) -> str:
        """Get the current word or theme display."""
        # For theme phase (2 or 3), return theme blanks
        if self.state.phase >= 2:
            return self.state.theme_display or "_ _ _ _ _"

        idx = self.state.current_word_index
        return self.state.word_displays.get(idx, "")

    def _find_next_unsolved_word(self) -> int | None:
        """Find the next unsolved, unskipped word."""
        current = self.state.current_word_index
        total = len(self.state.words_data)

        # Look forward from current position
        for i in range(current + 1, total):
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

        # Get solved word names
        solved_word_names = [
            self.state.word_displays.get(i, "???")
            for i in sorted(self.state.solved_words)
        ]

        message = f"Game over. You solved {len(self.state.solved_words)} of 5 words."
        if solved_word_names:
            message += f" Words found: {', '.join(solved_word_names)}."

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
            message = "I'll pause the game. Say 'continue puzzle game' when ready."
            self.session_active = False
            return {"message": message, "timeout_count": self.timeout_count, "should_pause": True}
        elif self.timeout_count == 2:
            clue = self.get_current_clue()
            message = f"Take your time. {clue}"
        else:
            clue = self.get_current_clue()
            message = f"Still thinking? {clue}"

        self.state.last_message = message
        return {"message": message, "timeout_count": self.timeout_count, "should_retry": True}

    def reset_timeout(self) -> None:
        """Reset timeout counter."""
        self.timeout_count = 0
