/**
 * Puzzle Game Online Panel for Home Assistant
 * Optimized for small screens (Echo Show, Lenovo Thinksmart)
 * Uses render-once pattern with element updates
 */

class PuzzleGameOnlinePanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._hass = null;
        this._config = null;
        this._activeTab = 'game';
        this._leaderboardPeriod = 'daily';
        this._stats = null;
        this._leaderboard = null;
        this._userInfo = null;
        this._gameHistory = null;
        this._historyFilter = 'all';
        this._historyExpanded = null;
        this._pollInterval = null;
        this._lastMessage = null;
        this._feedbackTimeout = null;
        this._helpVisible = false;
        this._rendered = false;
        this._lastGameResult = null;  // Store last game result for end-game display
        this._wasActive = false;  // Track if game was active to detect end
    }

    set hass(hass) {
        this._hass = hass;
        if (this._rendered) {
            this._updateDisplay();
        }
    }

    set panel(panel) {
        this._config = panel.config;
    }

    connectedCallback() {
        this._render();
        this._rendered = true;
        this._updateDisplay();
        this._startPolling();
        this._loadData();
    }

    disconnectedCallback() {
        this._stopPolling();
        if (this._feedbackTimeout) {
            clearTimeout(this._feedbackTimeout);
        }
    }

    _startPolling() {
        this._pollInterval = setInterval(() => {
            if (this._activeTab === 'game') {
                this._updateDisplay();
            }
        }, 500);
    }

    _stopPolling() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = null;
        }
    }

    async _loadData() {
        if (!this._hass) return;

        try {
            const userResult = await this._hass.callWS({
                type: 'puzzle_game_online/user_info'
            }).catch(() => null);
            if (userResult) this._userInfo = userResult;

            const statsResult = await this._hass.callWS({
                type: 'puzzle_game_online/stats'
            }).catch(() => null);
            if (statsResult) this._stats = statsResult;

            await this._loadLeaderboard();
        } catch (e) {
            console.error('Failed to load data:', e);
        }

        this._updateDisplay();
    }

    async _loadLeaderboard() {
        if (!this._hass) return;

        try {
            const result = await this._hass.callWS({
                type: 'puzzle_game_online/leaderboard',
                period: this._leaderboardPeriod
            }).catch(() => null);
            if (result) {
                this._leaderboard = result;
            }
        } catch (e) {
            console.error('Failed to load leaderboard:', e);
        }
    }

    async _loadGameHistory() {
        if (!this._hass) return;

        try {
            const result = await this._hass.callWS({
                type: 'puzzle_game_online/game_history',
                limit: 20,
                game_type: this._historyFilter === 'all' ? null : this._historyFilter
            }).catch(() => null);
            if (result) {
                this._gameHistory = result;
            }
        } catch (e) {
            console.error('Failed to load game history:', e);
        }
    }

    _getGameState() {
        if (!this._hass) return null;
        const sensor = this._hass.states['sensor.puzzle_game_online'];
        return sensor ? sensor.attributes : null;
    }

    _switchTab(tab) {
        this._activeTab = tab;
        if (tab === 'leaderboard') {
            this._leaderboard = null;
            this._loadLeaderboard().then(() => this._renderTabContent());
        } else if (tab === 'stats') {
            this._stats = null;
            this._gameHistory = null;
            Promise.all([this._loadData(), this._loadGameHistory()]).then(() => this._renderTabContent());
        }
        this._updateTabButtons();
        this._renderTabContent();
    }

    _switchHistoryFilter(filter) {
        this._historyFilter = filter;
        this._gameHistory = null;
        this._historyExpanded = null;
        this._renderTabContent();
        this._loadGameHistory().then(() => this._renderTabContent());
    }

    _toggleGameDetails(gameId) {
        this._historyExpanded = this._historyExpanded === gameId ? null : gameId;
        this._renderTabContent();
    }

    _switchLeaderboardPeriod(period) {
        this._leaderboardPeriod = period;
        this._leaderboard = null;
        this._renderTabContent();
        this._loadLeaderboard().then(() => this._renderTabContent());
    }

    _toggleHelp() {
        this._helpVisible = !this._helpVisible;
        const modal = this.shadowRoot.getElementById('helpModal');
        if (modal) {
            modal.classList.toggle('show', this._helpVisible);
        }
    }

    _updateTabButtons() {
        this.shadowRoot.querySelectorAll('.tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === this._activeTab);
        });
    }

    _render() {
        this.shadowRoot.innerHTML = `
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }

                :host {
                    display: flex;
                    flex-direction: column;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    height: 100%;
                    width: 100%;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    padding: 10px;
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    overflow: auto;
                }

                .container {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 15px;
                    width: 95%;
                    max-width: 800px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }

                .header {
                    text-align: center;
                    margin-bottom: 10px;
                }

                .header h1 {
                    font-size: clamp(1.3em, 4vw, 2em);
                    margin-bottom: 3px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }

                .user-info {
                    font-size: clamp(0.7em, 2vw, 0.9em);
                    opacity: 0.8;
                }

                .tabs {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 12px;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .tab {
                    padding: 8px 16px;
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 10px;
                    color: rgba(255,255,255,0.8);
                    font-size: clamp(0.8em, 2.5vw, 1rem);
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .tab:hover { background: rgba(255, 255, 255, 0.3); }
                .tab.active {
                    background: rgba(255, 255, 255, 0.4);
                    color: white;
                    font-weight: bold;
                }

                .tab-content { display: none; }
                .tab-content.active { display: block; }

                /* Game Display */
                .stats-row {
                    display: flex;
                    justify-content: space-around;
                    margin-bottom: 10px;
                    flex-wrap: wrap;
                    gap: 8px;
                }

                .stat {
                    background: rgba(255, 255, 255, 0.2);
                    padding: 8px 12px;
                    border-radius: 12px;
                    text-align: center;
                    min-width: 70px;
                    flex: 1;
                }

                .stat-label {
                    font-size: clamp(0.65em, 1.8vw, 0.8em);
                    opacity: 0.8;
                    margin-bottom: 2px;
                }

                .stat-value {
                    font-size: clamp(1.1em, 3.5vw, 1.5em);
                    font-weight: bold;
                }

                .feedback-message {
                    padding: 12px;
                    border-radius: 12px;
                    text-align: center;
                    margin-bottom: 10px;
                    font-size: clamp(0.9em, 2.5vw, 1.1em);
                    font-weight: bold;
                    display: none;
                    animation: slideIn 0.3s ease-out;
                }

                .feedback-message.show { display: block; }
                .feedback-message.correct {
                    background: rgba(76, 175, 80, 0.85);
                    border: 2px solid rgba(76, 175, 80, 1);
                }
                .feedback-message.wrong {
                    background: rgba(244, 67, 54, 0.85);
                    border: 2px solid rgba(244, 67, 54, 1);
                }

                @keyframes slideIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .solved-words {
                    background: rgba(255, 215, 0, 0.2);
                    border: 2px solid rgba(255, 215, 0, 0.5);
                    padding: 10px;
                    border-radius: 12px;
                    text-align: center;
                    margin-bottom: 10px;
                    display: none;
                }

                .solved-words.show { display: block; }

                .solved-words-label {
                    font-size: clamp(0.75em, 2vw, 0.9em);
                    opacity: 0.9;
                    margin-bottom: 6px;
                    color: #ffd700;
                    font-weight: bold;
                }

                .solved-words-list {
                    font-size: clamp(0.95em, 2.5vw, 1.2em);
                    font-weight: bold;
                    letter-spacing: 1px;
                    line-height: 1.4;
                }

                .word-display {
                    background: rgba(255, 255, 255, 0.2);
                    padding: 15px 10px;
                    border-radius: 15px;
                    text-align: center;
                    margin-bottom: 10px;
                }

                .word-number {
                    font-size: clamp(0.85em, 2.2vw, 1em);
                    margin-bottom: 8px;
                    opacity: 0.9;
                }

                .word-number.final-phase {
                    color: #ffd700;
                    font-weight: bold;
                }

                .word-blanks {
                    font-size: clamp(1em, 2.5vw, 1.4em);
                    letter-spacing: 0.12em;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                    margin: 8px 0;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }

                .clue {
                    font-size: clamp(0.85em, 2.2vw, 1.1em);
                    font-style: italic;
                    margin-top: 8px;
                    opacity: 0.9;
                    line-height: 1.3;
                }

                .voice-hint {
                    background: rgba(255, 255, 255, 0.15);
                    padding: 10px;
                    border-radius: 8px;
                    margin-top: 10px;
                    font-size: clamp(0.75em, 2vw, 0.9em);
                }

                .voice-hint strong { color: #ffd700; }

                .progress {
                    display: flex;
                    justify-content: center;
                    gap: clamp(6px, 2vw, 10px);
                    margin-top: 10px;
                    flex-wrap: wrap;
                }

                .progress-dot {
                    width: clamp(28px, 7vw, 35px);
                    height: clamp(28px, 7vw, 35px);
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: clamp(0.85em, 2.5vw, 1em);
                    font-weight: bold;
                }

                .progress-dot.correct { background: #4caf50; }
                .progress-dot.skipped { background: #f44336; }
                .progress-dot.pending {
                    background: rgba(255, 255, 255, 0.3);
                    animation: pulse 2s infinite;
                }
                .progress-dot.final { background: #ffd700; }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                .no-game {
                    text-align: center;
                    padding: 20px 10px;
                }

                .no-game h2 {
                    margin-bottom: 10px;
                    font-size: clamp(1.1em, 3vw, 1.4em);
                }

                .no-game p {
                    opacity: 0.8;
                    line-height: 1.5;
                    font-size: clamp(0.85em, 2.2vw, 1em);
                }

                /* Help Button */
                .help-button {
                    position: fixed;
                    bottom: 10px;
                    right: 10px;
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    border: 2px solid rgba(255, 255, 255, 0.5);
                    color: white;
                    font-size: 22px;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    z-index: 1000;
                }

                .help-modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                    z-index: 2000;
                    align-items: center;
                    justify-content: center;
                    padding: 15px;
                }

                .help-modal.show { display: flex; }

                .help-content {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 15px;
                    padding: 20px;
                    max-width: 450px;
                    max-height: 80vh;
                    overflow-y: auto;
                }

                .help-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }

                .help-title { font-size: 1.3em; font-weight: bold; }

                .help-close {
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .help-section {
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 10px;
                    padding: 12px;
                    margin-bottom: 12px;
                }

                .help-section h3 {
                    color: #ffd700;
                    margin-bottom: 8px;
                    font-size: 1em;
                }

                .help-command {
                    background: rgba(0, 0, 0, 0.2);
                    border-left: 3px solid #4caf50;
                    padding: 6px 10px;
                    margin-bottom: 6px;
                    border-radius: 0 5px 5px 0;
                    font-size: 0.9em;
                }

                .help-command strong {
                    color: #4caf50;
                    display: block;
                    margin-bottom: 2px;
                }

                /* Leaderboard & Stats */
                .period-tabs {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 15px;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .period-tab {
                    padding: 8px 16px;
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 10px;
                    color: rgba(255,255,255,0.8);
                    font-size: 0.9rem;
                    cursor: pointer;
                }

                .period-tab.active {
                    background: rgba(255, 255, 255, 0.4);
                    color: white;
                    font-weight: bold;
                }

                .leaderboard-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .leaderboard-table th,
                .leaderboard-table td {
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }

                .leaderboard-table th {
                    opacity: 0.8;
                    font-size: 0.8em;
                    text-transform: uppercase;
                }

                .rank-1 { color: #ffd700; font-weight: bold; }
                .rank-2 { color: #c0c0c0; font-weight: bold; }
                .rank-3 { color: #cd7f32; font-weight: bold; }

                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
                    gap: 12px;
                }

                .stats-card {
                    background: rgba(255, 255, 255, 0.15);
                    padding: 15px;
                    border-radius: 12px;
                    text-align: center;
                }

                .stats-card .value {
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #ffd700;
                }

                .stats-card .label {
                    opacity: 0.8;
                    font-size: 0.8em;
                    margin-top: 4px;
                }

                .loading {
                    text-align: center;
                    padding: 30px;
                    opacity: 0.7;
                }

                /* Stats Section Styles */
                .stats-section {
                    margin-bottom: 15px;
                }

                .section-title {
                    font-size: 1em;
                    font-weight: bold;
                    margin-bottom: 8px;
                    opacity: 0.9;
                }

                .history-filters {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 10px;
                    justify-content: center;
                }

                .history-filter-btn {
                    padding: 6px 14px;
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 8px;
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 0.85rem;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .history-filter-btn.active {
                    background: rgba(255, 255, 255, 0.4);
                    color: white;
                    font-weight: bold;
                }

                .game-history {
                    max-height: 300px;
                    overflow-y: auto;
                }

                .game-row {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    margin-bottom: 6px;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .game-row:hover {
                    background: rgba(255, 255, 255, 0.2);
                }

                .game-row.expanded {
                    background: rgba(255, 255, 255, 0.2);
                }

                .game-summary {
                    display: flex;
                    align-items: center;
                    padding: 10px 12px;
                    gap: 10px;
                }

                .game-type {
                    font-size: 1.1em;
                }

                .game-date {
                    flex: 1;
                    font-size: 0.9em;
                }

                .game-score {
                    font-weight: bold;
                    color: #ffd700;
                }

                .game-theme {
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.9em;
                    background: rgba(255, 255, 255, 0.2);
                }

                .game-theme.correct {
                    background: rgba(76, 175, 80, 0.8);
                }

                .game-theme.wrong {
                    background: rgba(244, 67, 54, 0.8);
                }

                .game-details {
                    padding: 0 12px 12px 12px;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                    margin-top: 2px;
                }

                .detail-row {
                    display: flex;
                    justify-content: space-between;
                    padding: 4px 0;
                    font-size: 0.85em;
                }

                .detail-label {
                    opacity: 0.8;
                }

                .detail-value {
                    font-weight: 500;
                }

                .detail-value.positive {
                    color: #4caf50;
                }

                .detail-value.negative {
                    color: #f44336;
                }

                .no-history {
                    text-align: center;
                    padding: 20px;
                    opacity: 0.7;
                }

                /* Game Complete Screen */
                .game-complete {
                    text-align: center;
                    padding: 15px;
                }

                .game-complete.theme-correct {
                    background: linear-gradient(135deg, rgba(76, 175, 80, 0.2) 0%, rgba(76, 175, 80, 0.05) 100%);
                    border-radius: 16px;
                }

                .game-complete.theme-wrong {
                    background: linear-gradient(135deg, rgba(244, 67, 54, 0.1) 0%, rgba(244, 67, 54, 0.02) 100%);
                    border-radius: 16px;
                }

                .result-header {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    margin-bottom: 10px;
                }

                .result-emoji {
                    font-size: 2em;
                }

                .result-header h2 {
                    margin: 0;
                    font-size: 1.3em;
                }

                .result-message {
                    font-size: 1.1em;
                    opacity: 0.9;
                    margin-bottom: 5px;
                }

                .theme-reveal {
                    font-size: 1.4em;
                    font-weight: bold;
                    color: #ffd700;
                    margin: 10px 0;
                    text-transform: uppercase;
                }

                .theme-success {
                    font-size: 1.1em;
                    color: #4caf50;
                    margin: 5px 0 15px;
                }

                .final-score {
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 12px;
                    padding: 15px;
                    margin: 15px 0;
                }

                .final-score .score-label {
                    font-size: 0.9em;
                    opacity: 0.8;
                    margin-bottom: 5px;
                }

                .final-score .score-value {
                    font-size: 2.5em;
                    font-weight: bold;
                    color: #ffd700;
                }

                .score-breakdown {
                    background: rgba(0, 0, 0, 0.2);
                    border-radius: 10px;
                    padding: 12px;
                    margin: 10px 0;
                }

                .score-row {
                    display: flex;
                    justify-content: space-between;
                    padding: 6px 0;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    font-size: 0.95em;
                }

                .score-row:last-child {
                    border-bottom: none;
                }

                .score-row.bonus span:last-child {
                    color: #4caf50;
                }

                .score-row.penalty span:last-child {
                    color: #f44336;
                }

                .game-stats-row {
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    margin: 15px 0;
                }

                .mini-stat {
                    background: rgba(255, 255, 255, 0.1);
                    padding: 8px 15px;
                    border-radius: 20px;
                }

                .mini-value {
                    font-size: 0.9em;
                }

                .next-action {
                    margin-top: 15px;
                    padding-top: 15px;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                }

                .next-action p {
                    margin: 0 0 10px;
                    opacity: 0.9;
                }

                /* Small screens - Echo Show, Lenovo Thinksmart */
                @media (max-width: 1024px) and (max-height: 600px) {
                    :host {
                        padding: 5px;
                        justify-content: flex-start;
                    }

                    .container {
                        padding: 8px;
                        border-radius: 12px;
                        margin-top: 5px;
                    }

                    .header {
                        margin-bottom: 6px;
                    }

                    .header h1 {
                        font-size: 1.4em;
                        margin-bottom: 2px;
                    }

                    .tabs {
                        margin-bottom: 8px;
                        gap: 5px;
                    }

                    .tab {
                        padding: 6px 12px;
                        font-size: 0.8em;
                    }

                    .stats-row {
                        margin-bottom: 6px;
                        gap: 5px;
                    }

                    .stat {
                        padding: 6px 10px;
                        border-radius: 8px;
                        min-width: 60px;
                    }

                    .stat-label { font-size: 0.65em; }
                    .stat-value { font-size: 1.1em; }

                    .feedback-message {
                        padding: 8px;
                        margin-bottom: 6px;
                        font-size: 0.9em;
                    }

                    .solved-words {
                        padding: 8px;
                        margin-bottom: 6px;
                    }

                    .word-display {
                        padding: 10px 8px;
                        margin-bottom: 6px;
                        border-radius: 10px;
                    }

                    .word-number {
                        font-size: 0.8em;
                        margin-bottom: 5px;
                    }

                    .word-blanks {
                        font-size: 1.1em;
                        margin: 5px 0;
                    }

                    .clue {
                        font-size: 0.85em;
                        margin-top: 5px;
                    }

                    .voice-hint {
                        padding: 8px;
                        font-size: 0.75em;
                    }

                    .progress {
                        gap: 5px;
                        margin-top: 6px;
                    }

                    .progress-dot {
                        width: 26px;
                        height: 26px;
                        font-size: 0.8em;
                    }

                    .no-game {
                        padding: 15px 8px;
                    }

                    .no-game h2 { font-size: 1.1em; }
                    .no-game p { font-size: 0.85em; }

                    .help-button {
                        width: 35px;
                        height: 35px;
                        font-size: 18px;
                        bottom: 8px;
                        right: 8px;
                    }

                    /* Game Complete - Small Screen */
                    .game-complete {
                        padding: 10px;
                    }

                    .result-header {
                        gap: 8px;
                        margin-bottom: 6px;
                    }

                    .result-emoji {
                        font-size: 1.5em;
                    }

                    .result-header h2 {
                        font-size: 1.1em;
                    }

                    .result-message {
                        font-size: 0.95em;
                        margin-bottom: 3px;
                    }

                    .theme-reveal {
                        font-size: 1.1em;
                        margin: 6px 0;
                    }

                    .theme-success {
                        font-size: 0.95em;
                        margin: 3px 0 10px;
                    }

                    .final-score {
                        padding: 10px;
                        margin: 10px 0;
                    }

                    .final-score .score-label {
                        font-size: 0.8em;
                    }

                    .final-score .score-value {
                        font-size: 1.8em;
                    }

                    .score-breakdown {
                        padding: 8px;
                        margin: 8px 0;
                    }

                    .score-row {
                        padding: 4px 0;
                        font-size: 0.85em;
                    }

                    .game-stats-row {
                        gap: 12px;
                        margin: 10px 0;
                    }

                    .mini-stat {
                        padding: 6px 10px;
                    }

                    .mini-value {
                        font-size: 0.8em;
                    }

                    .next-action {
                        margin-top: 10px;
                        padding-top: 10px;
                    }

                    .next-action p {
                        font-size: 0.9em;
                        margin-bottom: 6px;
                    }
                }
            </style>

            <div class="help-button" id="helpBtn">?</div>

            <div class="help-modal" id="helpModal">
                <div class="help-content">
                    <div class="help-header">
                        <div class="help-title">Voice Commands</div>
                        <button class="help-close" id="helpClose">×</button>
                    </div>
                    <div class="help-section">
                        <h3>Starting</h3>
                        <div class="help-command"><strong>"Start puzzle game"</strong><span>Begin daily puzzle</span></div>
                        <div class="help-command"><strong>"Play bonus game"</strong><span>Extra puzzle</span></div>
                        <div class="help-command"><strong>"Continue puzzle game"</strong><span>Resume paused</span></div>
                    </div>
                    <div class="help-section">
                        <h3>Playing</h3>
                        <div class="help-command"><strong>Say your answer</strong><span>Speak the word</span></div>
                        <div class="help-command"><strong>"Reveal" / "Hint"</strong><span>Show a letter</span></div>
                        <div class="help-command"><strong>"Skip" / "Next"</strong><span>Next word</span></div>
                        <div class="help-command"><strong>"Repeat" / "Clue"</strong><span>Hear clue again</span></div>
                        <div class="help-command"><strong>"Spell"</strong><span>Spell mode</span></div>
                    </div>
                    <div class="help-section">
                        <h3>Wager</h3>
                        <div class="help-command"><strong>"Wager 50"</strong><span>Risk points</span></div>
                        <div class="help-command"><strong>"No wager"</strong><span>Play safe</span></div>
                        <div class="help-command"><strong>"All in"</strong><span>Risk all!</span></div>
                    </div>
                    <div class="help-section">
                        <h3>Ending</h3>
                        <div class="help-command"><strong>"Pause" / "Stop"</strong><span>Pause game</span></div>
                        <div class="help-command"><strong>"Give up"</strong><span>End & see answers</span></div>
                    </div>
                </div>
            </div>

            <div class="container">
                <div class="header">
                    <h1>🦉 Puzzle Game Online</h1>
                    <div class="user-info" id="userInfo"></div>
                </div>

                <div class="tabs">
                    <button class="tab active" data-tab="game">Game</button>
                    <button class="tab" data-tab="leaderboard">Leaderboard</button>
                    <button class="tab" data-tab="stats">Stats</button>
                </div>

                <div class="tab-content active" id="gameTab"></div>
                <div class="tab-content" id="leaderboardTab"></div>
                <div class="tab-content" id="statsTab"></div>
            </div>
        `;

        // Set up event listeners once
        this.shadowRoot.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => this._switchTab(tab.dataset.tab));
        });

        this.shadowRoot.getElementById('helpBtn').addEventListener('click', () => this._toggleHelp());
        this.shadowRoot.getElementById('helpClose').addEventListener('click', () => this._toggleHelp());
        this.shadowRoot.getElementById('helpModal').addEventListener('click', (e) => {
            if (e.target.id === 'helpModal') this._toggleHelp();
        });
    }

    _updateDisplay() {
        if (!this._hass) return;

        // Check if game just ended - capture result for end-game display
        const state = this._getGameState();
        const isActive = state && state.is_active;

        if (this._wasActive && !isActive && state) {
            // Game just ended - capture the final state
            this._lastGameResult = {
                score: state.score || state.current_score || 0,
                solved_words: state.solved_words || [],
                theme_revealed: state.theme_revealed,
                last_message: state.last_message,
                // We'll fetch more details from history
            };
            // Fetch the actual game details from history
            this._loadLastGameDetails();
        }
        this._wasActive = isActive;

        // Update user info
        const userInfoEl = this.shadowRoot.getElementById('userInfo');
        if (userInfoEl && this._userInfo) {
            userInfoEl.textContent = `Playing as: ${this._userInfo.display_name || this._userInfo.username}`;
        }

        // Update active tab content
        this._renderTabContent();
    }

    async _loadLastGameDetails() {
        try {
            const result = await this._hass.callWS({
                type: 'puzzle_game_online/game_history',
                limit: 1
            }).catch(() => null);
            if (result && result.games && result.games.length > 0) {
                this._lastGameResult = result.games[0];
                this._renderTabContent();
            }
        } catch (e) {
            console.error('Failed to load last game details:', e);
        }
    }

    _renderTabContent() {
        const gameTab = this.shadowRoot.getElementById('gameTab');
        const leaderboardTab = this.shadowRoot.getElementById('leaderboardTab');
        const statsTab = this.shadowRoot.getElementById('statsTab');

        // Toggle visibility
        gameTab.classList.toggle('active', this._activeTab === 'game');
        leaderboardTab.classList.toggle('active', this._activeTab === 'leaderboard');
        statsTab.classList.toggle('active', this._activeTab === 'stats');

        if (this._activeTab === 'game') {
            gameTab.innerHTML = this._renderGame();
        } else if (this._activeTab === 'leaderboard') {
            leaderboardTab.innerHTML = this._renderLeaderboard();
            // Re-attach period tab listeners
            leaderboardTab.querySelectorAll('.period-tab').forEach(tab => {
                tab.addEventListener('click', () => this._switchLeaderboardPeriod(tab.dataset.period));
            });
        } else if (this._activeTab === 'stats') {
            statsTab.innerHTML = this._renderStats();
            // Re-attach history filter and game detail listeners
            statsTab.querySelectorAll('.history-filter-btn').forEach(btn => {
                btn.addEventListener('click', () => this._switchHistoryFilter(btn.dataset.filter));
            });
            statsTab.querySelectorAll('.game-row').forEach(row => {
                row.addEventListener('click', () => this._toggleGameDetails(row.dataset.gameid));
            });
        }
    }

    _renderGame() {
        const state = this._getGameState();

        if (!state || !state.is_active) {
            const dailyPlayed = this._stats && this._stats.daily_played_today;
            const lastGame = this._lastGameResult;

            // Show detailed end-game summary if we have last game data
            if (lastGame && lastGame.final_score !== undefined) {
                return this._renderGameComplete(lastGame, dailyPlayed);
            }

            if (dailyPlayed) {
                return `
                    <div class="no-game">
                        <h2>Daily Puzzle Complete!</h2>
                        <p>Come back tomorrow for a new challenge!</p>
                        <div class="voice-hint">
                            <strong>Want more?</strong> Say <strong>"Play bonus game"</strong>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="no-game">
                    <h2>Ready to Play?</h2>
                    <p>Solve 5 words connected by a theme!</p>
                    <div class="voice-hint">
                        Say <strong>"Start puzzle game"</strong> to begin!
                    </div>
                </div>
            `;
        }

        const phase = state.phase || 1;
        const wordNum = state.word_number || 1;
        const isWagerPhase = phase === 2;
        const isThemePhase = phase === 3;
        const isPostWords = phase >= 2;

        // Feedback message
        let feedbackHtml = '';
        if (state.last_message && state.last_message !== this._lastMessage) {
            this._lastMessage = state.last_message;
            const isCorrect = state.last_message.toLowerCase().includes('correct');
            feedbackHtml = `<div class="feedback-message show ${isCorrect ? 'correct' : 'wrong'}">${state.last_message}</div>`;
        }

        // Solved words
        let solvedWordsHtml = '';
        if (state.solved_words && state.solved_words.length > 0) {
            solvedWordsHtml = `
                <div class="solved-words show">
                    <div class="solved-words-label">Your Clue Words:</div>
                    <div class="solved-words-list">${state.solved_words.join(' • ')}</div>
                </div>
            `;
        }

        // Progress dots
        const solvedIndices = (state.solved_word_indices || []).map(Number);
        const skippedIndices = (state.skipped_word_indices || []).map(Number);
        // Debug: Log indices to help diagnose checkmark/skip issue
        console.log('Progress state:', {
            solved_word_indices: state.solved_word_indices,
            skipped_word_indices: state.skipped_word_indices,
            solvedParsed: solvedIndices,
            skippedParsed: skippedIndices,
            phase: phase,
            wordNum: wordNum
        });
        let progressHtml = '';
        for (let i = 1; i <= 6; i++) {
            const wordIndex = i - 1;
            let dotClass = 'progress-dot';
            let content = i;

            if (i === 6) {
                dotClass += isThemePhase ? ' final pending' : '';
                content = '🎯';
            } else if (solvedIndices.includes(wordIndex)) {
                dotClass += ' correct';
                content = '✓';
            } else if (skippedIndices.includes(wordIndex)) {
                dotClass += ' skipped';
                content = '✗';
            } else if (wordIndex === wordNum - 1 && phase === 1) {
                dotClass += ' pending';
            }

            progressHtml += `<div class="${dotClass}">${content}</div>`;
        }

        return `
            <div class="stats-row">
                <div class="stat">
                    <div class="stat-label">Score</div>
                    <div class="stat-value">${state.score || 0}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">${isPostWords ? 'Phase' : 'Word'}</div>
                    <div class="stat-value">${isWagerPhase ? 'Wager' : isThemePhase ? 'Theme' : `${wordNum}/5`}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Reveals</div>
                    <div class="stat-value">${state.reveals || 0}</div>
                </div>
            </div>

            ${feedbackHtml}

            ${isPostWords ? solvedWordsHtml : ''}

            <div class="word-display">
                <div class="word-number ${isPostWords ? 'final-phase' : ''}">
                    ${isWagerPhase ? '💰 MAKE YOUR WAGER!' : isThemePhase ? '🎯 Guess the Theme!' : `Word ${wordNum} of 5`}
                </div>
                <div class="word-blanks">${state.blanks || '_ _ _ _ _'}</div>
                ${isWagerPhase ? `
                    <div class="clue">Score: <strong>${state.current_score || 0}</strong> pts. Wager 0-${state.current_score || 0}</div>
                    <div class="voice-hint">
                        Say: <strong>"wager [amount]"</strong>, <strong>"no wager"</strong>, or <strong>"all in"</strong>
                    </div>
                ` : `<div class="clue">${state.clue || 'Loading...'}</div>`}
            </div>

            <div class="progress">${progressHtml}</div>
        `;
    }

    _renderLeaderboard() {
        return `
            <div class="period-tabs">
                <button class="period-tab ${this._leaderboardPeriod === 'daily' ? 'active' : ''}" data-period="daily">Today</button>
                <button class="period-tab ${this._leaderboardPeriod === 'weekly' ? 'active' : ''}" data-period="weekly">Week</button>
                <button class="period-tab ${this._leaderboardPeriod === 'alltime' ? 'active' : ''}" data-period="alltime">All Time</button>
            </div>

            ${this._leaderboard ? `
                <table class="leaderboard-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Player</th>
                            <th>Score</th>
                            ${this._leaderboardPeriod !== 'daily' ? '<th>Games</th>' : ''}
                        </tr>
                    </thead>
                    <tbody>
                        ${(this._leaderboard.entries || []).map((entry, i) => `
                            <tr>
                                <td class="${i < 3 ? `rank-${i + 1}` : ''}">${entry.rank || i + 1}</td>
                                <td>${entry.display_name || entry.username}</td>
                                <td>${entry.score || entry.total_score || 0}</td>
                                ${this._leaderboardPeriod !== 'daily' ? `<td>${entry.games_played || '-'}</td>` : ''}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : '<div class="loading">Loading...</div>'}
        `;
    }

    _renderStats() {
        if (!this._stats) {
            return '<div class="loading">Loading...</div>';
        }

        const s = this._stats;
        const avgScore = typeof s.avg_score === 'number' ? Math.round(s.avg_score) : 0;
        const bonusAvg = typeof s.bonus_avg_score === 'number' ? Math.round(s.bonus_avg_score) : 0;

        let historyHtml = '<div class="loading">Loading history...</div>';
        if (this._gameHistory && this._gameHistory.games) {
            if (this._gameHistory.games.length === 0) {
                historyHtml = '<div class="no-history">No games found</div>';
            } else {
                historyHtml = this._gameHistory.games.map(game => {
                    const isExpanded = this._historyExpanded === game.id;
                    const dateStr = game.puzzle_date || 'Bonus';
                    const themeIcon = game.theme_correct === true ? '✓' : game.theme_correct === false ? '✗' : '-';
                    const themeClass = game.theme_correct === true ? 'correct' : game.theme_correct === false ? 'wrong' : '';
                    const typeLabel = game.is_bonus ? '🎁' : '📅';

                    return `
                        <div class="game-row ${isExpanded ? 'expanded' : ''}" data-gameid="${game.id}">
                            <div class="game-summary">
                                <span class="game-type">${typeLabel}</span>
                                <span class="game-date">${dateStr}</span>
                                <span class="game-score">${game.final_score} pts</span>
                                <span class="game-theme ${themeClass}">${themeIcon}</span>
                            </div>
                            ${isExpanded ? `
                                <div class="game-details">
                                    <div class="detail-row">
                                        <span class="detail-label">Theme:</span>
                                        <span class="detail-value">${game.theme || 'Unknown'}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Words:</span>
                                        <span class="detail-value">${game.words_solved}/5</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Word Score:</span>
                                        <span class="detail-value">${game.word_score || 0}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Reveals Used:</span>
                                        <span class="detail-value">${game.reveals_used || 0}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Reveals Bonus:</span>
                                        <span class="detail-value">+${game.reveals_bonus || 0}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Time:</span>
                                        <span class="detail-value">${this._formatTime(game.time_seconds)}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Time Bonus:</span>
                                        <span class="detail-value">+${game.time_bonus || 0}</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Wager:</span>
                                        <span class="detail-value ${game.wager_result > 0 ? 'positive' : game.wager_result < 0 ? 'negative' : ''}">${game.wager_amount || 0} → ${game.wager_result > 0 ? '+' : ''}${game.wager_result || 0}</span>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }).join('');
            }
        }

        return `
            <div class="stats-section">
                <div class="section-title">📅 Daily Puzzles</div>
                <div class="stats-grid">
                    <div class="stats-card">
                        <div class="value">${s.games_played || 0}</div>
                        <div class="label">Games</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${s.total_score || 0}</div>
                        <div class="label">Total</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${avgScore}</div>
                        <div class="label">Avg</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${s.current_streak || 0}</div>
                        <div class="label">Streak</div>
                    </div>
                </div>
            </div>

            <div class="stats-section">
                <div class="section-title">🎁 Bonus Games</div>
                <div class="stats-grid">
                    <div class="stats-card">
                        <div class="value">${s.bonus_games_played || 0}</div>
                        <div class="label">Games</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${s.bonus_total_score || 0}</div>
                        <div class="label">Total</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${bonusAvg}</div>
                        <div class="label">Avg</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${s.bonus_best_score || 0}</div>
                        <div class="label">Best</div>
                    </div>
                </div>
            </div>

            <div class="stats-section">
                <div class="section-title">📜 Game History</div>
                <div class="history-filters">
                    <button class="history-filter-btn ${this._historyFilter === 'all' ? 'active' : ''}" data-filter="all">All</button>
                    <button class="history-filter-btn ${this._historyFilter === 'daily' ? 'active' : ''}" data-filter="daily">Daily</button>
                    <button class="history-filter-btn ${this._historyFilter === 'bonus' ? 'active' : ''}" data-filter="bonus">Bonus</button>
                </div>
                <div class="game-history">
                    ${historyHtml}
                </div>
            </div>
        `;
    }

    _formatTime(seconds) {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    _renderGameComplete(game, dailyPlayed) {
        const score = game.final_score || 0;
        const wordsSolved = game.words_solved || 0;
        const themeCorrect = game.theme_correct;
        const theme = game.theme || 'Unknown';
        const isBonus = game.is_bonus;
        const timeStr = this._formatTime(game.time_seconds);

        // Score breakdown
        const wordScore = game.word_score || 0;
        const timeBonus = game.time_bonus || 0;
        const revealsBonus = game.reveals_bonus || 0;
        const wagerAmount = game.wager_amount || 0;
        const wagerResult = game.wager_result || 0;

        // Determine result emoji and message
        let resultEmoji, resultMessage, resultClass;
        if (themeCorrect === true) {
            resultEmoji = '🎉';
            resultClass = 'theme-correct';
            if (score >= 100) {
                resultMessage = 'Amazing! Perfect game!';
            } else if (score >= 80) {
                resultMessage = 'Fantastic work!';
            } else {
                resultMessage = 'You got it!';
            }
        } else if (themeCorrect === false) {
            resultEmoji = '😔';
            resultClass = 'theme-wrong';
            resultMessage = 'So close! The theme was:';
        } else {
            resultEmoji = '🏁';
            resultClass = '';
            resultMessage = 'Game complete!';
        }

        // Build score breakdown rows
        let breakdownHtml = `<div class="score-row"><span>Words (${wordsSolved}/5)</span><span>+${wordScore}</span></div>`;
        if (timeBonus > 0) {
            breakdownHtml += `<div class="score-row bonus"><span>Time Bonus</span><span>+${timeBonus}</span></div>`;
        }
        if (revealsBonus > 0) {
            breakdownHtml += `<div class="score-row bonus"><span>Reveal Bonus</span><span>+${revealsBonus}</span></div>`;
        }
        if (wagerAmount > 0) {
            const wagerClass = wagerResult >= 0 ? 'bonus' : 'penalty';
            const wagerSign = wagerResult >= 0 ? '+' : '';
            breakdownHtml += `<div class="score-row ${wagerClass}"><span>Wager (${wagerAmount})</span><span>${wagerSign}${wagerResult}</span></div>`;
        }

        return `
            <div class="game-complete ${resultClass}">
                <div class="result-header">
                    <span class="result-emoji">${resultEmoji}</span>
                    <h2>${isBonus ? 'Bonus Round' : 'Daily Puzzle'} Complete!</h2>
                </div>

                <div class="result-message">${resultMessage}</div>
                ${themeCorrect === false ? `<div class="theme-reveal">${theme}</div>` : ''}
                ${themeCorrect === true ? `<div class="theme-success">Theme: ${theme}</div>` : ''}

                <div class="final-score">
                    <div class="score-label">Final Score</div>
                    <div class="score-value">${score}</div>
                </div>

                <div class="score-breakdown">
                    ${breakdownHtml}
                </div>

                <div class="game-stats-row">
                    <div class="mini-stat">
                        <span class="mini-value">⏱️ ${timeStr}</span>
                    </div>
                    <div class="mini-stat">
                        <span class="mini-value">💡 ${game.reveals_used || 0} reveals</span>
                    </div>
                </div>

                <div class="next-action">
                    ${dailyPlayed && !isBonus ?
                        `<p>Come back tomorrow for the next daily puzzle!</p>
                         <div class="voice-hint">
                             <strong>Want more?</strong> Say <strong>"Play bonus game"</strong>
                         </div>` :
                        `<div class="voice-hint">
                             Say <strong>"${isBonus ? 'Play bonus game' : 'Start puzzle game'}"</strong> to play again!
                         </div>`
                    }
                </div>
            </div>
        `;
    }
}

if (!customElements.get('puzzle-game-online-panel')) {
    customElements.define('puzzle-game-online-panel', PuzzleGameOnlinePanel);
}
