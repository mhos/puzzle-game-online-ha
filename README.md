# Puzzle Game Online for Home Assistant

A voice-controlled word puzzle game integration for Home Assistant that connects to an online API for daily puzzles, leaderboards, and statistics tracking.

## Features

- **Daily Puzzles**: Play AI-generated word puzzles with themed answers
- **Bonus Games**: Unlimited bonus puzzles when you want more
- **Global Leaderboard**: Compete with other players worldwide
- **Personal Statistics**: Track your games played, words solved, and more
- **Voice Control**: Play hands-free using any Assist satellite
- **Display Support**: Works with View Assist displays for visual gameplay
- **Voice-Only Mode**: Also works with voice-only devices

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add `https://github.com/mhos/puzzle-game-online-ha` with category "Integration"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy `custom_components/puzzle_game_online` to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Puzzle Game Online"
4. Enter your display name (this will appear on leaderboards)
5. The integration will automatically register your device with the game server

## Voice Commands

### Starting a Game

- "Start puzzle game" - Start the daily puzzle
- "Play bonus game" - Start a bonus puzzle
- "Continue puzzle game" - Resume a paused game

### During Gameplay

- Say your answer naturally (e.g., "The answer is apple")
- "Reveal" or "Hint" - Reveal a random letter
- "Skip" or "Pass" or "Next" - Skip to the next word
- "Repeat" or "Clue" - Hear the clue again
- "Spell" - Enter spelling mode for difficult words
- "Pause" or "Stop" - Pause the game
- "Give up" - End the game and reveal all answers

### Spelling Mode

When in spelling mode:
- Say letters one at a time (e.g., "A", "P", "P", "L", "E")
- "Done" or "Submit" - Submit your spelled word
- "Cancel" - Exit spelling mode

## Blueprint Installation

To enable voice control, import the blueprint:

1. Go to Settings > Automations & Scenes > Blueprints
2. Click "Import Blueprint"
3. Enter: `https://github.com/mhos/puzzle-game-online-ha/blob/main/homeassistant/blueprints/automation/puzzle_game_online_controller.yaml`
4. Create an automation from the blueprint

## Services

The integration provides the following services:

| Service | Description |
|---------|-------------|
| `puzzle_game_online.start_game` | Start a new game (daily or bonus) |
| `puzzle_game_online.submit_answer` | Submit an answer |
| `puzzle_game_online.reveal_letter` | Reveal a random letter |
| `puzzle_game_online.skip_word` | Skip the current word |
| `puzzle_game_online.repeat_clue` | Repeat the current clue |
| `puzzle_game_online.start_spelling` | Enter spelling mode |
| `puzzle_game_online.add_letter` | Add a letter in spelling mode |
| `puzzle_game_online.finish_spelling` | Submit spelled word |
| `puzzle_game_online.cancel_spelling` | Cancel spelling mode |
| `puzzle_game_online.give_up` | Give up and end the game |
| `puzzle_game_online.set_session` | Set voice session state |

## Frontend Panel

The integration adds a sidebar panel at `/puzzle-game-online` with:

- **Game Tab**: Active game display with score, blanks, and controls
- **Leaderboard Tab**: Daily, weekly, and all-time rankings
- **Stats Tab**: Your personal statistics

## Sensor

The integration creates a sensor `sensor.puzzle_game_online` with the following attributes:

- `is_active`: Whether a game is in progress
- `score`: Current game score
- `current_word_index`: Index of current word
- `words_count`: Total words in puzzle
- `solved_count`: Number of solved words
- `current_blanks`: Current word display (e.g., "A _ _ L E")
- `clue`: Current word clue
- `theme`: Puzzle theme
- `solved_words`: List of solved words
- `session_active`: Whether voice session is active
- `spelling_mode`: Whether spelling mode is active
- `spelled_letters`: Letters spelled so far

## How Scoring Works

- **Base Points**: 100 points per word
- **Time Bonus**: Faster answers earn more points
- **Reveal Penalty**: -10 points per revealed letter
- **Skip Penalty**: -25 points for skipping
- **Theme Bonus**: +200 points for guessing the theme

## Requirements

- Home Assistant 2024.1.0 or newer
- Internet connection to puzzle game server
- (Optional) Assist satellite for voice control
- (Optional) View Assist display for visual gameplay

## License

MIT License - See LICENSE file for details.
