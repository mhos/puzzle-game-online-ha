"""Constants for Puzzle Game Online integration."""
from typing import Final

DOMAIN: Final = "puzzle_game_online"
VERSION: Final = "1.1.5"

# API Configuration
API_BASE_URL: Final = "https://puzzleapi.techshit.xyz"
API_TIMEOUT: Final = 30

# Storage
STORAGE_KEY: Final = "puzzle_game_online"
STORAGE_VERSION: Final = 1

# Game Constants
POINTS_PER_WORD: Final = 10
THEME_BONUS: Final = 20
MAX_SCORE: Final = 70
WORDS_PER_PUZZLE: Final = 5
BASE_REVEALS: Final = 3

# Panel Configuration
PANEL_URL: Final = "/puzzle-game-online"
PANEL_TITLE: Final = "Puzzle Game"
PANEL_ICON: Final = "mdi:owl"

# Sensor
SENSOR_NAME: Final = "Puzzle Game Online"

# Services
SERVICE_START_GAME: Final = "start_game"
SERVICE_SUBMIT_ANSWER: Final = "submit_answer"
SERVICE_REVEAL_LETTER: Final = "reveal_letter"
SERVICE_SKIP_WORD: Final = "skip_word"
SERVICE_REPEAT_CLUE: Final = "repeat_clue"
SERVICE_START_SPELLING: Final = "start_spelling"
SERVICE_ADD_LETTER: Final = "add_letter"
SERVICE_FINISH_SPELLING: Final = "finish_spelling"
SERVICE_CANCEL_SPELLING: Final = "cancel_spelling"
SERVICE_GIVE_UP: Final = "give_up"
SERVICE_SET_SESSION: Final = "set_session"
SERVICE_LISTENING_TIMEOUT: Final = "listening_timeout"
SERVICE_RESET_TIMEOUT: Final = "reset_timeout"

# Attributes
ATTR_GAME_ID: Final = "game_id"
ATTR_SESSION_ID: Final = "session_id"
ATTR_PHASE: Final = "phase"
ATTR_WORD_NUMBER: Final = "word_number"
ATTR_SCORE: Final = "score"
ATTR_REVEALS: Final = "reveals"
ATTR_BLANKS: Final = "blanks"
ATTR_CLUE: Final = "clue"
ATTR_SOLVED_WORDS: Final = "solved_words"
ATTR_IS_ACTIVE: Final = "is_active"
ATTR_LAST_MESSAGE: Final = "last_message"
ATTR_THEME_REVEALED: Final = "theme_revealed"
ATTR_SESSION_ACTIVE: Final = "session_active"
ATTR_ACTIVE_SATELLITE: Final = "active_satellite"
ATTR_VIEW_ASSIST_DEVICE: Final = "view_assist_device"
ATTR_SPELLING_MODE: Final = "spelling_mode"
ATTR_SPELLING_BUFFER: Final = "spelling_buffer"

# Config
CONF_API_KEY: Final = "api_key"
CONF_USERNAME: Final = "username"
CONF_EMAIL: Final = "email"
CONF_DISPLAY_NAME: Final = "display_name"
CONF_USER_ID: Final = "user_id"
