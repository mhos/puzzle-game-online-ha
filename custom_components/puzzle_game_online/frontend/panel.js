/**
 * Puzzle Game Online Panel for Home Assistant
 * Provides game display, stats, and leaderboard views
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
        this._pollInterval = null;
    }

    set hass(hass) {
        this._hass = hass;
        this.render();
    }

    set panel(panel) {
        this._config = panel.config;
    }

    connectedCallback() {
        this.render();
        this._startPolling();
        this._loadData();
    }

    disconnectedCallback() {
        this._stopPolling();
    }

    _startPolling() {
        this._pollInterval = setInterval(() => {
            if (this._activeTab === 'game') {
                // Don't re-render if user is typing in the input
                // Check shadow DOM's active element
                const activeEl = this.shadowRoot.activeElement;
                const answerInput = this.shadowRoot.getElementById('answerInput');
                if (answerInput && activeEl === answerInput) {
                    // Just update the game state display without full re-render
                    this._updateGameDisplay();
                } else {
                    this.render();
                }
            }
        }, 2000);
    }

    _updateGameDisplay() {
        // Lightweight update of just game stats without re-rendering input
        const state = this._getGameState();
        if (!state) return;

        const scoreEl = this.shadowRoot.querySelector('.stat-box .value');
        const blanksEl = this.shadowRoot.querySelector('.blanks');
        const clueEl = this.shadowRoot.querySelector('.clue');
        const messageEl = this.shadowRoot.querySelector('.message');

        if (blanksEl) blanksEl.textContent = state.blanks || '_ _ _ _ _';
        if (clueEl) clueEl.textContent = state.clue || 'Loading...';
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
            // Load user info
            const userResult = await this._hass.callWS({
                type: 'puzzle_game_online/user_info'
            }).catch(() => null);
            if (userResult) this._userInfo = userResult;

            // Load stats
            const statsResult = await this._hass.callWS({
                type: 'puzzle_game_online/stats'
            }).catch(() => null);
            if (statsResult) this._stats = statsResult;

            // Load leaderboard
            await this._loadLeaderboard();
        } catch (e) {
            console.error('Failed to load data:', e);
        }

        this.render();
    }

    async _loadLeaderboard() {
        if (!this._hass) return;

        try {
            const result = await this._hass.callWS({
                type: 'puzzle_game_online/leaderboard',
                period: this._leaderboardPeriod
            }).catch(() => null);
            if (result) this._leaderboard = result;
        } catch (e) {
            console.error('Failed to load leaderboard:', e);
        }
    }

    _getGameState() {
        if (!this._hass) return null;
        const sensor = this._hass.states['sensor.puzzle_game_online'];
        return sensor ? sensor.attributes : null;
    }

    async _callService(service, data = {}) {
        if (!this._hass) return;
        await this._hass.callService('puzzle_game_online', service, data);
        setTimeout(() => this.render(), 100);
    }

    _switchTab(tab) {
        this._activeTab = tab;
        if (tab === 'leaderboard') {
            this._loadLeaderboard();
        } else if (tab === 'stats') {
            this._loadData();
        }
        this.render();
    }

    _switchLeaderboardPeriod(period) {
        this._leaderboardPeriod = period;
        this._loadLeaderboard();
        this.render();
    }

    render() {
        const state = this._getGameState();

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    height: 100%;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    color: #fff;
                    overflow: auto;
                }

                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }

                .header {
                    text-align: center;
                    margin-bottom: 20px;
                }

                .header h1 {
                    font-size: 2rem;
                    margin: 0 0 10px 0;
                    background: linear-gradient(to right, #e94560, #ff6b6b);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .user-info {
                    color: #aaa;
                    font-size: 0.9rem;
                }

                .tabs {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                    justify-content: center;
                }

                .tab {
                    padding: 12px 24px;
                    background: rgba(255,255,255,0.1);
                    border: none;
                    border-radius: 8px;
                    color: #aaa;
                    font-size: 1rem;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .tab:hover {
                    background: rgba(255,255,255,0.15);
                }

                .tab.active {
                    background: #e94560;
                    color: white;
                }

                .card {
                    background: rgba(255,255,255,0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 16px;
                    padding: 24px;
                    margin-bottom: 20px;
                }

                /* Game Display */
                .game-status {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                }

                .stat-box {
                    text-align: center;
                    padding: 15px;
                    background: rgba(0,0,0,0.2);
                    border-radius: 12px;
                    min-width: 80px;
                }

                .stat-box .value {
                    font-size: 1.8rem;
                    font-weight: bold;
                    color: #e94560;
                }

                .stat-box .label {
                    font-size: 0.8rem;
                    color: #aaa;
                    text-transform: uppercase;
                }

                .blanks {
                    font-size: 2.5rem;
                    font-family: 'Courier New', monospace;
                    text-align: center;
                    letter-spacing: 8px;
                    padding: 30px;
                    background: rgba(0,0,0,0.3);
                    border-radius: 12px;
                    margin-bottom: 20px;
                }

                .clue {
                    font-size: 1.2rem;
                    text-align: center;
                    color: #ddd;
                    font-style: italic;
                    padding: 20px;
                    background: rgba(233, 69, 96, 0.1);
                    border-left: 4px solid #e94560;
                    border-radius: 0 12px 12px 0;
                    margin-bottom: 20px;
                }

                .message {
                    text-align: center;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    font-weight: 500;
                }

                .message.success { background: rgba(74, 222, 128, 0.2); color: #4ade80; }
                .message.error { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
                .message.info { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }

                .solved-words {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    justify-content: center;
                }

                .solved-word {
                    padding: 8px 16px;
                    background: rgba(74, 222, 128, 0.2);
                    color: #4ade80;
                    border-radius: 20px;
                    font-weight: 500;
                }

                .actions {
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .btn {
                    padding: 12px 24px;
                    border: none;
                    border-radius: 8px;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .btn-primary {
                    background: #e94560;
                    color: white;
                }

                .btn-primary:hover {
                    background: #ff6b6b;
                }

                .btn-secondary {
                    background: rgba(255,255,255,0.15);
                    color: white;
                }

                .btn-secondary:hover {
                    background: rgba(255,255,255,0.25);
                }

                .btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .answer-input-container {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                    justify-content: center;
                }

                .answer-input {
                    flex: 1;
                    max-width: 300px;
                    padding: 15px 20px;
                    font-size: 1.2rem;
                    border: 2px solid rgba(255,255,255,0.2);
                    border-radius: 12px;
                    background: rgba(0,0,0,0.3);
                    color: white;
                    text-align: center;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }

                .answer-input:focus {
                    outline: none;
                    border-color: #e94560;
                }

                .answer-input::placeholder {
                    color: rgba(255,255,255,0.4);
                    text-transform: none;
                    letter-spacing: normal;
                }

                /* Leaderboard */
                .period-tabs {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                    justify-content: center;
                }

                .leaderboard-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .leaderboard-table th,
                .leaderboard-table td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }

                .leaderboard-table th {
                    color: #aaa;
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 0.8rem;
                }

                .rank-1 { color: #ffd700; font-weight: bold; }
                .rank-2 { color: #c0c0c0; font-weight: bold; }
                .rank-3 { color: #cd7f32; font-weight: bold; }

                /* Stats */
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                }

                .stats-card {
                    background: rgba(0,0,0,0.2);
                    padding: 20px;
                    border-radius: 12px;
                    text-align: center;
                }

                .stats-card .value {
                    font-size: 2rem;
                    font-weight: bold;
                    color: #e94560;
                }

                .stats-card .label {
                    color: #aaa;
                    font-size: 0.85rem;
                    margin-top: 5px;
                }

                .no-game {
                    text-align: center;
                    padding: 60px 20px;
                }

                .no-game h2 {
                    margin-bottom: 20px;
                    color: #ddd;
                }

                .loading {
                    text-align: center;
                    padding: 40px;
                    color: #aaa;
                }
            </style>

            <div class="container">
                <div class="header">
                    <h1>Puzzle Game Online</h1>
                    ${this._userInfo ? `<div class="user-info">Playing as: ${this._userInfo.display_name || this._userInfo.username}</div>` : ''}
                </div>

                <div class="tabs">
                    <button class="tab ${this._activeTab === 'game' ? 'active' : ''}" data-tab="game">Game</button>
                    <button class="tab ${this._activeTab === 'leaderboard' ? 'active' : ''}" data-tab="leaderboard">Leaderboard</button>
                    <button class="tab ${this._activeTab === 'stats' ? 'active' : ''}" data-tab="stats">My Stats</button>
                </div>

                ${this._activeTab === 'game' ? this._renderGame(state) : ''}
                ${this._activeTab === 'leaderboard' ? this._renderLeaderboard() : ''}
                ${this._activeTab === 'stats' ? this._renderStats() : ''}
            </div>
        `;

        // Add event listeners
        this.shadowRoot.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => this._switchTab(tab.dataset.tab));
        });

        this.shadowRoot.querySelectorAll('.period-tab').forEach(tab => {
            tab.addEventListener('click', () => this._switchLeaderboardPeriod(tab.dataset.period));
        });

        this.shadowRoot.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'start') {
                    this._callService('start_game');
                } else if (action === 'start_bonus') {
                    this._callService('start_game', { bonus: true });
                } else if (action === 'reveal') {
                    this._callService('reveal_letter');
                } else if (action === 'skip') {
                    this._callService('skip_word');
                } else if (action === 'give_up') {
                    this._callService('give_up');
                }
            });
        });

        // Answer input handling
        const answerInput = this.shadowRoot.getElementById('answerInput');
        const submitBtn = this.shadowRoot.getElementById('submitBtn');

        if (answerInput && submitBtn) {
            submitBtn.addEventListener('click', () => {
                const answer = answerInput.value.trim();
                if (answer) {
                    this._callService('submit_answer', { answer: answer });
                    answerInput.value = '';
                }
            });

            answerInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const answer = answerInput.value.trim();
                    if (answer) {
                        this._callService('submit_answer', { answer: answer });
                        answerInput.value = '';
                    }
                }
            });
        }
    }

    _renderGame(state) {
        if (!state || !state.is_active) {
            return `
                <div class="card no-game">
                    <h2>Ready to Play?</h2>
                    <p style="color: #aaa; margin-bottom: 30px;">
                        Solve 5 words connected by a theme.<br>
                        Earn points and compete on the leaderboard!
                    </p>
                    <div class="actions">
                        <button class="btn btn-primary" data-action="start">Start Today's Puzzle</button>
                        <button class="btn btn-secondary" data-action="start_bonus">Play Bonus Game</button>
                    </div>
                </div>
            `;
        }

        const phase = state.phase || 1;
        const wordNum = state.word_number || 1;
        const isPhase2 = phase === 2;

        return `
            <div class="card">
                <div class="game-status">
                    <div class="stat-box">
                        <div class="value">${state.score || 0}</div>
                        <div class="label">Score</div>
                    </div>
                    <div class="stat-box">
                        <div class="value">${isPhase2 ? 'Theme' : `${wordNum}/5`}</div>
                        <div class="label">${isPhase2 ? 'Phase' : 'Word'}</div>
                    </div>
                    <div class="stat-box">
                        <div class="value">${state.reveals || 0}</div>
                        <div class="label">Reveals</div>
                    </div>
                </div>

                <div class="blanks">${state.blanks || '_ _ _ _ _'}</div>

                <div class="clue">${state.clue || 'Loading...'}</div>

                <div class="answer-input-container">
                    <input type="text" class="answer-input" id="answerInput"
                           placeholder="Type your answer..."
                           autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
                    <button class="btn btn-primary" id="submitBtn">Submit</button>
                </div>

                ${state.last_message ? `
                    <div class="message ${this._getMessageClass(state.last_message)}">
                        ${state.last_message}
                    </div>
                ` : ''}

                ${state.solved_words && state.solved_words.length > 0 ? `
                    <div class="solved-words">
                        ${state.solved_words.map(w => `<span class="solved-word">${w}</span>`).join('')}
                    </div>
                ` : ''}

                <div class="actions" style="margin-top: 20px;">
                    <button class="btn btn-secondary" data-action="reveal" ${state.reveals <= 0 ? 'disabled' : ''}>
                        Reveal Letter
                    </button>
                    ${!isPhase2 ? `
                        <button class="btn btn-secondary" data-action="skip">Skip Word</button>
                    ` : ''}
                    <button class="btn btn-secondary" data-action="give_up">Give Up</button>
                </div>
            </div>
        `;
    }

    _renderLeaderboard() {
        return `
            <div class="card">
                <div class="period-tabs">
                    <button class="tab period-tab ${this._leaderboardPeriod === 'daily' ? 'active' : ''}" data-period="daily">Today</button>
                    <button class="tab period-tab ${this._leaderboardPeriod === 'weekly' ? 'active' : ''}" data-period="weekly">This Week</button>
                    <button class="tab period-tab ${this._leaderboardPeriod === 'all_time' ? 'active' : ''}" data-period="all_time">All Time</button>
                </div>

                ${this._leaderboard ? `
                    <table class="leaderboard-table">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Player</th>
                                <th>Score</th>
                                ${this._leaderboardPeriod !== 'daily' ? '<th>Games</th>' : '<th>Time</th>'}
                            </tr>
                        </thead>
                        <tbody>
                            ${(this._leaderboard.entries || []).map((entry, i) => `
                                <tr>
                                    <td class="${i < 3 ? `rank-${i + 1}` : ''}">${entry.rank || i + 1}</td>
                                    <td>${entry.display_name || entry.username}</td>
                                    <td>${entry.score || entry.total_score || 0}</td>
                                    <td>${this._leaderboardPeriod !== 'daily' ? entry.games_played : this._formatTime(entry.time_seconds)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<div class="loading">Loading leaderboard...</div>'}
            </div>
        `;
    }

    _renderStats() {
        if (!this._stats) {
            return `<div class="card"><div class="loading">Loading stats...</div></div>`;
        }

        return `
            <div class="card">
                <h3 style="margin-bottom: 20px; text-align: center;">Your Statistics</h3>
                <div class="stats-grid">
                    <div class="stats-card">
                        <div class="value">${this._stats.games_played || 0}</div>
                        <div class="label">Games Played</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${this._stats.total_score || 0}</div>
                        <div class="label">Total Score</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${this._stats.avg_score || 0}</div>
                        <div class="label">Avg Score</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${this._stats.best_score || 0}</div>
                        <div class="label">Best Score</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${this._stats.current_streak || 0}</div>
                        <div class="label">Current Streak</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${this._stats.longest_streak || 0}</div>
                        <div class="label">Longest Streak</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${this._stats.perfect_games || 0}</div>
                        <div class="label">Perfect Games</div>
                    </div>
                    <div class="stats-card">
                        <div class="value">${this._stats.total_words_solved || 0}</div>
                        <div class="label">Words Solved</div>
                    </div>
                </div>
            </div>
        `;
    }

    _getMessageClass(message) {
        if (!message) return 'info';
        const lower = message.toLowerCase();
        if (lower.includes('correct') || lower.includes('points')) return 'success';
        if (lower.includes('not') || lower.includes('wrong') || lower.includes('try again')) return 'error';
        return 'info';
    }

    _formatTime(seconds) {
        if (!seconds) return '-';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// Only register if not already defined (prevents errors on hot reload)
if (!customElements.get('puzzle-game-online-panel')) {
    customElements.define('puzzle-game-online-panel', PuzzleGameOnlinePanel);
}
