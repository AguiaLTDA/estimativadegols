import json
import sqlite3
import os

def generate_html():
    print("Generating HTML dashboard...")
    from datetime import datetime, timezone, timedelta
    last_update_str = datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M") + " BRT"
    
    # 1. Load team summaries
    with open("world_cup_2026_teams.json", "r", encoding="utf-8") as f:
        teams_summary = json.load(f)
        
    # 2. Load data from SQLite
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
        
    # 3. Load simulations
    cursor.execute("""
    SELECT match_number, match_date, group_name, home_team, away_team, 
           expected_goals_home, expected_goals_away, prob_win_home, prob_draw, prob_win_away, 
           prob_over_1_5, prob_over_2_5, prob_btts, predicted_score_home, predicted_score_away, 
           is_over_1_5_alert, is_over_2_5_alert, real_goals_home, real_goals_away, kickoff_utc,
           gas_home, gas_away, gas_desc_home, gas_desc_away, is_gas_alert,
           stage, yc_home, yc_away, rc_home, rc_away,
           exp_corners_home, exp_corners_away, exp_shots_home, exp_shots_away,
           exp_shots_on_target_home, exp_shots_on_target_away,
           sim_corners_home, sim_corners_away, sim_shots_home, sim_shots_away,
           sim_shots_on_target_home, sim_shots_on_target_away
    FROM group_stage_simulations
    ORDER BY match_number ASC
    """)
    
    group_simulations = []
    for row in cursor.fetchall():
        group_simulations.append({
            "match_number": row[0],
            "date": row[1],
            "group": row[2],
            "home_team": row[3],
            "away_team": row[4],
            "exp_g_home": row[5],
            "exp_g_away": row[6],
            "prob_win_home": row[7],
            "prob_draw": row[8],
            "prob_win_away": row[9],
            "prob_over_1_5": row[10],
            "prob_over_2_5": row[11],
            "prob_btts": row[12],
            "pred_home": row[13],
            "pred_away": row[14],
            "is_alert_1_5": row[15],
            "is_alert_2_5": row[16],
            "is_alert": 1 if (row[15] or row[16]) else 0,
            "real_home": row[17],
            "real_away": row[18],
            "kickoff": row[19],
            "gas_home": row[20],
            "gas_away": row[21],
            "gas_desc_home": row[22],
            "gas_desc_away": row[23],
            "is_gas_alert": row[24],
            "stage": row[25],
            "yc_home": row[26],
            "yc_away": row[27],
            "rc_home": row[28],
            "rc_away": row[29],
            "exp_corners_home": row[30],
            "exp_corners_away": row[31],
            "exp_shots_home": row[32],
            "exp_shots_away": row[33],
            "exp_shots_on_target_home": row[34],
            "exp_shots_on_target_away": row[35],
            "sim_corners_home": row[36],
            "sim_corners_away": row[37],
            "sim_shots_home": row[38],
            "sim_shots_away": row[39],
            "sim_shots_on_target_home": row[40],
            "sim_shots_on_target_away": row[41]
        })
        
    conn.close()

    # 4. Write HTML file
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Copa do Mundo - Previsão de resultados</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #08070d;
            --card-bg: rgba(20, 18, 36, 0.45);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-primary: #8b5cf6;
            --accent-secondary: #06b6d4;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --pink-alert: #ec4899;
            --cyan-alert: #06b6d4;
            --gas-alert: #f97316;
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
            padding: 2rem 1rem;
            background-image: 
                radial-gradient(at 10% 15%, rgba(139, 92, 246, 0.15) 0px, transparent 50%),
                radial-gradient(at 90% 85%, rgba(6, 182, 212, 0.15) 0px, transparent 50%);
            background-attachment: fixed;
        }}

        .wrapper {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 2.5rem;
        }}

        h1 {{
            font-size: 2.6rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #a78bfa, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        p.subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
            margin-bottom: 0.25rem;
        }}

        .last-update {{
            color: var(--text-muted);
            font-size: 0.8rem;
            opacity: 0.85;
            margin-top: 0.25rem;
        }}

        /* Navigation Tabs */
        .tabs-nav {{
            display: flex;
            justify-content: center;
            gap: 0.75rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1rem;
        }}

        .tab-btn {{
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--card-border);
            color: var(--text-muted);
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            font-family: inherit;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }}

        .tab-btn:hover {{
            color: var(--text-main);
            background: rgba(255,255,255,0.06);
            border-color: rgba(255,255,255,0.15);
        }}

        .tab-btn.active {{
            color: #fff;
            background: linear-gradient(to right, var(--accent-primary), var(--accent-secondary));
            border-color: transparent;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
        }}

        .tab-btn.alert-tab-btn {{
            border-color: rgba(236, 72, 153, 0.2);
            color: #f472b6;
        }}

        .tab-btn.alert-tab-btn:hover {{
            background: rgba(236, 72, 153, 0.05);
            border-color: rgba(236, 72, 153, 0.5);
        }}

        .tab-btn.alert-tab-btn.active {{
            background: linear-gradient(to right, var(--pink-alert), #d946ef);
            color: #fff;
            border-color: transparent;
            box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
        }}

        /* Tab Content panels */
        .tab-content {{
            display: none;
            animation: fadeIn 0.4s ease-out;
        }}

        .tab-content.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Simulator / Comparison Section */
        .simulator-section {{
            background: rgba(30, 27, 51, 0.25);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2rem;
            backdrop-filter: blur(15px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }}

        .simulator-title {{
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
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

        .metric-matchup-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.8rem;
            font-size: 0.9rem;
        }}

        /* Timeline / Matches table for Phase List */
        .timeline-section {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .timeline-date-group {{
            background: rgba(20, 18, 36, 0.35);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
        }}

        .timeline-date-header {{
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 1rem;
            border-left: 4px solid var(--accent-secondary);
            padding-left: 0.75rem;
            color: var(--accent-secondary);
        }}

        .match-row-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.2rem;
        }}

        .match-item-card {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: border-color 0.2s ease;
        }}

        .match-item-card:hover {{
            border-color: rgba(255,255,255,0.08);
        }}

        .match-item-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 0.6rem;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            padding-bottom: 0.4rem;
        }}

        .match-item-teams {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 0.6rem;
        }}

        .match-item-score-prediction {{
            text-align: center;
            background: rgba(139, 92, 246, 0.08);
            border: 1px dashed rgba(139, 92, 246, 0.2);
            border-radius: 8px;
            padding: 0.5rem;
            font-size: 0.85rem;
            margin-bottom: 0.6rem;
        }}

        .match-item-footer-stats {{
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        /* Alerts Styling */
        .alerts-intro {{
            background: rgba(236, 72, 153, 0.08);
            border: 1px solid rgba(236, 72, 153, 0.2);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            display: flex;
            gap: 1rem;
            align-items: center;
        }}

        .alerts-icon {{
            font-size: 2.2rem;
            color: var(--pink-alert);
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.1); opacity: 0.8; }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}

        .alert-card-glow-over25 {{
            position: relative;
            border: 1px solid rgba(236, 72, 153, 0.25) !important;
            background: rgba(236, 72, 153, 0.03) !important;
        }}

        .alert-card-glow-over25::after {{
            content: 'ALERTA 70%+ OVER 2.5';
            position: absolute;
            top: -10px;
            right: 15px;
            background: linear-gradient(to right, var(--pink-alert), #d946ef);
            color: #fff;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            box-shadow: 0 0 10px rgba(236, 72, 153, 0.4);
        }}

        .alert-card-glow-over15 {{
            position: relative;
            border: 1px solid rgba(6, 182, 212, 0.25) !important;
            background: rgba(6, 182, 212, 0.03) !important;
        }}

        .alert-card-glow-over15::after {{
            content: 'ALERTA 85%+ OVER 1.5';
            position: absolute;
            top: -10px;
            right: 15px;
            background: linear-gradient(to right, var(--cyan-alert), #0891b2);
            color: #fff;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            box-shadow: 0 0 10px rgba(6, 182, 212, 0.4);
        }}

        .alert-card-glow-gas {{
            position: relative;
            border: 1px solid rgba(249, 115, 22, 0.3) !important;
            background: rgba(249, 115, 22, 0.03) !important;
        }}

        .alert-card-glow-gas::after {{
            content: 'ALERTA GÁS 80%+';
            position: absolute;
            top: -10px;
            right: 15px;
            background: linear-gradient(to right, var(--gas-alert), #f97316);
            color: #fff;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            box-shadow: 0 0 10px rgba(249, 115, 22, 0.4);
        }}

        .alert-value-highlight {{
            color: var(--pink-alert) !important;
            font-weight: 700;
        }}

        .alert-value-highlight-over15 {{
            color: var(--cyan-alert) !important;
            font-weight: 700;
        }}

        .alert-value-highlight-gas {{
            color: var(--gas-alert) !important;
            font-weight: 700;
        }}

        /* Filters and general grid */
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

        .clickable-team {{
            cursor: pointer;
            transition: color 0.2s ease;
        }}
        
        .clickable-team:hover {{
            color: var(--accent-secondary) !important;
            text-decoration: underline;
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

        /* Time Control Panel */
        .time-control-panel {{
            background: rgba(15, 13, 28, 0.65);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.2rem;
            margin-bottom: 1.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }}

        @media (min-width: 768px) {{
            .time-control-panel {{
                flex-direction: row;
                padding: 1rem 1.8rem;
            }}
        }}

        .time-control-title {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--accent-secondary);
        }}

        .calendar-icon {{
            font-size: 1.3rem;
        }}

        .time-control-actions {{
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }}

        .time-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            font-size: 0.85rem;
            user-select: none;
        }}

        .time-btn:hover {{
            background: var(--accent-secondary);
            color: #000;
            border-color: var(--accent-secondary);
            box-shadow: 0 0 10px rgba(34, 211, 238, 0.3);
        }}

        .copa-date-picker {{
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 0.5rem 0.8rem;
            border-radius: 8px;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.9rem;
            outline: none;
            cursor: pointer;
            text-align: center;
        }}

        .copa-date-picker:focus {{
            border-color: var(--accent-secondary);
            box-shadow: 0 0 8px rgba(34, 211, 238, 0.25);
        }}

        .time-control-status {{
            font-size: 0.9rem;
            color: var(--text-muted);
            font-weight: 500;
        }}

        .match-item-real-result {{
            text-align: center;
            background: rgba(16, 185, 129, 0.06);
            border: 1px solid rgba(16, 185, 129, 0.15);
            border-radius: 8px;
            padding: 0.5rem;
            font-size: 0.85rem;
            margin-bottom: 0.6rem;
            color: var(--text-main);
        }}

        .match-item-real-result.waiting {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px dashed rgba(255, 255, 255, 0.08);
            color: var(--text-muted);
        }}
        
        .match-item-card.match-played {{
            background: rgba(16, 185, 129, 0.03) !important;
            border-color: rgba(16, 185, 129, 0.12) !important;
        }}
        
        .match-item-card.match-played .match-item-header span {{
            color: rgba(16, 185, 129, 0.6) !important;
        }}

        /* Styled Switch Toggle */
        .toggle-container {{
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 1.5rem;
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--card-border);
            padding: 0.8rem 1.2rem;
            border-radius: 12px;
            width: fit-content;
        }}

        .switch {{
            position: relative;
            display: inline-block;
            width: 48px;
            height: 24px;
        }}

        .switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}

        .slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(255,255,255,0.1);
            transition: .3s;
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.1);
        }}

        .slider:before {{
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 3px;
            bottom: 3px;
            background-color: var(--text-muted);
            transition: .3s;
            border-radius: 50%;
        }}

        input:checked + .slider {{
            background-color: rgba(139, 92, 246, 0.2);
            border-color: var(--accent-primary);
        }}

        input:checked + .slider:before {{
            transform: translateX(24px);
            background-color: var(--accent-secondary);
            box-shadow: 0 0 8px rgba(34, 211, 238, 0.6);
        }}

        .toggle-label {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-main);
            user-select: none;
            cursor: pointer;
        }}
    </style>
