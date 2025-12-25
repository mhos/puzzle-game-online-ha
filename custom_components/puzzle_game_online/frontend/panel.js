/**
 * Puzzle Game Online Panel for Home Assistant
 * View-only panel for game display, stats, and leaderboard
 * Gameplay is voice-only via Assist satellites
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
        this._lastMessage = null;
        this._feedbackTimeout = null;
        this._helpVisible = false;
    }

    set hass(hass) {
        this._hass = hass;
        // Don't re-render while help modal is open (preserves scroll position)
        if (!this._helpVisible) {
            this.render();
        }
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
        if (this._feedbackTimeout) {
            clearTimeout(this._feedbackTimeout);
        }
    }

    _startPolling() {
        this._pollInterval = setInterval(() => {
            // Don't re-render while help modal is open (preserves scroll position)
            if (this._activeTab === 'game' && !this._helpVisible) {
                this.render();
            }
        }, 2000);
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

        this.render();
    }

    async _loadLeaderboard() {
        if (!this._hass) return;

        try {
            const result = await this._hass.callWS({
                type: 'puzzle_game_online/leaderboard',
                period: this._leaderboardPeriod
            }).catch((e) => {
                console.error('Leaderboard WS error:', e);
                return null;
            });
            if (result) {
                this._leaderboard = result;
            }
        } catch (e) {
            console.error('Failed to load leaderboard:', e);
        }
        this.render();
    }

    _getGameState() {
        if (!this._hass) return null;
        const sensor = this._hass.states['sensor.puzzle_game_online'];
        return sensor ? sensor.attributes : null;
    }

    _switchTab(tab) {
        this._activeTab = tab;
        if (tab === 'leaderboard') {
            this._leaderboard = null; // Show loading state
            this.render();
            this._loadLeaderboard();
        } else if (tab === 'stats') {
            this._stats = null; // Show loading state
            this.render();
            this._loadData();
        } else {
            this.render();
        }
    }

    _switchLeaderboardPeriod(period) {
        this._leaderboardPeriod = period;
        this._leaderboard = null; // Show loading state
        this.render();
        this._loadLeaderboard();
    }

    _toggleHelp() {
        this._helpVisible = !this._helpVisible;
        this.render();
    }

    render() {
        const state = this._getGameState();

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
                    padding: 20px;
                    width: 95%;
                    max-width: 800px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    margin: 10px auto;
                }

                .header {
                    text-align: center;
                    margin-bottom: 15px;
                }

                .header h1 {
                    font-size: clamp(1.5em, 5vw, 2.5em);
                    margin-bottom: 5px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }

                .user-info {
                    font-size: 0.9em;
                    opacity: 0.8;
                }

                /* Tabs */
                .tabs {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .tab {
                    padding: 10px 20px;
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 10px;
                    color: rgba(255,255,255,0.8);
                    font-size: 1rem;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .tab:hover {
                    background: rgba(255, 255, 255, 0.3);
                }

                .tab.active {
                    background: rgba(255, 255, 255, 0.4);
                    color: white;
                    font-weight: bold;
                }

                /* Game Display */
                .stats-row {
                    display: flex;
                    justify-content: space-around;
                    margin-bottom: 15px;
                    flex-wrap: wrap;
                    gap: 10px;
                }

                .stat {
                    background: rgba(255, 255, 255, 0.2);
                    padding: 10px 15px;
                    border-radius: 15px;
                    text-align: center;
                    min-width: 80px;
                    flex: 1;
                }

                .stat-label {
                    font-size: 0.8em;
                    opacity: 0.8;
                    margin-bottom: 3px;
                }

                .stat-value {
                    font-size: 1.5em;
                    font-weight: bold;
                }

                .feedback-message {
                    padding: 15px;
                    border-radius: 15px;
                    text-align: center;
                    margin-bottom: 15px;
                    font-size: 1.1em;
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
                    padding: 15px;
                    border-radius: 15px;
                    text-align: center;
                    margin-bottom: 15px;
                    display: none;
                }

                .solved-words.show { display: block; }

                .solved-words-label {
                    font-size: 0.9em;
                    opacity: 0.9;
                    margin-bottom: 10px;
                    color: #ffd700;
                    font-weight: bold;
                }

                .solved-words-list {
                    font-size: 1.2em;
                    font-weight: bold;
                    letter-spacing: 1px;
                }

                .word-display {
                    background: rgba(255, 255, 255, 0.2);
                    padding: 20px;
                    border-radius: 20px;
                    text-align: center;
                    margin-bottom: 15px;
                }

                .word-number {
                    font-size: 1em;
                    margin-bottom: 10px;
                    opacity: 0.9;
                }

                .word-number.final-phase {
                    color: #ffd700;
                    font-weight: bold;
                }

                .word-blanks {
                    font-size: clamp(1.2em, 4vw, 2em);
                    letter-spacing: 0.15em;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                    margin: 10px 0;
                    word-wrap: break-word;
                }

                .clue {
                    font-size: 1.1em;
                    font-style: italic;
                    margin-top: 10px;
                    opacity: 0.9;
                }

                .progress {
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin-top: 15px;
                    flex-wrap: wrap;
                }

                .progress-dot {
                    width: 35px;
                    height: 35px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1em;
                    font-weight: bold;
                }

                .progress-dot.correct { background: #4caf50; }
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
                    padding: 40px 20px;
                }

                .no-game h2 {
                    margin-bottom: 15px;
                    font-size: 1.5em;
                }

                .no-game p {
                    opacity: 0.8;
                    line-height: 1.6;
                }

                .voice-hint {
                    background: rgba(255, 255, 255, 0.15);
                    padding: 15px;
                    border-radius: 10px;
                    margin-top: 20px;
                    font-size: 0.95em;
                }

                .voice-hint strong { color: #ffd700; }

                /* Leaderboard */
                .period-tabs {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .period-tab {
                    padding: 10px 20px;
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 10px;
                    color: rgba(255,255,255,0.8);
                    font-size: 1rem;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .period-tab:hover {
                    background: rgba(255, 255, 255, 0.3);
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
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }

                .leaderboard-table th {
                    opacity: 0.8;
                    font-size: 0.85em;
                    text-transform: uppercase;
                }

                .rank-1 { color: #ffd700; font-weight: bold; }
                .rank-2 { color: #c0c0c0; font-weight: bold; }
                .rank-3 { color: #cd7f32; font-weight: bold; }

                /* Stats */
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 15px;
                }

                .stats-card {
                    background: rgba(255, 255, 255, 0.15);
                    padding: 20px;
                    border-radius: 15px;
                    text-align: center;
                }

                .stats-card .value {
                    font-size: 1.8em;
                    font-weight: bold;
                    color: #ffd700;
                }

                .stats-card .label {
                    opacity: 0.8;
                    font-size: 0.85em;
                    margin-top: 5px;
                }

                .loading {
                    text-align: center;
                    padding: 40px;
                    opacity: 0.7;
                }

                /* Help Button */
                .help-button {
                    position: fixed;
                    bottom: 15px;
                    right: 15px;
                    width: 45px;
                    height: 45px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    border: 2px solid rgba(255, 255, 255, 0.5);
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    z-index: 1000;
                    transition: all 0.3s ease;
                }

                .help-button:hover {
                    background: rgba(255, 255, 255, 0.5);
                    transform: scale(1.1);
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
                    padding: 20px;
                }

                .help-modal.show { display: flex; }

                .help-content {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 20px;
                    padding: 25px;
                    max-width: 500px;
                    max-height: 80vh;
                    overflow-y: auto;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
                }

                .help-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }

                .help-title { font-size: 1.5em; font-weight: bold; }

                .help-close {
                    width: 35px;
                    height: 35px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    border: none;
                    color: white;
                    font-size: 20px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .help-section {
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 12px;
                    padding: 15px;
                    margin-bottom: 15px;
                }

                .help-section h3 {
                    color: #ffd700;
                    margin-bottom: 10px;
                    font-size: 1.1em;
                }

                .help-command {
                    background: rgba(0, 0, 0, 0.2);
                    border-left: 3px solid #4caf50;
                    padding: 8px 12px;
                    margin-bottom: 8px;
                    border-radius: 0 5px 5px 0;
                }

                .help-command strong {
                    color: #4caf50;
                    display: block;
                    margin-bottom: 3px;
                }

                .help-command span {
                    font-size: 0.9em;
                    opacity: 0.9;
                }
            </style>

            <div class="help-button" id="helpBtn">?</div>

            <div class="help-modal ${this._helpVisible ? 'show' : ''}" id="helpModal">
                <div class="help-content">
                    <div class="help-header">
                        <div class="help-title">🎤 Voice Commands</div>
                        <button class="help-close" id="helpClose">×</button>
                    </div>

                    <div class="help-section">
                        <h3>Starting the Game</h3>
                        <div class="help-command">
                            <strong>"Start puzzle game"</strong>
                            <span>Begin today's daily puzzle</span>
                        </div>
                        <div class="help-command">
                            <strong>"Play bonus game"</strong>
                            <span>Start an extra bonus round</span>
                        </div>
                        <div class="help-command">
                            <strong>"Continue puzzle game"</strong>
                            <span>Resume a paused game</span>
                        </div>
                    </div>

                    <div class="help-section">
                        <h3>During Gameplay</h3>
                        <div class="help-command">
                            <strong>Say your answer</strong>
                            <span>Just speak the word naturally</span>
                        </div>
                        <div class="help-command">
                            <strong>"Reveal" or "Hint"</strong>
                            <span>Show one random letter</span>
                        </div>
                        <div class="help-command">
                            <strong>"Skip" or "Next"</strong>
                            <span>Move to next word</span>
                        </div>
                        <div class="help-command">
                            <strong>"Repeat" or "Clue"</strong>
                            <span>Hear the clue again</span>
                        </div>
                        <div class="help-command">
                            <strong>"Spell"</strong>
                            <span>Enter spelling mode</span>
                        </div>
                    </div>

                    <div class="help-section">
                        <h3>Wager Phase</h3>
                        <div class="help-command">
                            <strong>"Wager 50" or "Wager 20 points"</strong>
                            <span>Risk points on the theme</span>
                        </div>
                        <div class="help-command">
                            <strong>"All in"</strong>
                            <span>Risk your entire score!</span>
                        </div>
                        <div class="help-command">
                            <strong>"No wager"</strong>
                            <span>Play it safe, no risk</span>
                        </div>
                    </div>

                    <div class="help-section">
                        <h3>Ending</h3>
                        <div class="help-command">
                            <strong>"Pause" or "Stop"</strong>
                            <span>Pause the game</span>
                        </div>
                        <div class="help-command">
                            <strong>"Give up"</strong>
                            <span>End game and see answers</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="container">
                <div class="header">
                    <h1>🦉 Puzzle Game Online</h1>
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

        // Help button
        const helpBtn = this.shadowRoot.getElementById('helpBtn');
        const helpClose = this.shadowRoot.getElementById('helpClose');
        const helpModal = this.shadowRoot.getElementById('helpModal');

        if (helpBtn) helpBtn.addEventListener('click', () => this._toggleHelp());
        if (helpClose) helpClose.addEventListener('click', () => this._toggleHelp());
        if (helpModal) helpModal.addEventListener('click', (e) => {
            if (e.target.id === 'helpModal') this._toggleHelp();
        });
    }

    _renderGame(state) {
        if (!state || !state.is_active) {
            const dailyPlayed = this._stats && this._stats.daily_played_today;

            if (dailyPlayed) {
                return `
                    <div class="no-game">
                        <h2>✅ Daily Puzzle Complete!</h2>
                        <p>
                            You've already played today's puzzle.<br>
                            Come back tomorrow for a new daily challenge!
                        </p>
                        <div class="voice-hint">
                            <strong>🎤 Want to play more?</strong><br>
                            Say <strong>"Play bonus game"</strong> to your Assist satellite for an extra puzzle!
                        </div>
                    </div>
                `;
            }

            return `
                <div class="no-game">
                    <h2>🎯 Ready to Play?</h2>
                    <p>
                        Solve 5 words connected by a theme.<br>
                        Earn points and compete on the leaderboard!
                    </p>
                    <div class="voice-hint">
                        <strong>🎤 Voice Control Only</strong><br>
                        Say <strong>"Start puzzle game"</strong> to your Assist satellite to begin!
                    </div>
                </div>
            `;
        }

        const phase = state.phase || 1;
        const wordNum = state.word_number || 1;
        const isWagerPhase = phase === 2;
        const isThemePhase = phase === 3;
        const isPostWords = phase >= 2; // Any phase after word solving

        // Check for feedback message
        let feedbackHtml = '';
        if (state.last_message && state.last_message !== this._lastMessage) {
            this._lastMessage = state.last_message;
            const isCorrect = state.last_message.toLowerCase().includes('correct');
            feedbackHtml = `<div class="feedback-message show ${isCorrect ? 'correct' : 'wrong'}">${state.last_message}</div>`;
        }

        // Solved words section
        let solvedWordsHtml = '';
        if (state.solved_words && state.solved_words.length > 0) {
            solvedWordsHtml = `
                <div class="solved-words show">
                    <div class="solved-words-label">🎯 Your Clue Words:</div>
                    <div class="solved-words-list">${state.solved_words.join(' • ')}</div>
                </div>
            `;
        }

        // Progress dots
        let progressHtml = '';
        // Convert indices to numbers to handle potential string serialization from HA
        const solvedIndices = (state.solved_word_indices || []).map(Number);
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
                    ${isWagerPhase ? '💰 MAKE YOUR WAGER!' : isThemePhase ? '🎯 FINAL ANSWER - Guess the Theme!' : `Word ${wordNum} of 5`}
                </div>
                <div class="word-blanks">${state.blanks || '_ _ _ _ _'}</div>
                ${isWagerPhase ? `
                    <div class="clue">Your score: <strong>${state.current_score || '?'}</strong> points. Wager 0 to ${state.current_score || '?'} on the theme!</div>
                    <div class="voice-hint">
                        Say: <strong>"wager [amount]"</strong>, <strong>"no wager"</strong>, or <strong>"all in"</strong><br>
                        Win = gain your wager | Lose = lose your wager
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
                <button class="period-tab ${this._leaderboardPeriod === 'weekly' ? 'active' : ''}" data-period="weekly">This Week</button>
                <button class="period-tab ${this._leaderboardPeriod === 'alltime' ? 'active' : ''}" data-period="alltime">All Time</button>
            </div>

            ${this._leaderboard ? `
                <table class="leaderboard-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
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
            ` : '<div class="loading">Loading leaderboard...</div>'}
        `;
    }

    _renderStats() {
        if (!this._stats) {
            return '<div class="loading">Loading stats...</div>';
        }

        return `
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
        `;
    }
}

// Only register if not already defined (prevents errors on hot reload)
if (!customElements.get('puzzle-game-online-panel')) {
    customElements.define('puzzle-game-online-panel', PuzzleGameOnlinePanel);
}
