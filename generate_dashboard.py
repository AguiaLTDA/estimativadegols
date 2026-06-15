import json
import sqlite3
import os

def generate_html():
    print("Generating HTML dashboard...")
    
    # 1. Load team summaries
    with open("world_cup_2026_teams.json", "r", encoding="utf-8") as f:
        teams_summary = json.load(f)
        
    # 2. Load match history from SQLite
    conn = sqlite3.connect("world_cup_2026.db")
    cursor = conn.cursor()
    
    db_data = {}
    for team_data in teams_summary:
        team = team_data["team"]
        
        cursor.execute("""
        SELECT match_date, opponent, competition, goals_scored, goals_conceded, result, opponent_fifa_rank, opponent_elo, weight
        FROM team_matches
        WHERE team = ?
        ORDER BY match_date DESC
        """, (team,))
        
        matches = []
        for row in cursor.fetchall():
            matches.append({
                "date": row[0],
                "opponent": row[1],
                "competition": row[2],
                "goals_scored": row[3],
                "goals_conceded": row[4],
                "result": row[5],
                "opp_fifa_rank": row[6],
                "opp_elo": int(round(row[7])),
                "weight": round(row[8], 2)
            })
            
        db_data[team] = {
            "summary": team_data,
            "matches": matches
        }
        
    conn.close()

    # 3. Write HTML file
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Preditivo - Copa do Mundo 2026</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0a12;
            --card-bg: rgba(25, 22, 43, 0.45);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-primary: #8b5cf6;
            --accent-secondary: #06b6d4;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem;
            background-image: 
                radial-gradient(at 10% 20%, rgba(139, 92, 246, 0.12) 0px, transparent 50%),
                radial-gradient(at 90% 80%, rgba(6, 182, 212, 0.12) 0px, transparent 50%);
            background-attachment: fixed;
        }}

        .wrapper {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 3rem;
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #a78bfa, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        p.subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
        }}

        /* Simulator / Comparison Section */
        .simulator-section {{
            background: rgba(30, 27, 51, 0.3);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2rem;
            margin-bottom: 3rem;
            backdrop-filter: blur(15px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }}

        .simulator-title {{
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: linear-gradient(to right, #f472b6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .simulator-controls {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
            margin-bottom: 1.5rem;
        }}

        .sim-select-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            min-width: 250px;
            flex: 1;
        }}

        .sim-select-label {{
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .sim-select {{
            background: rgba(15, 13, 28, 0.8);
            border: 1px solid var(--card-border);
            padding: 0.9rem 1.2rem;
            border-radius: 12px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 1rem;
            outline: none;
            cursor: pointer;
            width: 100%;
            transition: border-color 0.3s ease;
        }}

        .sim-select:focus {{
            border-color: var(--accent-secondary);
        }}

        .vs-badge {{
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: #fff;
            width: 42px;
            height: 42px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
            margin-top: 1.2rem;
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.4);
        }}

        .compare-btn {{
            background: linear-gradient(to right, #8b5cf6, #06b6d4);
            border: none;
            padding: 0.9rem 2rem;
            border-radius: 12px;
            color: white;
            font-family: inherit;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 1.2rem;
            box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2);
        }}

        .compare-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4);
        }}

        /* Simulation Results */
        .sim-results-card {{
            display: none;
            background: rgba(15, 13, 28, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.8rem;
            margin-top: 1.5rem;
            animation: fadeIn 0.5s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .sim-results-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }}

        @media (min-width: 768px) {{
            .sim-results-grid {{
                grid-template-columns: 2fr 1fr;
            }}
        }}

        .probability-header {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--accent-secondary);
        }}

        /* Probability Bar Chart */
        .prob-bar-container {{
            display: flex;
            height: 36px;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }}

        .prob-bar-part {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.85rem;
            color: #fff;
            transition: width 0.5s ease;
        }}

        .prob-bar-part.winA {{ background: var(--success); }}
        .prob-bar-part.draw {{ background: #4b5563; }}
        .prob-bar-part.winB {{ background: var(--danger); }}

        .prob-labels {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }}

        .prob-label-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .color-dot {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }}

        /* Expected Score Panel */
        .score-panel {{
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.2rem;
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}

        .score-num {{
            font-size: 2.2rem;
            font-weight: 700;
            color: #fff;
            margin: 0.5rem 0;
            text-shadow: 0 0 10px rgba(34, 211, 238, 0.3);
        }}

        .score-chance {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}

        /* Stats Matchups */
        .metric-matchup-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.8rem;
            font-size: 0.9rem;
        }}

        .matchup-bar-wrapper {{
            flex: 1;
            height: 8px;
            background: rgba(255,255,255,0.05);
            border-radius: 4px;
            margin: 0 1rem;
            overflow: hidden;
            display: flex;
        }}

        .matchup-bar-fill {{
            height: 100%;
        }}

        /* Grid filter tools */
        .filter-section {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-bottom: 2rem;
        }}

        .search-bar {{
            flex: 1;
            min-width: 250px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.8rem 1.2rem;
            border-radius: 12px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 1rem;
            outline: none;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}

        .search-bar:focus {{
            border-color: var(--accent-secondary);
            box-shadow: 0 0 15px rgba(6, 182, 212, 0.2);
        }}

        .sort-select {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.8rem 1.2rem;
            border-radius: 12px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 1rem;
            outline: none;
            cursor: pointer;
            min-width: 200px;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}

        .sort-select:focus {{
            border-color: var(--accent-primary);
        }}

        /* Cards Grid */
        .teams-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
        }}

        .team-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(12px);
            position: relative;
            overflow: hidden;
        }}

        .team-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(to right, var(--accent-primary), var(--accent-secondary));
            opacity: 0;
            transition: opacity 0.3s ease;
        }}

        .team-card:hover {{
            transform: translateY(-5px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
        }}

        .team-card:hover::before {{
            opacity: 1;
        }}

        .team-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.2rem;
        }}

        .team-name {{
            font-size: 1.4rem;
            font-weight: 600;
        }}

        .fifa-badge {{
            background: rgba(6, 182, 212, 0.15);
            color: var(--accent-secondary);
            padding: 0.25rem 0.6rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .stat-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.6rem;
            font-size: 0.95rem;
        }}

        .stat-label {{
            color: var(--text-muted);
        }}

        .stat-value {{
            font-weight: 600;
        }}

        /* Modal styling */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }}

        .modal-overlay.active {{
            opacity: 1;
            pointer-events: auto;
        }}

        .modal-content {{
            background: #11101b;
            border: 1px solid var(--card-border);
            width: 90%;
            max-width: 850px;
            max-height: 85vh;
            border-radius: 24px;
            padding: 2rem;
            overflow-y: auto;
            position: relative;
            transform: scale(0.9);
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }}

        .modal-overlay.active .modal-content {{
            transform: scale(1);
        }}

        .close-btn {{
            position: absolute;
            top: 1.5rem;
            right: 1.5rem;
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.8rem;
            cursor: pointer;
            transition: color 0.2s ease;
        }}

        .close-btn:hover {{
            color: var(--text-main);
        }}

        .modal-title-wrapper {{
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1rem;
        }}

        .modal-title {{
            font-size: 2rem;
            font-weight: 700;
        }}

        .modal-grid-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .modal-stat-card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
        }}

        .modal-stat-title {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 0.3rem;
            text-transform: uppercase;
        }}

        .modal-stat-number {{
            font-size: 1.3rem;
            font-weight: 700;
        }}

        .match-history-title {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }}

        .matches-table-wrapper {{
            overflow-x: auto;
        }}

        .matches-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }}

        .matches-table th {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--card-border);
            color: var(--text-muted);
            font-weight: 600;
        }}

        .matches-table td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }}

        .result-badge {{
            display: inline-block;
            width: 24px;
            height: 24px;
            line-height: 24px;
            text-align: center;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.8rem;
        }}

        .result-badge.w {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
        .result-badge.d {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}
        .result-badge.l {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
    </style>
</head>
<body>

    <div class="wrapper">
        <header>
            <h1>Copa do Mundo 2026</h1>
            <p class="subtitle">Base de Dados Preditiva das Seleções Qualificadas</p>
        </header>

        <!-- Poisson Simulator Section -->
        <div class="simulator-section">
            <div class="simulator-title">
                <span style="font-size: 1.6rem;">🔮</span> Simulador de Confrontos (Modelo de Poisson)
            </div>
            
            <div class="simulator-controls">
                <div class="sim-select-wrapper">
                    <span class="sim-select-label">Seleção A</span>
                    <select id="teamASelect" class="sim-select"></select>
                </div>
                <div class="vs-badge">VS</div>
                <div class="sim-select-wrapper">
                    <span class="sim-select-label">Seleção B</span>
                    <select id="teamBSelect" class="sim-select"></select>
                </div>
                <button id="compareBtn" class="compare-btn">Simular Partida</button>
            </div>

            <!-- Simulation Results Card -->
            <div id="simResultsCard" class="sim-results-card">
                <div class="sim-results-grid">
                    <div>
                        <div class="probability-header">Probabilidades do Confronto</div>
                        <div class="prob-bar-container">
                            <div id="probWinA" class="prob-bar-part winA" title="Vitória Seleção A">33%</div>
                            <div id="probDraw" class="prob-bar-part draw" title="Empate">33%</div>
                            <div id="probWinB" class="prob-bar-part winB" title="Vitória Seleção B">33%</div>
                        </div>
                        <div class="prob-labels">
                            <span class="prob-label-item">
                                <span class="color-dot" style="background: var(--success);"></span>
                                <span id="labelTeamA">Seleção A</span>: <strong id="valWinA">0%</strong>
                            </span>
                            <span class="prob-label-item">
                                <span class="color-dot" style="background: #4b5563;"></span>
                                Empate: <strong id="valDraw">0%</strong>
                            </span>
                            <span class="prob-label-item">
                                <span class="color-dot" style="background: var(--danger);"></span>
                                <span id="labelTeamB">Seleção B</span>: <strong id="valWinB">0%</strong>
                            </span>
                        </div>

                        <!-- Mini matchup indicators -->
                        <div class="metric-matchup-row">
                            <span id="matchupStatValA_1">0.0</span>
                            <span style="color: var(--text-muted); font-size: 0.85rem;">Gols Esperados (xG)</span>
                            <span id="matchupStatValB_1">0.0</span>
                        </div>
                        <div class="metric-matchup-row">
                            <span id="matchupStatValA_2">0%</span>
                            <span style="color: var(--text-muted); font-size: 0.85rem;">Ambas Marcam (BTTS)</span>
                            <span id="matchupStatValB_2">0%</span>
                        </div>
                        <div class="metric-matchup-row">
                            <span id="matchupStatValA_3">0%</span>
                            <span style="color: var(--text-muted); font-size: 0.85rem;">Mais de 2.5 Gols (Over 2.5)</span>
                            <span id="matchupStatValB_3">0%</span>
                        </div>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 1rem;">
                        <div class="score-panel">
                            <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Placar Mais Provável</div>
                            <div id="predictedScore" class="score-num">2 - 1</div>
                            <div id="predictedScoreChance" class="score-chance">Probabilidade: 0%</div>
                        </div>
                        <div class="score-panel" style="background: rgba(6, 182, 212, 0.04); border-color: rgba(6, 182, 212, 0.15);">
                            <div style="font-size: 0.8rem; color: var(--accent-secondary); font-weight: 600; text-transform: uppercase;">Total de Gols Esperados</div>
                            <div id="expectedTotalGoals" style="font-size: 1.8rem; font-weight: 700; margin: 0.2rem 0;">2.84</div>
                            <div style="font-size: 0.80rem; color: var(--text-muted);">Média da partida</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Grid Filter Tools -->
        <div class="filter-section">
            <input type="text" id="searchInput" class="search-bar" placeholder="Buscar seleção na lista...">
            <select id="sortSelect" class="sort-select">
                <option value="elo-desc">Elo Rating (Maior)</option>
                <option value="elo-asc">Elo Rating (Menor)</option>
                <option value="fifa-asc">Ranking FIFA (Melhor)</option>
                <option value="form-desc">Forma Recente</option>
                <option value="attack-desc">Força de Ataque</option>
                <option value="defense-asc">Força de Defesa (Melhor)</option>
            </select>
        </div>

        <!-- Teams Grid -->
        <div class="teams-grid" id="teamsGrid"></div>
    </div>

    <!-- Detailed Modal Overlay -->
    <div class="modal-overlay" id="modalOverlay">
        <div class="modal-content">
            <button class="close-btn" id="closeBtn">&times;</button>
            <div class="modal-title-wrapper">
                <span class="modal-title" id="modalTeamName">Brasil</span>
            </div>
            
            <div class="modal-grid-stats" id="modalStatsGrid"></div>

            <div class="match-history-title">Últimos 20 Jogos</div>
            <div class="matches-table-wrapper">
                <table class="matches-table">
                    <thead>
                        <tr>
                            <th>Data</th>
                            <th>Resultado</th>
                            <th>Placar</th>
                            <th>Adversário</th>
                            <th>Competição</th>
                            <th>Elo Adv.</th>
                            <th>Rank FIFA Adv.</th>
                            <th>Peso</th>
                        </tr>
                    </thead>
                    <tbody id="matchesTableBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Injected payload
        const dbData = {json.dumps(db_data, ensure_ascii=False)};
        
        // Calculate average defense strength dynamically across all 48 teams
        const allTeams = Object.values(dbData);
        const avgDefense = allTeams.reduce((sum, t) => sum + t.summary.defense_strength, 0) / allTeams.length;

        const teamsGrid = document.getElementById('teamsGrid');
        const searchInput = document.getElementById('searchInput');
        const sortSelect = document.getElementById('sortSelect');
        const modalOverlay = document.getElementById('modalOverlay');
        const closeBtn = document.getElementById('closeBtn');

        // Selects for simulation
        const teamASelect = document.getElementById('teamASelect');
        const teamBSelect = document.getElementById('teamBSelect');
        const compareBtn = document.getElementById('compareBtn');
        const simResultsCard = document.getElementById('simResultsCard');

        // Populate simulation select dropdowns
        function populateSelectors() {{
            const sortedNames = Object.keys(dbData).sort();
            
            teamASelect.innerHTML = '';
            teamBSelect.innerHTML = '';
            
            sortedNames.forEach((name, idx) => {{
                const optionA = document.createElement('option');
                optionA.value = name;
                optionA.text = name;
                teamASelect.appendChild(optionA);
                
                const optionB = document.createElement('option');
                optionB.value = name;
                optionB.text = name;
                teamBSelect.appendChild(optionB);
            }});
            
            // Set defaults (ex: Argentina vs Brazil)
            if (dbData["Argentina"]) teamASelect.value = "Argentina";
            if (dbData["Brazil"]) teamBSelect.value = "Brazil";
        }}

        // Poisson calculation helper
        function poissonProbability(k, lambda) {{
            if (lambda <= 0) return k === 0 ? 1 : 0;
            let factorial = 1;
            for (let i = 2; i <= k; i++) factorial *= i;
            return (Math.pow(lambda, k) * Math.exp(-lambda)) / factorial;
        }}

        // Run Poisson Match Simulation
        function simulateMatch() {{
            const teamA = teamASelect.value;
            const teamB = teamBSelect.value;
            
            if (teamA === teamB) {{
                alert("Por favor, selecione duas equipes diferentes para simular o confronto.");
                return;
            }}
            
            const statsA = dbData[teamA].summary;
            const statsB = dbData[teamB].summary;
            
            // Calculate lambda (Expected Goals) for each team
            // ExpG = Attack_A * Defense_B / AvgDefense
            const lambdaA = (statsA.attack_strength * statsB.defense_strength) / avgDefense;
            const lambdaB = (statsB.attack_strength * statsA.defense_strength) / avgDefense;
            
            // Grid simulation (up to 9 goals)
            let winA = 0;
            let winB = 0;
            let draw = 0;
            let over1_5 = 0;
            let over2_5 = 0;
            let btts = 0;
            
            let maxProb = -1;
            let bestScore = [0, 0];
            
            // 10x10 score grid
            for (let x = 0; x < 10; x++) {{
                const probX = poissonProbability(x, lambdaA);
                for (let y = 0; y < 10; y++) {{
                    const probY = poissonProbability(y, lambdaB);
                    const probXY = probX * probY;
                    
                    if (x > y) winA += probXY;
                    else if (x < y) winB += probXY;
                    else draw += probXY;
                    
                    if (x + y > 1) over1_5 += probXY;
                    if (x + y > 2) over2_5 += probXY;
                    if (x > 0 && y > 0) btts += probXY;
                    
                    if (probXY > maxProb) {{
                        maxProb = probXY;
                        bestScore = [x, y];
                    }}
                }}
            }}
            
            // Normalize probabilities to sum to 1.0 (since we capped grid at 9)
            const sumP = winA + winB + draw;
            winA = winA / sumP;
            winB = winB / sumP;
            draw = draw / sumP;
            
            // Update UI Elements
            document.getElementById('labelTeamA').innerText = teamA;
            document.getElementById('labelTeamB').innerText = teamB;
            
            document.getElementById('valWinA').innerText = (winA * 100).toFixed(1) + '%';
            document.getElementById('valDraw').innerText = (draw * 100).toFixed(1) + '%';
            document.getElementById('valWinB').innerText = (winB * 100).toFixed(1) + '%';
            
            const barA = document.getElementById('probWinA');
            const barDraw = document.getElementById('probDraw');
            const barB = document.getElementById('probWinB');
            
            barA.style.width = (winA * 100) + '%';
            barDraw.style.width = (draw * 100) + '%';
            barB.style.width = (winB * 100) + '%';
            
            barA.innerText = (winA * 100).toFixed(0) + '%';
            barDraw.innerText = (draw * 100).toFixed(0) + '%';
            barB.innerText = (winB * 100).toFixed(0) + '%';
            
            // Placar esperado
            document.getElementById('predictedScore').innerText = `${{bestScore[0]}} - ${{bestScore[1]}}`;
            document.getElementById('predictedScoreChance').innerText = `Probabilidade: ${{(maxProb * 100).toFixed(1)}}%`;
            document.getElementById('expectedTotalGoals').innerText = (lambdaA + lambdaB).toFixed(2);
            
            // Stats matchups numbers
            document.getElementById('matchupStatValA_1').innerText = lambdaA.toFixed(2) + " xG";
            document.getElementById('matchupStatValB_1').innerText = lambdaB.toFixed(2) + " xG";
            
            document.getElementById('matchupStatValA_2').innerText = (btts * 100).toFixed(1) + '%';
            document.getElementById('matchupStatValB_2').innerText = "Sim";
            
            document.getElementById('matchupStatValA_3').innerText = (over2_5 * 100).toFixed(1) + '%';
            document.getElementById('matchupStatValB_3').innerText = "Sim";
            
            simResultsCard.style.display = 'block';
        }}

        compareBtn.addEventListener('click', simulateMatch);

        // Render cards
        function renderTeams(filteredTeams) {{
            teamsGrid.innerHTML = '';
            
            filteredTeams.forEach(teamName => {{
                const team = dbData[teamName];
                const sum = team.summary;
                
                const card = document.createElement('div');
                card.className = 'team-card';
                card.innerHTML = `
                    <div class="team-header">
                        <div class="team-name">${{sum.team}}</div>
                        <div class="fifa-badge">Rank #${{sum.fifa_rank}}</div>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Elo Rating</span>
                        <span class="stat-value" style="color: var(--accent-secondary);">${{sum.elo}}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Gols Pro / Contra (Pond.)</span>
                        <span class="stat-value" style="color: #fff;">${{sum.weighted_goals_scored.toFixed(2)}} / ${{sum.weighted_goals_conceded.toFixed(2)}}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Ataque Ajustado</span>
                        <span class="stat-value" style="color: var(--success);">${{sum.attack_strength.toFixed(2)}}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Defesa Ajustada</span>
                        <span class="stat-value" style="color: var(--danger);">${{sum.defense_strength.toFixed(2)}}</span>
                    </div>
                    <div class="stat-row" style="margin-top: 0.8rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.6rem;">
                        <span class="stat-label">V / E / D (Pond.)</span>
                        <span class="stat-value">${{(sum.weighted_win_rate*100).toFixed(0)}}% / ${{((sum.weighted_draw_rate)*100).toFixed(0)}}% / ${{((sum.weighted_loss_rate)*100).toFixed(0)}}%</span>
                    </div>
                `;
                
                card.addEventListener('click', () => openModal(teamName));
                teamsGrid.appendChild(card);
            }});
        }}

        // Sort and Filter logic
        function getFilteredAndSortedTeams() {{
            const query = searchInput.value.toLowerCase();
            const sortVal = sortSelect.value;
            
            let teamKeys = Object.keys(dbData).filter(team => 
                team.toLowerCase().includes(query)
            );
            
            teamKeys.sort((a, b) => {{
                const sumA = dbData[a].summary;
                const sumB = dbData[b].summary;
                
                if (sortVal === 'elo-desc') return sumB.elo - sumA.elo;
                if (sortVal === 'elo-asc') return sumA.elo - sumB.elo;
                if (sortVal === 'fifa-asc') return sumA.fifa_rank - sumB.fifa_rank;
                if (sortVal === 'form-desc') return sumB.form_index - sumA.form_index;
                if (sortVal === 'attack-desc') return sumB.attack_strength - sumA.attack_strength;
                if (sortVal === 'defense-asc') return sumA.defense_strength - sumB.defense_strength;
                return 0;
            }});
            
            return teamKeys;
        }}

        function updateView() {{
            renderTeams(getFilteredAndSortedTeams());
        }}

        searchInput.addEventListener('input', updateView);
        sortSelect.addEventListener('change', updateView);

        // Modal Logic
        function openModal(teamName) {{
            const team = dbData[teamName];
            const sum = team.summary;
            
            document.getElementById('modalTeamName').innerText = sum.team;
            
            const statsGrid = document.getElementById('modalStatsGrid');
            statsGrid.innerHTML = `
                <div class="modal-stat-card">
                    <div class="modal-stat-title">RANKING FIFA</div>
                    <div class="modal-stat-number" style="color: var(--accent-secondary);">#${{sum.fifa_rank}}</div>
                </div>
                <div class="modal-stat-card">
                    <div class="modal-stat-title">ELO RATING</div>
                    <div class="modal-stat-number" style="color: var(--accent-primary);">${{sum.elo}}</div>
                </div>
                <div class="modal-stat-card">
                    <div class="modal-stat-title">ÍNDICE DE FORMA</div>
                    <div class="modal-stat-number" style="color: #fff;">${{sum.form_index}}</div>
                </div>
                <div class="modal-stat-card">
                    <div class="modal-stat-title">GOLS PRO (Pond.)</div>
                    <div class="modal-stat-number" style="color: var(--success);">${{sum.weighted_goals_scored.toFixed(2)}}</div>
                </div>
                <div class="modal-stat-card">
                    <div class="modal-stat-title">GOLS CONTRA (Pond.)</div>
                    <div class="modal-stat-number" style="color: var(--danger);">${{sum.weighted_goals_conceded.toFixed(2)}}</div>
                </div>
                <div class="modal-stat-card">
                    <div class="modal-stat-title">FORÇA OFENSIVA</div>
                    <div class="modal-stat-number" style="color: var(--success);">${{sum.attack_strength.toFixed(2)}}</div>
                </div>
                <div class="modal-stat-card">
                    <div class="modal-stat-title">FORÇA DEFENSIVA</div>
                    <div class="modal-stat-number" style="color: var(--danger);">${{sum.defense_strength.toFixed(2)}}</div>
                </div>
                <div class="modal-stat-card">
                    <div class="modal-stat-title">FORÇA ADVERSÁRIOS</div>
                    <div class="modal-stat-number">${{sum.opponent_strength}}</div>
                </div>
            `;
            
            const matchesTableBody = document.getElementById('matchesTableBody');
            matchesTableBody.innerHTML = '';
            
            team.matches.forEach(m => {{
                const row = document.createElement('tr');
                const scoreStr = `${{m.goals_scored}} - ${{m.goals_conceded}}`;
                
                row.innerHTML = `
                    <td>${{m.date}}</td>
                    <td><span class="result-badge ${{m.result.toLowerCase()}}">${{m.result}}</span></td>
                    <td style="font-weight: 600;">${{scoreStr}}</td>
                    <td style="font-weight: 500;">${{m.opponent}}</td>
                    <td>${{m.competition}}</td>
                    <td>${{m.opp_elo}}</td>
                    <td>#${{m.opp_fifa_rank}}</td>
                    <td>${{m.weight.toFixed(2)}}</td>
                `;
                matchesTableBody.appendChild(row);
            }});
            
            modalOverlay.classList.add('active');
        }}

        function closeModal() {{
            modalOverlay.classList.remove('active');
        }}

        closeBtn.addEventListener('click', closeModal);
        modalOverlay.addEventListener('click', (e) => {{
            if (e.target === modalOverlay) closeModal();
        }});

        // Initialize selectors and view
        populateSelectors();
        updateView();
    </script>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Dashboard HTML created successfully as 'index.html'!")

if __name__ == "__main__":
    generate_html()
