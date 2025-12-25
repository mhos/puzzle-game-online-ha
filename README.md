# Puzzle Game Online for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge&logo=homeassistant&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mhos&repository=puzzle-game-online-ha&category=integration)

A voice-controlled word puzzle game integration for Home Assistant that connects to an online API for daily puzzles, leaderboards, and statistics tracking. Compete with players worldwide!

## Features

- **Daily Puzzles**: Play AI-generated word puzzles with themed answers
- **Bonus Games**: Unlimited bonus puzzles when you want more
- **Wager System**: Risk your points on guessing the theme - go all in!
- **Global Leaderboard**: Compete with other players worldwide
- **Personal Statistics**: Track your games played, words solved, and more
- **Voice Control**: Play hands-free using any Assist satellite
- **Display Support**: Works with View Assist displays for visual gameplay
- **Voice-Only Mode**: Also works with voice-only devices

## Installation

### Step 1: Install via HACS

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=mhos&repository=puzzle-game-online-ha&category=integration" target="_blank"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

Click the button above, or manually:

1. Open HACS in Home Assistant
2. Click the three dots menu > **Custom repositories**
3. Add: `https://github.com/mhos/puzzle-game-online-ha`
4. Category: **Integration**
5. Click **Add**
6. Find "Puzzle Game Online" and click **Download**
7. Restart Home Assistant

### Step 2: Add the Integration

1. Go to **Settings > Devices & Services**
2. Click **Add Integration**
3. Search for "Puzzle Game Online"
4. Choose your setup option:
   - **Create a new account**: Enter username, email, and display name
   - **Use an existing API key**: Enter your API key if reinstalling
5. The integration will register with the game server

> **Note:** Your API key is shown in the integration options. Save it in case you need to reinstall!
> A "Puzzle Game" entry will automatically appear in your sidebar.

### Step 3: Import the Blueprint

<a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmhos%2Fpuzzle-game-online-ha%2Fblob%2Fmain%2Fhomeassistant%2Fblueprints%2Fautomation%2Fpuzzle_game_online_controller.yaml" target="_blank"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a>

Click the button above, or manually:

1. Go to **Settings > Automations & Scenes > Blueprints**
2. Click **Import Blueprint**
3. Paste: `https://github.com/mhos/puzzle-game-online-ha/blob/main/homeassistant/blueprints/automation/puzzle_game_online_controller.yaml`
4. Click **Preview** then **Import**
5. Click **Create Automation** from the blueprint (no configuration needed!)

**That's it! You're ready to play!**

### Updating the Blueprint

When the blueprint is updated:
1. Go to **Settings > Automations & Scenes > Blueprints**
2. Find "Puzzle Game Online Controller"
3. Click the three dots menu (⋮) > **Re-import blueprint**
4. Your automations using this blueprint will automatically use the updated version

---

### Manual Installation (Without HACS)

1. Download the latest release
2. Copy `custom_components/puzzle_game_online` to your `config/custom_components/` directory
3. Restart Home Assistant
4. Follow Steps 2 and 3 above

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

### Wager Phase (After Solving All Words)

- "Wager 50" or "Wager 20 points" - Risk specific points
- "All in" - Risk your entire score!
- "No wager" - Play it safe with no risk

### Spelling Mode

When in spelling mode:
- Say letters one at a time (e.g., "A", "P", "P", "L", "E")
- "Done" or "Submit" - Submit your spelled word
- "Cancel" - Exit spelling mode

## Services

The integration provides the following services:

| Service | Description |
|---------|-------------|
| `puzzle_game_online.start_game` | Start a new game (daily or bonus) |
| `puzzle_game_online.submit_answer` | Submit an answer |
| `puzzle_game_online.reveal_letter` | Reveal a random letter |
| `puzzle_game_online.skip_word` | Skip the current word |
| `puzzle_game_online.repeat_clue` | Repeat the current clue |
| `puzzle_game_online.set_wager` | Set wager amount (-1 for all in) |
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

### Word Points (Based on Reveals Used)
- **No reveals**: 20 points per word
- **1 reveal**: 15 points per word
- **2 reveals**: 10 points per word
- **3+ reveals**: 5 points per word

### Bonuses
- **Reveal Bonus**: 5 points for each unused reveal
- **Time Bonus**: Points for completing faster

### Wager System
After solving all 5 words, you enter the wager phase:
- Wager any amount from 0 to your entire score
- **Correct theme guess**: Win your wager (double your risked points!)
- **Wrong theme guess**: Lose your wager
- Say "all in" to risk everything for maximum points!

## Requirements

- Home Assistant 2024.1.0 or newer
- Internet connection to puzzle game server
- (Optional) Assist satellite for voice control
- (Optional) View Assist display for visual gameplay

## License

MIT License - See LICENSE file for details.