</head>
<body>

    <div class="wrapper">
        <header>
            <h1>Copa do Mundo - Previsão de resultados</h1>
            <p class="subtitle">Base de Dados Preditiva das Seleções Qualificadas</p>
            <p class="last-update">Última atualização: {last_update_str}</p>
        </header>

        <!-- Time Control Panel -->
        <div class="time-control-panel">
            <div class="time-control-title">
                <span class="calendar-icon">📅</span>
                <span>Controle de Tempo da Copa 2026</span>
            </div>
            <div class="time-control-actions">
                <button id="prevDayBtn" class="time-btn">◀ Dia Anterior</button>
                <input type="date" id="copaDateInput" class="copa-date-picker" min="2026-06-11" max="2026-07-19" value="2026-06-15">
                <button id="nextDayBtn" class="time-btn">Próximo Dia ▶</button>
            </div>
            <div class="time-control-status" id="timeControlStatus">
                Carregando...
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-nav">
            <button class="tab-btn" onclick="switchTab(event, 'simulador')">🔮 Simulador de Jogos</button>
            <button class="tab-btn active" onclick="switchTab(event, 'fase-grupos')">📅 JOGOS COPA!</button>
            <button class="tab-btn alert-tab-btn" onclick="switchTab(event, 'alertas')">🚨 Alertas de Gols <span id="alertsBadge" style="background: linear-gradient(135deg, var(--pink-alert), var(--cyan-alert)); color: #fff; padding: 0.1rem 0.4rem; border-radius: 6px; font-size: 0.75rem; margin-left: 0.3rem;">0</span></button>
            <button class="tab-btn" onclick="switchTab(event, 'selecoes')">🏳️  Diretório de Seleções</button>
        </div>

        <!-- TAB 1: SIMULADOR DE JOGOS -->
        <div id="simulador" class="tab-content">
            <div class="simulator-section">
                <div class="simulator-title">
                    Simular Confronto (Modelo de Poisson)
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

                            <!-- Matchup stats -->
                            <div class="metric-matchup-row">
                                <span id="matchupStatValA_1">0.0</span>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">Gols Esperados (xG)</span>
                                <span id="matchupStatValB_1">0.0</span>
                            </div>
                            <div class="metric-matchup-row">
                                <span id="matchupStatValA_4">0.0</span>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">Escanteios Esperados</span>
                                <span id="matchupStatValB_4">0.0</span>
                            </div>
                            <div class="metric-matchup-row">
                                <span id="matchupStatValA_5">0.0</span>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">Chutes Esperados</span>
                                <span id="matchupStatValB_5">0.0</span>
                            </div>
                            <div class="metric-matchup-row">
                                <span id="matchupStatValA_6">0.0</span>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">Chutes no Alvo Esperados</span>
                                <span id="matchupStatValB_6">0.0</span>
                            </div>
                            <div class="metric-matchup-row">
                                <span id="matchupStatValA_2">0%</span>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">Ambas Marcam (BTTS)</span>
                                <span id="matchupStatValB_2">Sim</span>
                            </div>
                            <div class="metric-matchup-row">
                                <span id="matchupStatValA_15">0%</span>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">Mais de 1.5 Gols (Over 1.5)</span>
                                <span id="matchupStatValB_15">Sim</span>
                            </div>
                            <div class="metric-matchup-row">
                                <span id="matchupStatValA_3">0%</span>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">Mais de 2.5 Gols (Over 2.5)</span>
                                <span id="matchupStatValB_3">Sim</span>
                            </div>
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
        </div>

        <!-- TAB 2: FASE DE GRUPOS CRONOLÓGICA -->
        <div id="fase-grupos" class="tab-content active">
            <!-- Day Filter Toggle -->
            <div class="toggle-container">
                <label class="switch">
                    <input type="checkbox" id="onlySelectedDayToggle" checked>
                    <span class="slider"></span>
                </label>
                <span class="toggle-label" id="toggleLabel">Mostrar apenas jogos do dia selecionado</span>
            </div>
            <div class="timeline-section" id="timelineSection"></div>
        </div>

        <!-- TAB 3: ALERTAS OVER 2.5 (>= 70%) -->
        <div id="alertas" class="tab-content">
            <div class="alerts-intro">
                <span class="alerts-icon">🚨</span>
                <div>
                    <h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.2rem;">Alertas de Over 2.5 Gols (Threshold &ge; 70%)</h3>
                    <p style="color: var(--text-muted); font-size: 0.9rem;">Estas são as partidas da fase de grupos com maior propensão a gols, onde o modelo Poisson estimou mais de 70% de probabilidade de sair 3 ou mais gols no confronto.</p>
                </div>
            </div>
            <div class="timeline-section" id="alertsSection"></div>
        </div>

        <!-- TAB 4: SELEÇÕES -->
        <div id="selecoes" class="tab-content">
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
            
            <div class="legend-panel" style="margin-bottom: 1.5rem; padding: 1rem; border-radius: 12px; background: rgba(255,255,255,0.02); border: 1px solid var(--card-border); font-size: 0.85rem; display: flex; flex-direction: column; gap: 0.5rem;">
                <div style="font-weight: 600; color: var(--accent-secondary); margin-bottom: 0.2rem;">📋 Legenda Disciplinar (Cartões acumulados na Fase de Grupos)</div>
                <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; color: var(--text-muted);">
                    <div style="display: flex; align-items: center; gap: 0.4rem;">
                        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 3px; background: var(--success);"></span>
                        <span><strong>Comportado:</strong> &le; 3 amarelos e 0 vermelhos</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.4rem;">
                        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 3px; background: #f59e0b;"></span>
                        <span><strong>Neutro:</strong> 4 a 6 amarelos e 0 vermelhos</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.4rem;">
                        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 3px; background: var(--danger);"></span>
                        <span><strong>Rebelde:</strong> &ge; 7 amarelos OU &ge; 1 vermelho</span>
                    </div>
                </div>
            </div>
            <div class="teams-grid" id="teamsGrid"></div>
        </div>
        
        <!-- Footer -->
        <footer style="text-align: center; padding: 2rem 0 1rem 0; margin-top: 3rem; border-top: 1px solid var(--card-border); font-size: 0.85rem; color: var(--text-muted);">
            By Felipe Aguia
        </footer>
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
        // Injected payloads
        const dbData = {json.dumps(db_data, ensure_ascii=False)};
        const groupSimulations = {json.dumps(group_simulations, ensure_ascii=False)};
        
        function formatStageName(stage) {{
            if (stage === 'group-stage') return 'Fase de Grupos';
            if (stage === 'round-of-32') return 'Fase de 32 (16avos)';
            if (stage === 'round-of-16') return 'Oitavas de Final';
            if (stage === 'quarter-finals') return 'Quartas de Final';
            if (stage === 'semi-finals') return 'Semifinal';
            if (stage === 'third-place') return 'Disputa de 3º Lugar';
            if (stage === 'final') return 'Final';
            return stage;
        }}
        
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

        // Tab Switching Logic
        function switchTab(evt, tabId) {{
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));
            
            const buttons = document.querySelectorAll('.tab-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            evt.currentTarget.classList.add('active');
        }}

        // Populate simulation select dropdowns
        function populateSelectors() {{
            const sortedNames = Object.keys(dbData).sort();
            
            teamASelect.innerHTML = '';
            teamBSelect.innerHTML = '';
            
            sortedNames.forEach(name => {{
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

        function dixonColesCorrection(x, y, lambdaA, lambdaB, rho = -0.10) {{
            if (x === 0 && y === 0) return Math.max(0.0, 1.0 - lambdaA * lambdaB * rho);
            if (x === 0 && y === 1) return Math.max(0.0, 1.0 + lambdaA * rho);
            if (x === 1 && y === 0) return Math.max(0.0, 1.0 + lambdaB * rho);
            if (x === 1 && y === 1) return Math.max(0.0, 1.0 - rho);
            return 1.0;
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
            
            let hostAdvA = 1.0;
            let hostAdvB = 1.0;
            if (["Mexico", "Canada", "United States"].includes(teamA)) hostAdvA = 1.10;
            if (["Mexico", "Canada", "United States"].includes(teamB)) hostAdvB = 1.10;
            
            const lambdaA = ((statsA.attack_strength * statsB.defense_strength) / avgDefense) * hostAdvA / hostAdvB;
            const lambdaB = ((statsB.attack_strength * statsA.defense_strength) / avgDefense) * hostAdvB / hostAdvA;
            
            let winA = 0, winB = 0, draw = 0;
            let over1_5 = 0, over2_5 = 0, btts = 0;
            let maxProb = -1;
            let bestScore = [0, 0];
            
            for (let x = 0; x < 10; x++) {{
                const probX = poissonProbability(x, lambdaA);
                for (let y = 0; y < 10; y++) {{
                    const probY = poissonProbability(y, lambdaB);
                    const probXY = probX * probY * dixonColesCorrection(x, y, lambdaA, lambdaB);
                    
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
            
            const sumP = winA + winB + draw;
            if (sumP > 0) {{
                winA /= sumP;
                winB /= sumP;
                draw /= sumP;
                over1_5 /= sumP;
                over2_5 /= sumP;
                btts /= sumP;
            }}
            
            const labelA = document.getElementById('labelTeamA');
            const labelB = document.getElementById('labelTeamB');
            labelA.innerText = teamA;
            labelA.onclick = () => openModal(teamA);
            labelB.innerText = teamB;
            labelB.onclick = () => openModal(teamB);
            
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
            
            document.getElementById('predictedScore').innerText = `${{bestScore[0]}} - ${{bestScore[1]}}`;
            document.getElementById('predictedScoreChance').innerText = `Probabilidade: ${{(maxProb * 100).toFixed(1)}}%`;
            document.getElementById('expectedTotalGoals').innerText = (lambdaA + lambdaB).toFixed(2);
            
            document.getElementById('matchupStatValA_1').innerText = lambdaA.toFixed(2) + " xG";
            document.getElementById('matchupStatValB_1').innerText = lambdaB.toFixed(2) + " xG";
            
            // Corners & Shots
            const expCornersA = ((5.0 * (statsA.attack_strength * statsB.defense_strength)) / avgDefense) * hostAdvA / hostAdvB;
            const expCornersB = ((4.5 * (statsB.attack_strength * statsA.defense_strength)) / avgDefense) * hostAdvB / hostAdvA;
            const expShotsA = ((12.5 * (statsA.attack_strength * statsB.defense_strength)) / avgDefense) * hostAdvA / hostAdvB;
            const expShotsB = ((10.5 * (statsB.attack_strength * statsA.defense_strength)) / avgDefense) * hostAdvB / hostAdvA;
            const expSotA = ((4.5 * (statsA.attack_strength * statsB.defense_strength)) / avgDefense) * hostAdvA / hostAdvB;
            const expSotB = ((3.8 * (statsB.attack_strength * statsA.defense_strength)) / avgDefense) * hostAdvB / hostAdvA;
            
            document.getElementById('matchupStatValA_4').innerText = expCornersA.toFixed(1);
            document.getElementById('matchupStatValB_4').innerText = expCornersB.toFixed(1);
            document.getElementById('matchupStatValA_5').innerText = expShotsA.toFixed(1);
            document.getElementById('matchupStatValB_5').innerText = expShotsB.toFixed(1);
            document.getElementById('matchupStatValA_6').innerText = expSotA.toFixed(1);
            document.getElementById('matchupStatValB_6').innerText = expSotB.toFixed(1);
            
            document.getElementById('matchupStatValA_2').innerText = (btts * 100).toFixed(1) + '%';
            document.getElementById('matchupStatValA_15').innerText = (over1_5 * 100).toFixed(1) + '%';
            document.getElementById('matchupStatValA_3').innerText = (over2_5 * 100).toFixed(1) + '%';
            
            simResultsCard.style.display = 'block';
        }}

        compareBtn.addEventListener('click', simulateMatch);

        // Render Group Stage and Alerts timeline dynamically
        function renderGroupStageTimeline(selectedDate) {{
            const timelineSection = document.getElementById('timelineSection');
            const alertsSection = document.getElementById('alertsSection');
            const onlySelectedDay = document.getElementById('onlySelectedDayToggle').checked;
            
            timelineSection.innerHTML = '';
            alertsSection.innerHTML = '';
            
            // Group simulations by date
            const dateGroups = {{}};
            const alertDateGroups = {{}};
            let activeAlertCount = 0;
            
            groupSimulations.forEach(sim => {{
                // Standard timeline
                if (!dateGroups[sim.date]) dateGroups[sim.date] = [];
                dateGroups[sim.date].push(sim);
                
                // Alerts timeline (threshold >= 70%)
                const isCompleted = sim.date < selectedDate || sim.real_home !== null;
                if (sim.is_alert && !isCompleted) {{
                    activeAlertCount++;
                    if (!alertDateGroups[sim.date]) alertDateGroups[sim.date] = [];
                    alertDateGroups[sim.date].push(sim);
                }}
            }});
            
            // Update alerts tab badge
            document.getElementById('alertsBadge').innerText = activeAlertCount;
            
            // 1. Render main timeline
            let datesToRender = Object.keys(dateGroups);
            if (onlySelectedDay) {{
                datesToRender = datesToRender.filter(d => d === selectedDate);
            }}
            
            if (datesToRender.length === 0) {{
                timelineSection.innerHTML = `
                    <div class="timeline-date-group" style="text-align:center; padding: 3rem; color: var(--text-muted);">
                        Nenhuma partida agendada para esta data (${{selectedDate}}).
                    </div>
                `;
            }} else {{
                datesToRender.sort().forEach(date => {{
                    const groupCard = document.createElement('div');
                    groupCard.className = 'timeline-date-group';
                    
                    // Format Date Label
                    const dateObj = new Date(date + 'T00:00:00');
                    const formattedDate = dateObj.toLocaleDateString('pt-BR', {{ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }});
                    const isDayPlayed = date < selectedDate;
                    
                    let matchesHtml = '';
                    dateGroups[date].forEach(match => {{
                        const isMatchPlayed = match.date < selectedDate || match.real_home !== null;
                        let cardClass = 'match-item-card';
                        if (isMatchPlayed) {{
                            cardClass += ' match-played';
                        }} else if (match.prob_over_2_5 >= 0.70) {{
                            cardClass += ' alert-card-glow-over25';
                        }} else if (match.prob_over_1_5 >= 0.85) {{
                            cardClass += ' alert-card-glow-over15';
                        }}
                        
                        let realResultHtml = '';
                        if (match.real_home !== null) {{
                            realResultHtml = `<div class="match-item-real-result">Resultado COPA 2026: <strong>${{match.real_home}} - ${{match.real_away}}</strong></div>`;
                        }} else if (isMatchPlayed) {{
                            realResultHtml = `<div class="match-item-real-result waiting">Resultado COPA 2026: <strong>Pendente</strong></div>`;
                        }} else {{
                            realResultHtml = `<div class="match-item-real-result waiting">Resultado COPA 2026: <strong>- (Agendado)</strong></div>`;
                        }}

                        let kickoffTimeHtml = '';
                        if (match.kickoff) {{
                            try {{
                                const kickoffDate = new Date(match.kickoff);
                                const kickoffTimeStr = kickoffDate.toLocaleTimeString('pt-BR', {{ hour: '2-digit', minute: '2-digit' }});
                                kickoffTimeHtml = ` • 🕒 ${{kickoffTimeStr}}`;
                            }} catch (e) {{
                                console.error("Error parsing kickoff date:", e);
                            }}
                        }}

                        matchesHtml += `
                            <div class="${{cardClass}}">
                                <div class="match-item-header">
                                    <span>Jogo #${{match.match_number}} - ${{match.stage === 'group-stage' ? 'Grupo ' + match.group : formatStageName(match.stage)}}${{kickoffTimeHtml}}</span>
                                    <span style="font-weight:600;">xG: ${{match.exp_g_home.toFixed(2)}} - ${{match.exp_g_away.toFixed(2)}}</span>
                                </div>
                                <div class="match-item-teams">
                                    <span class="clickable-team" onclick="openModal('${{match.home_team}}')">${{match.home_team}}</span>
                                    <span style="color:var(--text-muted); font-size:0.8rem;">vs</span>
                                    <span class="clickable-team" onclick="openModal('${{match.away_team}}')">${{match.away_team}}</span>
                                </div>
                                <div class="match-item-score-prediction">
                                    Placar Provável: <strong>${{match.pred_home}} - ${{match.pred_away}}</strong>
                                </div>
                                <div style="text-align: center; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.4rem;">
                                    🟨 ${{match.yc_home}} - ${{match.yc_away}} 🟨 ${{ (match.rc_home > 0 || match.rc_away > 0) ? ' | 🟥 ' + match.rc_home + ' - ' + match.rc_away + ' 🟥' : '' }}
                                </div>
                                <div style="text-align: center; font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.4rem; display: flex; justify-content: center; gap: 0.8rem; background: rgba(255,255,255,0.02); padding: 0.2rem 0; border-radius: 6px;">
                                    <span>🚩 Escanteios: <strong>${{match.sim_corners_home}} - ${{match.sim_corners_away}}</strong> <span style="font-size:0.65rem; opacity:0.75;">(${{match.exp_corners_home.toFixed(1)}} - ${{match.exp_corners_away.toFixed(1)}})</span></span>
                                    <span>🎯 Finalizações (Alvo): <strong>${{match.sim_shots_home}} (${{match.sim_shots_on_target_home}}) - ${{match.sim_shots_away}} (${{match.sim_shots_on_target_away}})</strong></span>
                                </div>
                                ${{realResultHtml}}

                                <div class="match-item-footer-stats">
                                    <span>V/E/D: ${{Math.round(match.prob_win_home*100)}}%/${{Math.round(match.prob_draw*100)}}%/${{Math.round(match.prob_win_away*100)}}%</span>
                                    <span style="color: ${{match.prob_over_1_5 >= 0.85 ? 'var(--cyan-alert)' : 'var(--text-muted)'}}; font-weight: ${{match.prob_over_1_5 >= 0.85 ? '700' : 'normal'}}">Over 1.5: <strong>${{Math.round(match.prob_over_1_5*100)}}%</strong></span>
                                    <span style="color: var(--text-muted);">|</span>
                                    <span style="color: ${{match.prob_over_2_5 >= 0.70 ? 'var(--pink-alert)' : 'var(--text-muted)'}}; font-weight: ${{match.prob_over_2_5 >= 0.70 ? '700' : 'normal'}}">Over 2.5: <strong>${{Math.round(match.prob_over_2_5*100)}}%</strong></span>
                                </div>
                            </div>
                        `;
                    }});
                    
                    groupCard.innerHTML = `
                        <div class="timeline-date-header" style="${{isDayPlayed ? 'border-color: var(--success); color: var(--success);' : ''}}">${{formattedDate.charAt(0).toUpperCase() + formattedDate.slice(1)}}</div>
                        <div class="match-row-grid">${{matchesHtml}}</div>
                    `;
                    timelineSection.appendChild(groupCard);
                }});
            }}
            
            // 2. Render alerts timeline
            if (activeAlertCount === 0) {{
                alertsSection.innerHTML += `
                    <div class="timeline-date-group" style="text-align:center; padding: 3rem; color: var(--text-muted);">
                        Nenhum alerta ativo de gols (Over 1.5 ou Over 2.5) após a data selecionada.
                    </div>
                `;
            }} else {{
                Object.keys(alertDateGroups).sort().forEach(date => {{
                    const groupCard = document.createElement('div');
                    groupCard.className = 'timeline-date-group';
                    
                    const dateObj = new Date(date + 'T00:00:00');
                    const formattedDate = dateObj.toLocaleDateString('pt-BR', {{ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }});
                    
                    let matchesHtml = '';
                    alertDateGroups[date].forEach(match => {{
                        let kickoffTimeHtml = '';
                        if (match.kickoff) {{
                            try {{
                                const kickoffDate = new Date(match.kickoff);
                                const kickoffTimeStr = kickoffDate.toLocaleTimeString('pt-BR', {{ hour: '2-digit', minute: '2-digit' }});
                                kickoffTimeHtml = ` • 🕒 ${{kickoffTimeStr}}`;
                            }} catch (e) {{
                                console.error("Error parsing kickoff date:", e);
                            }}
                        }}

                        let cardClass = 'match-item-card';
                        let predictionStyle = '';
                        if (match.prob_over_2_5 >= 0.70) {{
                            cardClass += ' alert-card-glow-over25';
                            predictionStyle = 'style="background: rgba(236, 72, 153, 0.08); border-color: rgba(236, 72, 153, 0.25);"';
                        }} else if (match.prob_over_1_5 >= 0.85) {{
                            cardClass += ' alert-card-glow-over15';
                            predictionStyle = 'style="background: rgba(6, 182, 212, 0.08); border-color: rgba(6, 182, 212, 0.25);"';
                        }}

                        matchesHtml += `
                            <div class="${{cardClass}}">
                                <div class="match-item-header">
                                    <span>Jogo #${{match.match_number}} - ${{match.stage === 'group-stage' ? 'Grupo ' + match.group : formatStageName(match.stage)}}${{kickoffTimeHtml}}</span>
                                    <span style="font-weight:600;">xG: ${{match.exp_g_home.toFixed(2)}} - ${{match.exp_g_away.toFixed(2)}}</span>
                                </div>
                                <div class="match-item-teams">
                                    <span class="clickable-team" onclick="openModal('${{match.home_team}}')">${{match.home_team}}</span>
                                    <span style="color:var(--text-muted); font-size:0.8rem;">vs</span>
                                    <span class="clickable-team" onclick="openModal('${{match.away_team}}')">${{match.away_team}}</span>
                                </div>
                                <div class="match-item-score-prediction" ${{predictionStyle}}>
                                    Placar Provável: <strong>${{match.pred_home}} - ${{match.pred_away}}</strong>
                                </div>
                                <div style="text-align: center; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.4rem;">
                                    🟨 ${{match.yc_home}} - ${{match.yc_away}} 🟨 ${{ (match.rc_home > 0 || match.rc_away > 0) ? ' | 🟥 ' + match.rc_home + ' - ' + match.rc_away + ' 🟥' : '' }}
                                </div>
                                <div style="text-align: center; font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.4rem; display: flex; justify-content: center; gap: 0.8rem; background: rgba(255,255,255,0.02); padding: 0.2rem 0; border-radius: 6px;">
                                    <span>🚩 Escanteios: <strong>${{match.sim_corners_home}} - ${{match.sim_corners_away}}</strong> <span style="font-size:0.65rem; opacity:0.75;">(${{match.exp_corners_home.toFixed(1)}} - ${{match.exp_corners_away.toFixed(1)}})</span></span>
                                    <span>🎯 Finalizações (Alvo): <strong>${{match.sim_shots_home}} (${{match.sim_shots_on_target_home}}) - ${{match.sim_shots_away}} (${{match.sim_shots_on_target_away}})</strong></span>
                                </div>
                                </div>

                                <div class="match-item-footer-stats">
                                    <span>V/E/D: ${{Math.round(match.prob_win_home*100)}}%/${{Math.round(match.prob_draw*100)}}%/${{Math.round(match.prob_win_away*100)}}%</span>
                                    <span class="${{match.prob_over_1_5 >= 0.85 ? 'alert-value-highlight-over15' : ''}}">Over 1.5: <strong>${{Math.round(match.prob_over_1_5*100)}}%</strong></span>
                                    <span style="color: var(--text-muted);">|</span>
                                    <span class="${{match.prob_over_2_5 >= 0.70 ? 'alert-value-highlight' : ''}}">Over 2.5: <strong>${{Math.round(match.prob_over_2_5*100)}}%</strong></span>
                                </div>
                            </div>
                        `;
                    }});
                    
                    groupCard.innerHTML = `
                        <div class="timeline-date-header" style="border-color: var(--accent-primary); color: var(--accent-primary);">${{formattedDate.charAt(0).toUpperCase() + formattedDate.slice(1)}}</div>
                        <div class="match-row-grid">${{matchesHtml}}</div>
                    `;
                    alertsSection.appendChild(groupCard);
                }});
            }}
        }}

        // Render team cards
        function renderTeams(filteredTeams) {{
            teamsGrid.innerHTML = '';
            
            filteredTeams.forEach(teamName => {{
                const team = dbData[teamName];
                const sum = team.summary;
                
                let behaviorColor = 'var(--text-muted)';
                let behaviorLabel = sum.card_behavior.charAt(0).toUpperCase() + sum.card_behavior.slice(1);
                if (sum.card_behavior === 'comportado') behaviorColor = 'var(--success)';
                else if (sum.card_behavior === 'neutro') behaviorColor = '#f59e0b';
                else if (sum.card_behavior === 'rebelde') behaviorColor = 'var(--danger)';
                
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
                        <span class="stat-label">Ataque / Defesa</span>
                        <span class="stat-value"><span style="color: var(--success);">${{sum.attack_strength.toFixed(2)}}</span> / <span style="color: var(--danger);">${{sum.defense_strength.toFixed(2)}}</span></span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Cartões (🟨 / 🟥)</span>
                        <span class="stat-value" style="color: #fff;">🟨 ${{sum.yellow_cards}} / 🟥 ${{sum.red_cards}}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Conduta Disciplinar</span>
                        <span class="stat-value" style="color: ${{behaviorColor}}; font-weight: 600;">${{behaviorLabel}}</span>
                    </div>
                    <div class="stat-row" style="margin-top: 0.4rem; border-top: 1px dashed rgba(255,255,255,0.08); padding-top: 0.4rem;">
                        <span class="stat-label">Status Copa 2026</span>
                        <span class="stat-value" style="color: ${{sum.gas_desc_next_match === 'Campeão' ? 'var(--success)' : (sum.gas_desc_next_match.startsWith('Eliminado') ? 'var(--text-muted)' : 'var(--accent-secondary)')}}; font-weight: 600;">${{sum.gas_desc_next_match}}</span>
                    </div>
                    <div class="stat-row" style="margin-top: 0.4rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.4rem;">
                        <span class="stat-label">V / E / D (Pond.)</span>
                        <span class="stat-value">${{ (sum.weighted_win_rate*100).toFixed(0) }}% / ${{ ((sum.weighted_draw_rate)*100).toFixed(0) }}% / ${{ ((sum.weighted_loss_rate)*100).toFixed(0) }}%</span>
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
            if (!dbData[teamName]) {{
                console.warn("Team not found in dbData:", teamName);
                return;
            }}
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
                
                const opponentName = m.opponent;
                const isOpponentClickable = dbData[opponentName] ? 'class="clickable-team" onclick="openModal(\\\'' + opponentName + '\\\')"' : '';
                
                row.innerHTML = `
                    <td>${{m.date}}</td>
                    <td><span class="result-badge ${{m.result.toLowerCase()}}">${{m.result}}</span></td>
                    <td style="font-weight: 600;">${{scoreStr}}</td>
                    <td style="font-weight: 500;" ${{isOpponentClickable}}>${{opponentName}}</td>
                    <td>${{m.competition}}</td>
                    <td>${{m.opp_elo}}</td>
                    <td>#${{m.opp_fifa_rank}}</td>
                    <td>${{m.weight.toFixed(2)}}</td>
                `;
                matchesTableBody.appendChild(row);
            }});
            
            document.body.style.overflow = 'hidden';
            modalOverlay.classList.add('active');
        }}

        function closeModal() {{
            document.body.style.overflow = '';
            modalOverlay.classList.remove('active');
        }}

        closeBtn.addEventListener('click', closeModal);
        modalOverlay.addEventListener('click', (e) => {{
            if (e.target === modalOverlay) closeModal();
        }});

        // Setup Time Control Panel
        const dateInput = document.getElementById('copaDateInput');
        const prevBtn = document.getElementById('prevDayBtn');
        const nextBtn = document.getElementById('nextDayBtn');
        const statusText = document.getElementById('timeControlStatus');

        function updateStatusText(dateStr) {{
            const dateObj = new Date(dateStr + 'T00:00:00');
            const options = {{ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }};
            const formatted = dateObj.toLocaleDateString('pt-BR', options);
            statusText.textContent = `Tempo: ${{formatted.charAt(0).toUpperCase() + formatted.slice(1)}}`;
        }}

        function changeDate(dateStr) {{
            updateStatusText(dateStr);
            renderGroupStageTimeline(dateStr);
        }}

        dateInput.addEventListener('change', (e) => {{
            changeDate(e.target.value);
        }});

        prevBtn.addEventListener('click', () => {{
            const current = new Date(dateInput.value + 'T00:00:00');
            current.setDate(current.getDate() - 1);
            const yyyy = current.getFullYear();
            const mm = String(current.getMonth() + 1).padStart(2, '0');
            const dd = String(current.getDate()).padStart(2, '0');
            const newDate = `${{yyyy}}-${{mm}}-${{dd}}`;
            if (newDate >= dateInput.min) {{
                dateInput.value = newDate;
                changeDate(newDate);
            }}
        }});

        nextBtn.addEventListener('click', () => {{
            const current = new Date(dateInput.value + 'T00:00:00');
            current.setDate(current.getDate() + 1);
            const yyyy = current.getFullYear();
            const mm = String(current.getMonth() + 1).padStart(2, '0');
            const dd = String(current.getDate()).padStart(2, '0');
            const newDate = `${{yyyy}}-${{mm}}-${{dd}}`;
            if (newDate <= dateInput.max) {{
                dateInput.value = newDate;
                changeDate(newDate);
            }}
        }});

        // Setup toggle event listener
        const dayToggle = document.getElementById('onlySelectedDayToggle');
        dayToggle.addEventListener('change', () => {{
            renderGroupStageTimeline(dateInput.value);
        }});
        
        document.getElementById('toggleLabel').addEventListener('click', () => {{
            dayToggle.checked = !dayToggle.checked;
            renderGroupStageTimeline(dateInput.value);
        }});

        // Initialize selectors and view
        populateSelectors();
        
        // Initialize to today's date if within tournament range, otherwise default to first/last day
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        const todayStr = `${{yyyy}}-${{mm}}-${{dd}}`;
        
        let initialDate = "2026-06-15";
        if (todayStr >= dateInput.min && todayStr <= dateInput.max) {{
            initialDate = todayStr;
        }} else if (todayStr < dateInput.min) {{
            initialDate = dateInput.min;
        }} else {{
            initialDate = dateInput.max;
        }}
        
        dateInput.value = initialDate;
        changeDate(initialDate);
        
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
