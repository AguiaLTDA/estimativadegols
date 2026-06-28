import csv
import json
import sqlite3
import os
import re
import math
from datetime import datetime
import random

# Poisson probability helper
def poisson_probability(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam**k * math.exp(-lam)) / math.factorial(k)

# 1. Normalization function for team names
def normalize_name(name):
    if not name:
        return ""
    name = name.strip()
    
    # Common name mapping dictionary
    replacements = {
        "US Virgin Islands": "U.S. Virgin Islands",
        "Trkiye": "Turkey",
        "Türkiye": "Turkey",
        "Turkiye": "Turkey",
        "Cte d'Ivoire": "Ivory Coast",
        "Côte d'Ivoire": "Ivory Coast",
        "Cote d'Ivoire": "Ivory Coast",
        "Congo DR": "DR Congo",
        "Congo Republic": "Congo",
        "IR Iran": "Iran",
        "Korea Republic": "South Korea",
        "Korea DPR": "North Korea",
        "Cabo Verde": "Cape Verde",
        "Curacao": "Curaçao",
        "Curaao": "Curaçao",
        "Bosnia-Herzegovina": "Bosnia and Herzegovina",
        "Czechia": "Czech Republic",
        "USA": "United States"
    }
    return replacements.get(name, name)

# 2. Get K-factor based on tournament type
def get_k_factor(tournament):
    t_lower = tournament.lower()
    if tournament == "FIFA World Cup":
        return 60
    elif any(term in t_lower for term in ["uefa euro", "copa américa", "copa america", "afc asian cup", "african cup of nations", "gold cup", "confederations cup"]):
        return 50
    elif "qualification" in t_lower or "qualifying" in t_lower:
        return 40
    elif tournament == "Friendly":
        return 20
    else:
        return 30

# 3. Load FIFA rankings
def load_fifa_rankings(filename):
    rankings = {}
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team_norm = normalize_name(row['team'])
            rankings[team_norm] = int(row['rank'])
    return rankings

# 4. Approximate FIFA rank based on Elo if missing
def get_approx_fifa_rank(elo_val):
    if elo_val > 1850:
        return 5
    elif elo_val > 1750:
        return 15
    elif elo_val > 1650:
        return 30
    elif elo_val > 1550:
        return 50
    elif elo_val > 1450:
        return 80
    elif elo_val > 1350:
        return 110
    elif elo_val > 1250:
        return 140
    elif elo_val > 1150:
        return 170
    else:
        return 200

# 5. Get FIFA Rank for a team at a specific date
def get_fifa_rank(team, date_str, fifa_2022, fifa_2026, elo_val):
    team_norm = normalize_name(team)
    if date_str <= "2024-06-30":
        rank = fifa_2022.get(team_norm)
    else:
        rank = fifa_2026.get(team_norm)
        
    if rank is not None:
        return rank
    return get_approx_fifa_rank(elo_val)

def get_team_state_before_match(team, match_num, fixtures_list, real_results):
    played_count = 0
    points = 0
    goals_for = 0
    goals_against = 0
    wins = 0
    draws = 0
    losses = 0
    
    for f in fixtures_list:
        if f['stage'] != 'group-stage':
            continue
        m_id = int(f['match_number'])
        if m_id < match_num:
            home = normalize_name(f['home_team'])
            away = normalize_name(f['away_team'])
            if home == team or away == team:
                if m_id in real_results:
                    played_count += 1
                    res = real_results[m_id]
                    is_home = (home == team)
                    t_goals = res['home_score'] if is_home else res['away_score']
                    o_goals = res['away_score'] if is_home else res['home_score']
                    
                    goals_for += t_goals
                    goals_against += o_goals
                    
                    if t_goals > o_goals:
                        points += 3
                        wins += 1
                    elif t_goals == o_goals:
                        points += 1
                        draws += 1
                    else:
                        losses += 1
                        
    return {
        "played": played_count,
        "points": points,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goals_diff": goals_for - goals_against,
        "wins": wins,
        "draws": draws,
        "losses": losses
    }

def calculate_gas_for_team(team_state, group_teams_states):
    played = team_state["played"]
    points = team_state["points"]
    
    if played == 0:
        return 0.50, "Estreia no grupo"
    elif played == 1:
        if points == 0:
            return 0.85, "precisa vencer, risco de eliminação"
        elif points == 1:
            return 0.75, "precisa se posicionar no grupo"
        else:
            return 0.60, "busca confirmar a classificação"
    else: # played == 2 (rodada decisiva)
        if points >= 6:
            return 0.40, "classificado, busca liderança"
        elif points == 4:
            return 0.70, "precisa se posicionar no grupo"
        elif points == 3:
            return 0.85, "precisa fazer gols para classificar"
        elif points == 2:
            return 0.90, "precisa vencer e de saldo"
        elif points == 1:
            return 0.95, "jogo de vida ou morte, precisa vencer"
        else: # points == 0
            # Verificação de eliminação matemática do top 3 do grupo
            sorted_group_points = sorted([ts["points"] for ts in group_teams_states], reverse=True)
            if len(sorted_group_points) >= 3 and sorted_group_points[2] >= 4:
                return 0.20, "eliminado, cumprir tabela"
            else:
                return 0.80, "chance remota, precisa golear"

import hashlib
import functools

def get_deterministic_cards(home_team, away_team, match_num):
    seed_str = f"cards_wc_2026_{match_num}_{home_team}_{away_team}"
    seed_val = int(hashlib.md5(seed_str.encode('utf-8')).hexdigest(), 16) % 10000000
    rng = random.Random(seed_val)
    
    # Yellow cards probabilities: 0 (15%), 1 (30%), 2 (30%), 3 (15%), 4 (8%), 5 (2%)
    yc_probs = [0, 1, 1, 2, 2, 2, 3, 3, 4, 5]
    home_yc = rng.choice(yc_probs)
    away_yc = rng.choice(yc_probs)
    
    # Red cards: 0 (95%), 1 (5%)
    rc_probs = [0] * 19 + [1]
    home_rc = rng.choice(rc_probs)
    away_rc = rng.choice(rc_probs)
    
    return home_yc, away_yc, home_rc, away_rc

def allocate_third_places(best_thirds):
    slots = [
        {"matchNumber": 74, "allowedGroups": ['A', 'B', 'C', 'D', 'F'], "opponentGroup": 'E'},
        {"matchNumber": 77, "allowedGroups": ['C', 'D', 'F', 'G', 'H'], "opponentGroup": 'I'},
        {"matchNumber": 79, "allowedGroups": ['C', 'E', 'F', 'H', 'I'], "opponentGroup": 'A'},
        {"matchNumber": 80, "allowedGroups": ['E', 'H', 'I', 'J', 'K'], "opponentGroup": 'L'},
        {"matchNumber": 81, "allowedGroups": ['B', 'E', 'F', 'I', 'J'], "opponentGroup": 'D'},
        {"matchNumber": 82, "allowedGroups": ['A', 'E', 'H', 'I', 'J'], "opponentGroup": 'G'},
        {"matchNumber": 85, "allowedGroups": ['E', 'F', 'G', 'I', 'J'], "opponentGroup": 'B'},
        {"matchNumber": 87, "allowedGroups": ['D', 'E', 'I', 'J', 'L'], "opponentGroup": 'K'}
    ]
    assignment = {}
    used_thirds = set()
    
    def backtrack(slot_idx):
        if slot_idx == len(slots):
            return True
        slot = slots[slot_idx]
        
        # Try strict: third.group != opponentGroup
        for i, third in enumerate(best_thirds):
            if i in used_thirds:
                continue
            if third["group"] in slot["allowedGroups"] and third["group"] != slot["opponentGroup"]:
                assignment[slot["matchNumber"]] = third["team"]
                used_thirds.add(i)
                if backtrack(slot_idx + 1):
                    return True
                used_thirds.remove(i)
                if slot["matchNumber"] in assignment:
                    del assignment[slot["matchNumber"]]
                    
        # Try relaxed: allow opponentGroup == third.group if strict fails
        for i, third in enumerate(best_thirds):
            if i in used_thirds:
                continue
            if third["group"] in slot["allowedGroups"]:
                assignment[slot["matchNumber"]] = third["team"]
                used_thirds.add(i)
                if backtrack(slot_idx + 1):
                    return True
                used_thirds.remove(i)
                if slot["matchNumber"] in assignment:
                    del assignment[slot["matchNumber"]]
        return False

    if backtrack(0):
        return assignment
    else:
        # Fallback
        fallback = {}
        for idx, slot in enumerate(slots):
            if idx < len(best_thirds):
                fallback[slot["matchNumber"]] = best_thirds[idx]["team"]
        return fallback

def compare_teams(a, b):
    # 1. Points (higher is better)
    if b["points"] != a["points"]:
        return b["points"] - a["points"]
    # 2. Goal Difference (higher is better)
    if b["goalDifference"] != a["goalDifference"]:
        return b["goalDifference"] - a["goalDifference"]
    # 3. Goals Scored (higher is better)
    if b["goalsFor"] != a["goalsFor"]:
        return b["goalsFor"] - a["goalsFor"]
    # 4. H2H points (higher is better)
    a_h2h = a["headToHead"].get(b["team"], 0)
    b_h2h = b["headToHead"].get(a["team"], 0)
    if b_h2h != a_h2h:
        return b_h2h - a_h2h
    # 5. FIFA Rank (lower rank number is better)
    return a["fifa_rank"] - b["fifa_rank"]

def get_group_standings(group_simulations, consolidated_data, fixtures_list):
    standings = {}
    
    # Initialize standings for all 48 teams
    for team_data in consolidated_data:
        team_name = team_data["team"]
        standings[team_name] = {
            "team": team_name,
            "fifa_rank": team_data["fifa_rank"],
            "elo": team_data["elo"],
            "played": 0,
            "points": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goalsFor": 0,
            "goalsAgainst": 0,
            "goalDifference": 0,
            "headToHead": {}
        }
        
    for sim in group_simulations:
        home = sim["home_team"]
        away = sim["away_team"]
        
        # Determine score
        h_score = sim["real_score_home"]
        a_score = sim["real_score_away"]
        if h_score is None:
            h_score = sim["predicted_score_home"]
            a_score = sim["predicted_score_away"]
            
        if home not in standings or away not in standings:
            continue
            
        standings[home]["played"] += 1
        standings[away]["played"] += 1
        standings[home]["goalsFor"] += h_score
        standings[home]["goalsAgainst"] += a_score
        standings[away]["goalsFor"] += a_score
        standings[away]["goalsAgainst"] += h_score
        
        if h_score > a_score:
            standings[home]["points"] += 3
            standings[home]["wins"] += 1
            standings[away]["losses"] += 1
            standings[home]["headToHead"][away] = standings[home]["headToHead"].get(away, 0) + 3
            standings[away]["headToHead"][home] = standings[away]["headToHead"].get(home, 0) + 0
        elif h_score < a_score:
            standings[away]["points"] += 3
            standings[away]["wins"] += 1
            standings[home]["losses"] += 1
            standings[away]["headToHead"][home] = standings[away]["headToHead"].get(home, 0) + 3
            standings[home]["headToHead"][away] = standings[home]["headToHead"].get(away, 0) + 0
        else:
            standings[home]["points"] += 1
            standings[away]["points"] += 1
            standings[home]["draws"] += 1
            standings[away]["draws"] += 1
            standings[home]["headToHead"][away] = standings[home]["headToHead"].get(away, 0) + 1
            standings[away]["headToHead"][home] = standings[away]["headToHead"].get(home, 0) + 1
            
    for team in standings:
        standings[team]["goalDifference"] = standings[team]["goalsFor"] - standings[team]["goalsAgainst"]
        
    groups = {}
    for f in fixtures_list:
        if f["stage"] == "group-stage":
            g = f["group"]
            if g not in groups:
                groups[g] = set()
            groups[g].add(normalize_name(f["home_team"]))
            groups[g].add(normalize_name(f["away_team"]))
            
    group_standings = {}
    for g, team_set in groups.items():
        team_list = [standings[t] for t in team_set if t in standings]
        team_list.sort(key=functools.cmp_to_key(compare_teams))
        group_standings[g] = team_list
        
    return group_standings

def get_best_third_placed_teams(group_standings):
    thirds = []
    for g, list_teams in group_standings.items():
        if len(list_teams) >= 3:
            thirds.append({
                "group": g,
                "team": list_teams[2]["team"],
                "points": list_teams[2]["points"],
                "goalDifference": list_teams[2]["goalDifference"],
                "goalsFor": list_teams[2]["goalsFor"],
                "wins": list_teams[2]["wins"],
                "fifa_rank": list_teams[2]["fifa_rank"]
            })
            
    def compare_thirds(a, b):
        if b["points"] != a["points"]:
            return b["points"] - a["points"]
        if b["goalDifference"] != a["goalDifference"]:
            return b["goalDifference"] - a["goalDifference"]
        if b["goalsFor"] != a["goalsFor"]:
            return b["goalsFor"] - a["goalsFor"]
        if b["wins"] != a["wins"]:
            return b["wins"] - a["wins"]
        return a["fifa_rank"] - b["fifa_rank"]
        
    thirds.sort(key=functools.cmp_to_key(compare_thirds))
    return thirds[:8]

def resolve_r32_teams(match_num, group_standings, best_thirds_allocation):
    def get_winner(g):
        return group_standings.get(g, [None])[0]["team"] if group_standings.get(g) else f"1º Grupo {g}"
    def get_runner(g):
        return group_standings.get(g, [None, None])[1]["team"] if len(group_standings.get(g, [])) >= 2 else f"2º Grupo {g}"
        
    if match_num == 73:
        return get_runner('A'), get_runner('B')
    elif match_num == 74:
        return get_winner('E'), best_thirds_allocation.get(74, '3º A/B/C/D/F')
    elif match_num == 75:
        return get_winner('F'), get_runner('C')
    elif match_num == 76:
        return get_winner('C'), get_runner('F')
    elif match_num == 77:
        return get_winner('I'), best_thirds_allocation.get(77, '3º C/D/F/G/H')
    elif match_num == 78:
        return get_runner('E'), get_runner('I')
    elif match_num == 79:
        return get_winner('A'), best_thirds_allocation.get(79, '3º C/E/F/H/I')
    elif match_num == 80:
        return get_winner('L'), best_thirds_allocation.get(80, '3º E/H/I/J/K')
    elif match_num == 81:
        return get_winner('D'), best_thirds_allocation.get(81, '3º B/E/F/I/J')
    elif match_num == 82:
        return get_winner('G'), best_thirds_allocation.get(82, '3º A/E/H/I/J')
    elif match_num == 83:
        return get_runner('K'), get_runner('L')
    elif match_num == 84:
        return get_winner('H'), get_runner('J')
    elif match_num == 85:
        return get_winner('B'), best_thirds_allocation.get(85, '3º E/F/G/I/J')
    elif match_num == 86:
        return get_winner('J'), get_runner('H')
    elif match_num == 87:
        return get_winner('K'), best_thirds_allocation.get(87, '3º D/E/I/J/L')
    elif match_num == 88:
        return get_runner('D'), get_runner('G')
    return None, None

def resolve_team_placeholder(team_text, match_results_resolved):
    m_winner = re.match(r'Winner Match (\d+)', team_text, re.IGNORECASE)
    if m_winner:
        parent_num = int(m_winner.group(1))
        return match_results_resolved.get(parent_num, {}).get("winner", f"Vencedor Jogo {parent_num}")
        
    m_loser = re.match(r'Loser Match (\d+)', team_text, re.IGNORECASE)
    if m_loser:
        parent_num = int(m_loser.group(1))
        return match_results_resolved.get(parent_num, {}).get("loser", f"Perdedor Jogo {parent_num}")
        
    return team_text

def get_elimination_status(team, qualified_set, match_results_resolved):
    if team not in qualified_set:
        return "Eliminado na Fase de Grupos"
    
    if 104 in match_results_resolved:
        res104 = match_results_resolved[104]
        if res104["winner"] == team:
            return "Campeão"
        if res104["loser"] == team:
            return "Vice-campeão"
            
    if 103 in match_results_resolved:
        res103 = match_results_resolved[103]
        if res103["winner"] == team:
            return "3º Colocado"
        if res103["loser"] == team:
            return "4º Colocado"
            
    for m in [97, 98, 99, 100]:
        if m in match_results_resolved and match_results_resolved[m]["loser"] == team:
            return "Eliminado nas Quartas"
    for m in range(89, 97):
        if m in match_results_resolved and match_results_resolved[m]["loser"] == team:
            return "Eliminado nas Oitavas"
    for m in range(73, 89):
        if m in match_results_resolved and match_results_resolved[m]["loser"] == team:
            return "Eliminado nos 16 avos (R32)"
            
    return "Classificado para próxima fase"

def main():
    print("Starting data pipeline execution...")
    
    # Load qualified teams list
    if not os.path.exists("teams.json"):
        print("Error: teams.json not found. Run extract_qualified_teams.py first.")
        return
        
    with open("teams.json", "r", encoding="utf-8") as f:
        qualified_teams = set(json.load(f))
    print(f"Loaded {len(qualified_teams)} qualified teams.")

    # Load FIFA rankings snapshots
    fifa_2022 = load_fifa_rankings("fifa_ranking_2022-10-06.csv")
    fifa_2026 = load_fifa_rankings("fifa_ranking_2026.csv")
    print(f"Loaded FIFA Rankings: {len(fifa_2022)} teams for 2022, {len(fifa_2026)} teams for 2026.")

    # Try downloading the latest results.csv from GitHub
    results_url = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    print(f"Downloading latest results.csv from {results_url}...")
    try:
        import urllib.request
        import ssl
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(results_url, headers=headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            with open("results.csv", "wb") as f:
                f.write(response.read())
        print("Downloaded latest results.csv successfully.")
    except Exception as e:
        print(f"Could not download latest results.csv (using local file instead): {e}")

    # Load results.csv matches
    if not os.path.exists("results.csv"):
        print("Error: results.csv not found.")
        return
        
    all_matches = []
    with open("results.csv", "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_matches.append(row)
            
    # Sort matches chronologically
    all_matches.sort(key=lambda x: x['date'])
    print(f"Loaded {len(all_matches)} total historical matches.")

    # Load manual overrides/results from JSON for Elo calculation
    manual_results = {}
    real_results_json = "copa_2026_real_results.json"
    if os.path.exists(real_results_json):
        try:
            with open(real_results_json, "r", encoding="utf-8") as f:
                custom_res = json.load(f)
                for m_num_str, scores in custom_res.items():
                    m_num = int(m_num_str)
                    manual_results[m_num] = {
                        "home_score": int(scores["home_score"]),
                        "away_score": int(scores["away_score"])
                    }
            print(f"Loaded {len(manual_results)} manual real results for Elo integration.")
        except Exception as e:
            print(f"Error loading custom real results from JSON: {e}")

    # Map matchups from fixtures to match numbers for manual lookup
    fixture_lookup = {}
    fixtures_list = []
    group_teams_map = {}
    if os.path.exists("fixtures.csv"):
        with open("fixtures.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fixtures_list.append(row)
                if row['stage'] == 'group-stage':
                    h_norm = normalize_name(row['home_team'])
                    a_norm = normalize_name(row['away_team'])
                    m_num = int(row['match_number'])
                    fixture_lookup[(h_norm, a_norm)] = m_num
                    
                    g_name = row['group']
                    if g_name not in group_teams_map:
                        group_teams_map[g_name] = set()
                    group_teams_map[g_name].add(h_norm)
                    group_teams_map[g_name].add(a_norm)

    # Initialize Elo ratings
    elo = {} # team -> Elo rating
    
    processed_matches = []
    
    # Chronological simulation
    for idx, match in enumerate(all_matches):
        date_str = match['date']
        
        home = normalize_name(match['home_team'])
        away = normalize_name(match['away_team'])
        
        # Check if this is a Copa 2026 match and if we have a manual result for it
        h_score_val = match['home_score']
        a_score_val = match['away_score']
        
        if match['tournament'] == 'FIFA World Cup' and date_str >= '2026-06-11':
            if (home, away) in fixture_lookup:
                m_num = fixture_lookup[(home, away)]
                if m_num in manual_results:
                    h_score_val = str(manual_results[m_num]["home_score"])
                    a_score_val = str(manual_results[m_num]["away_score"])
                    
        # Skip matches without score
        if not h_score_val or h_score_val == 'NA':
            continue
        if not a_score_val or a_score_val == 'NA':
            continue
            
        home_score = int(h_score_val)
        away_score = int(a_score_val)
        
        # Initialize Elo if not present
        if home not in elo:
            elo[home] = 1500.0
        if away not in elo:
            elo[away] = 1500.0
            
        r_home_before = elo[home]
        r_away_before = elo[away]
        
        # Home advantage (100 points if not neutral)
        neutral = match['neutral'].upper() == 'TRUE'
        h_adv = 0.0 if neutral else 100.0
        
        # Win expectancy (expected score)
        dr = r_home_before - r_away_before + h_adv
        e_home = 1.0 / (10.0 ** (-dr / 400.0) + 1.0)
        e_away = 1.0 - e_home
        
        # Actual result
        if home_score > away_score:
            s_home, s_away = 1.0, 0.0
        elif home_score < away_score:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5
            
        # Goal difference multiplier
        gd = abs(home_score - away_score)
        gdm = 1.0
        if gd == 2:
            gdm = 1.5
        elif gd == 3:
            gdm = 1.75
        elif gd >= 4:
            gdm = 1.75 + (gd - 3) / 8.0
            
        # K factor
        k = get_k_factor(match['tournament'])
        
        # Update ratings
        change = k * gdm * (s_home - e_home)
        elo[home] += change
        elo[away] -= change
        
        # Get FIFA Ranks at the time of the match
        rank_home = get_fifa_rank(home, date_str, fifa_2022, fifa_2026, r_home_before)
        rank_away = get_fifa_rank(away, date_str, fifa_2022, fifa_2026, r_away_before)
        
        # Store processed match info
        processed_matches.append({
            'date': date_str,
            'home_team': home,
            'away_team': away,
            'home_score': home_score,
            'away_score': away_score,
            'tournament': match['tournament'],
            'neutral': neutral,
            'home_elo_before': r_home_before,
            'away_elo_before': r_away_before,
            'home_fifa_rank': rank_home,
            'away_fifa_rank': rank_away,
            'expected_home': e_home,
            'expected_away': e_away
        })

    print("Elo simulation completed.")
    
    # 6. Extract last 20 matches for each of the 48 teams
    consolidated_data = []
    
    # Setup database connection
    db_file = "world_cup_2026.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE teams_summary (
        team TEXT PRIMARY KEY,
        fifa_rank INTEGER,
        elo INTEGER,
        form_index REAL,
        attack_strength REAL,
        defense_strength REAL,
        weighted_win_rate REAL,
        weighted_draw_rate REAL,
        weighted_loss_rate REAL,
        opponent_strength REAL,
        weighted_goals_scored REAL,
        weighted_goals_conceded REAL,
        gas_next_match REAL,
        gas_desc_next_match TEXT,
        yellow_cards INTEGER,
        red_cards INTEGER,
        card_behavior TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE group_stage_simulations (
        match_number INTEGER PRIMARY KEY,
        match_date TEXT,
        group_name TEXT,
        stage TEXT,
        home_team TEXT,
        away_team TEXT,
        expected_goals_home REAL,
        expected_goals_away REAL,
        prob_win_home REAL,
        prob_draw REAL,
        prob_win_away REAL,
        prob_over_1_5 REAL,
        prob_over_2_5 REAL,
        prob_btts REAL,
        predicted_score_home INTEGER,
        predicted_score_away INTEGER,
        is_over_1_5_alert INTEGER,
        is_over_2_5_alert INTEGER,
        real_goals_home INTEGER,
        real_goals_away INTEGER,
        kickoff_utc TEXT,
        gas_home REAL,
        gas_away REAL,
        gas_desc_home TEXT,
        gas_desc_away TEXT,
        is_gas_alert INTEGER,
        yc_home INTEGER,
        yc_away INTEGER,
        rc_home INTEGER,
        rc_away INTEGER
    )
    """)
    
    cursor.execute("""
    CREATE TABLE team_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team TEXT,
        match_date TEXT,
        opponent TEXT,
        competition TEXT,
        goals_scored INTEGER,
        goals_conceded INTEGER,
        result TEXT,
        opponent_fifa_rank INTEGER,
        opponent_elo REAL,
        weight REAL
    )
    """)
    
    # Load market values
    market_values = {}
    if os.path.exists("market_values.json"):
        try:
            with open("market_values.json", "r", encoding="utf-8") as f:
                market_values = json.load(f)
            print(f"Loaded {len(market_values)} team market values.")
        except Exception as e:
            print(f"Error loading market_values.json: {e}")
            
    # Compute average market value for baseline
    if market_values:
        avg_market_value = sum(market_values.values()) / len(market_values)
    else:
        avg_market_value = 1.0
    print(f"Average team market value: {avg_market_value:.2f}M €")
    
    # Process each qualified team
    for team in sorted(qualified_teams):
        # Filter matches where this team played
        team_matches = []
        for m in processed_matches:
            if m['home_team'] == team or m['away_team'] == team:
                team_matches.append(m)
                
        # Sort by date ascending to get recent ones at the end
        team_matches.sort(key=lambda x: x['date'])
        
        # Take the last 40 matches
        N = len(team_matches)
        if N > 40:
            team_matches = team_matches[-40:]
            N = len(team_matches)
            
        if N == 0:
            print(f"Warning: No matches found for {team} before June 14, 2026!")
            continue
            
        # Compute weights based on time-decay and tournament significance
        weights = []
        ref_date = datetime(2026, 6, 11)
        for m in team_matches:
            try:
                m_date = datetime.strptime(m['date'], "%Y-%m-%d")
                days_ago = (ref_date - m_date).days
                if days_ago < 0:
                    days_ago = 0
            except Exception:
                days_ago = 547
                
            # Time-decay: half-life of 1.5 years (547 days)
            time_decay = 0.5 ** (days_ago / 547.0)
            
            # Tournament significance
            tourney = m['tournament'].lower()
            if 'fifa world cup' in tourney:
                tourney_weight = 2.0
            elif any(x in tourney for x in ['copa américa', 'copa america', 'uefa european championship', 'conmebol', 'uefa', 'qualifiers', 'qualification']):
                tourney_weight = 1.5
            elif 'friendly' in tourney:
                tourney_weight = 0.5
            else:
                tourney_weight = 1.0
                
            weights.append(time_decay * tourney_weight)
            
        sum_weights = sum(weights)
        
        # Aggregate variables
        w_wins = 0.0
        w_draws = 0.0
        w_losses = 0.0
        w_goals_scored = 0.0
        w_goals_conceded = 0.0
        w_clean_sheets = 0.0
        w_btts = 0.0
        w_over_2_5 = 0.0
        w_opponent_elo = 0.0
        w_form_points = 0.0
        
        # Iterate over matches and apply weights
        for idx, m in enumerate(team_matches):
            w = weights[idx]
            is_home = m['home_team'] == team
            
            # Identify goals and opponent
            if is_home:
                g_scored = m['home_score']
                g_conceded = m['away_score']
                opp = m['away_team']
                opp_elo = m['away_elo_before']
                opp_rank = m['away_fifa_rank']
                expected_score = m['expected_home']
            else:
                g_scored = m['away_score']
                g_conceded = m['home_score']
                opp = m['home_team']
                opp_elo = m['home_elo_before']
                opp_rank = m['home_fifa_rank']
                expected_score = m['expected_away']
                
            # Result and actual score
            if g_scored > g_conceded:
                result_char = 'W'
                s_val = 1.0
                w_wins += w
            elif g_scored < g_conceded:
                result_char = 'L'
                s_val = 0.0
                w_losses += w
            else:
                result_char = 'D'
                s_val = 0.5
                w_draws += w
                
            w_goals_scored += w * g_scored
            w_goals_conceded += w * g_conceded
            
            if g_conceded == 0:
                w_clean_sheets += w
                
            if g_scored > 0 and g_conceded > 0:
                w_btts += w
                
            if g_scored + g_conceded > 2:
                w_over_2_5 += w
                
            w_opponent_elo += w * opp_elo
            
            # Recent form points: 50 + 50 * (S - E)
            perf_score = 50.0 + 50.0 * (s_val - expected_score)
            w_form_points += w * perf_score
            
            # Save individual match to SQLite
            cursor.execute("""
            INSERT INTO team_matches (team, match_date, opponent, competition, goals_scored, goals_conceded, result, opponent_fifa_rank, opponent_elo, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (team, m['date'], opp, m['tournament'], g_scored, g_conceded, result_char, opp_rank, opp_elo, w))
            
        # Final weighted averages
        avg_win_rate = w_wins / sum_weights
        avg_draw_rate = w_draws / sum_weights
        avg_loss_rate = w_losses / sum_weights
        avg_goals_scored = w_goals_scored / sum_weights
        avg_goals_conceded = w_goals_conceded / sum_weights
        avg_opp_elo = w_opponent_elo / sum_weights
        avg_form_index = w_form_points / sum_weights
        
        # Baseline Elo for adjusting strengths (we set it to 1600 as competitive baseline)
        baseline_elo = 1600.0
        opp_factor = avg_opp_elo / baseline_elo
        
        # Opponent adjusted strengths
        # If opponents are stronger, attack strength is amplified and defense strength is minimized (improved)
        attack_strength = avg_goals_scored * opp_factor
        defense_strength = avg_goals_conceded / opp_factor
        
        # Market value adjustment (compressed with power of 0.12)
        team_value = market_values.get(team, 50.0) # default to 50M if team is missing
        market_factor = team_value / avg_market_value
        market_adj = market_factor ** 0.12
        
        # Adjust values to reward high market values and adjust lower ones
        attack_strength = attack_strength * market_adj
        defense_strength = defense_strength / market_adj
        
        # Get team's current status (as of June 14, 2026)
        current_elo = elo.get(team, 1500.0)
        current_fifa = fifa_2026.get(team, get_approx_fifa_rank(current_elo))
        
        # Prepare record
        record = {
            "team": team,
            "fifa_rank": current_fifa,
            "elo": int(round(current_elo)),
            "form_index": round(avg_form_index, 1),
            "attack_strength": round(attack_strength, 2),
            "defense_strength": round(defense_strength, 2),
            "weighted_win_rate": round(avg_win_rate, 2),
            "weighted_draw_rate": round(avg_draw_rate, 2),
            "weighted_loss_rate": round(avg_loss_rate, 2),
            "opponent_strength": int(round(avg_opp_elo)),
            "weighted_goals_scored": round(avg_goals_scored, 2),
            "weighted_goals_conceded": round(avg_goals_conceded, 2)
        }
        consolidated_data.append(record)
        
        # Pre-calculate cards for matches 1 to 72 (group stage)
        group_stage_cards = {}
        for team_name in qualified_teams:
            group_stage_cards[normalize_name(team_name)] = {"yc": 0, "rc": 0}
            
        with open("fixtures.csv", "r", encoding="utf-8") as f_cards:
            reader_cards = csv.DictReader(f_cards)
            for row_c in reader_cards:
                if row_c['stage'] == 'group-stage':
                    m_num_c = int(row_c['match_number'])
                    home_nc = normalize_name(row_c['home_team'])
                    away_nc = normalize_name(row_c['away_team'])
                    yc_h, yc_a, rc_h, rc_a = get_deterministic_cards(home_nc, away_nc, m_num_c)
                    if home_nc in group_stage_cards:
                        group_stage_cards[home_nc]["yc"] += yc_h
                        group_stage_cards[home_nc]["rc"] += rc_h
                    if away_nc in group_stage_cards:
                        group_stage_cards[away_nc]["yc"] += yc_a
                        group_stage_cards[away_nc]["rc"] += rc_a

        # Get card statistics for this team
        c_stats = group_stage_cards.get(team, {"yc": 0, "rc": 0})
        yc = c_stats["yc"]
        rc = c_stats["rc"]
        if yc <= 3 and rc == 0:
            behavior = "comportado"
        elif yc >= 7 or rc >= 1:
            behavior = "rebelde"
        else:
            behavior = "neutro"
            
        record["yellow_cards"] = yc
        record["red_cards"] = rc
        record["card_behavior"] = behavior

        # Insert summary record into SQLite
        cursor.execute("""
        INSERT INTO teams_summary (team, fifa_rank, elo, form_index, attack_strength, defense_strength, weighted_win_rate, weighted_draw_rate, weighted_loss_rate, opponent_strength, weighted_goals_scored, weighted_goals_conceded, gas_next_match, gas_desc_next_match, yellow_cards, red_cards, card_behavior)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (team, current_fifa, int(round(current_elo)), round(avg_form_index, 1), round(attack_strength, 2), round(defense_strength, 2), round(avg_win_rate, 2), round(avg_draw_rate, 2), round(avg_loss_rate, 2), int(round(avg_opp_elo)), round(avg_goals_scored, 2), round(avg_goals_conceded, 2), 0.0, "", yc, rc, behavior))
        
    # 7. Simulate World Cup 2026 matches
    print("Simulating World Cup 2026 matches...")
    
    # Load actual Copa 2026 results
    print("Loading actual Copa 2026 results...")
    real_results = {}
    
    # Map matchups from fixtures to match numbers
    fixture_lookup = {}
    with open("fixtures.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['stage'] == 'group-stage':
                h_norm = normalize_name(row['home_team'])
                a_norm = normalize_name(row['away_team'])
                m_num = int(row['match_number'])
                fixture_lookup[(h_norm, a_norm)] = m_num

    # Ingest from results.csv (FIFA World Cup matches on/after 2026-06-11)
    with open("results.csv", "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['tournament'] == 'FIFA World Cup' and row['date'] >= '2026-06-11':
                h_norm = normalize_name(row['home_team'])
                a_norm = normalize_name(row['away_team'])
                h_score = row['home_score']
                a_score = row['away_score']
                if h_score and a_score and h_score != 'NA' and a_score != 'NA':
                    if (h_norm, a_norm) in fixture_lookup:
                        m_num = fixture_lookup[(h_norm, a_norm)]
                        real_results[m_num] = {
                            "home_score": int(h_score),
                            "away_score": int(a_score)
                        }

    # Ingest from copa_2026_real_results.json (manual overrides/updates)
    real_results_json = "copa_2026_real_results.json"
    if os.path.exists(real_results_json):
        try:
            with open(real_results_json, "r", encoding="utf-8") as f:
                custom_res = json.load(f)
                for m_num_str, scores in custom_res.items():
                    m_num = int(m_num_str)
                    real_results[m_num] = {
                        "home_score": int(scores["home_score"]),
                        "away_score": int(scores["away_score"])
                    }
            print(f"Loaded {len(custom_res)} custom results from JSON override.")
        except Exception as e:
            print(f"Error loading custom real results from JSON: {e}")
            
    print(f"Total resolved real results: {len(real_results)}")

    group_simulations = []
    
    # Calculate average defense strength across all 48 teams
    avg_defense = sum(t["defense_strength"] for t in consolidated_data) / len(consolidated_data)
    
    # Map teams by name for easy lookup
    teams_map = {t["team"]: t for t in consolidated_data}
    
    # 7.1 Group Stage Simulation (matches 1 to 72)
    with open("fixtures.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['stage'] == 'group-stage':
                match_num = int(row['match_number'])
                date_str = row['date']
                kickoff_utc = row['kickoff_utc']
                group_name = row['group']
                home = normalize_name(row['home_team'])
                away = normalize_name(row['away_team'])
                
                stats_h = teams_map[home]
                stats_a = teams_map[away]
                
                # Expected goals
                lambda_h = (stats_h["attack_strength"] * stats_a["defense_strength"]) / avg_defense
                lambda_a = (stats_a["attack_strength"] * stats_h["defense_strength"]) / avg_defense
                
                # Apply home advantage for host nations
                if home in ["Mexico", "Canada", "United States"]:
                    lambda_h *= 1.10
                    lambda_a /= 1.10
                    
                win_h, win_a, draw = 0.0, 0.0, 0.0
                over_1_5 = 0.0
                over_2_5 = 0.0
                btts = 0.0
                max_prob = -1.0
                best_score = (0, 0)
                
                for x in range(10):
                    probX = poisson_probability(x, lambda_h)
                    for y in range(10):
                        probY = poisson_probability(y, lambda_a)
                        probXY = probX * probY
                        
                        if x > y:
                            win_h += probXY
                        elif x < y:
                            win_a += probXY
                        else:
                            draw += probXY
                            
                        if x + y > 1:
                            over_1_5 += probXY
                        if x + y > 2:
                            over_2_5 += probXY
                        if x > 0 and y > 0:
                            btts += probXY
                            
                        if probXY > max_prob:
                            max_prob = probXY
                            best_score = (x, y)
                            
                # Normalize probabilities
                sum_prob = win_h + win_a + draw
                win_h /= sum_prob
                win_a /= sum_prob
                draw /= sum_prob
                
                is_alert = 1 if over_2_5 >= 0.70 else 0
                is_alert_1_5 = 1 if over_1_5 >= 0.85 else 0
                
                # Check for real results
                real_h = None
                real_a = None
                if match_num in real_results:
                    real_h = real_results[match_num]["home_score"]
                    real_a = real_results[match_num]["away_score"]
                
                # Calculate states and motivation before this match
                state_h = get_team_state_before_match(home, match_num, fixtures_list, real_results)
                state_a = get_team_state_before_match(away, match_num, fixtures_list, real_results)
                
                group_teams = group_teams_map.get(group_name, set())
                group_teams_states = []
                for team_g in group_teams:
                    group_teams_states.append(get_team_state_before_match(team_g, match_num, fixtures_list, real_results))
                    
                gas_h, gas_desc_h = calculate_gas_for_team(state_h, group_teams_states)
                gas_a, gas_desc_a = calculate_gas_for_team(state_a, group_teams_states)
                is_gas_alert = 1 if (gas_h >= 0.80 or gas_a >= 0.80) else 0
                
                # Generate cards
                home_yc, away_yc, home_rc, away_rc = get_deterministic_cards(home, away, match_num)
                
                sim_record = {
                    "match_number": match_num,
                    "date": date_str,
                    "kickoff_utc": kickoff_utc,
                    "group": group_name,
                    "stage": "group-stage",
                    "home_team": home,
                    "away_team": away,
                    "expected_goals_home": round(lambda_h, 2),
                    "expected_goals_away": round(lambda_a, 2),
                    "prob_win_home": round(win_h, 3),
                    "prob_draw": round(draw, 3),
                    "prob_win_away": round(win_a, 3),
                    "prob_over_1_5": round(over_1_5, 3),
                    "prob_over_2_5": round(over_2_5, 3),
                    "prob_btts": round(btts, 3),
                    "predicted_score_home": best_score[0],
                    "predicted_score_away": best_score[1],
                    "is_over_1_5_alert": is_alert_1_5,
                    "is_over_2_5_alert": is_alert,
                    "real_score_home": real_h,
                    "real_score_away": real_a,
                    "gas_home": round(gas_h, 2),
                    "gas_away": round(gas_a, 2),
                    "gas_desc_home": gas_desc_h,
                    "gas_desc_away": gas_desc_a,
                    "is_gas_alert": is_gas_alert,
                    "yc_home": home_yc,
                    "yc_away": away_yc,
                    "rc_home": home_rc,
                    "rc_away": away_rc
                }
                group_simulations.append(sim_record)
                
                # Write to SQLite
                cursor.execute("""
                INSERT INTO group_stage_simulations (
                    match_number, match_date, group_name, stage, home_team, away_team,
                    expected_goals_home, expected_goals_away, prob_win_home, prob_draw, prob_win_away,
                    prob_over_1_5, prob_over_2_5, prob_btts, predicted_score_home, predicted_score_away, 
                    is_over_1_5_alert, is_over_2_5_alert, real_goals_home, real_goals_away, kickoff_utc,
                    gas_home, gas_away, gas_desc_home, gas_desc_away, is_gas_alert,
                    yc_home, yc_away, rc_home, rc_away
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_num, date_str, group_name, "group-stage", home, away,
                    round(lambda_h, 2), round(lambda_a, 2), round(win_h, 3), round(draw, 3), round(win_a, 3),
                    round(over_1_5, 3), round(over_2_5, 3), round(btts, 3), best_score[0], best_score[1], 
                    is_alert_1_5, is_alert, real_h, real_a, kickoff_utc,
                    round(gas_h, 2), round(gas_a, 2), gas_desc_h, gas_desc_a, is_gas_alert,
                    home_yc, away_yc, home_rc, away_rc
                ))
                
    # 7.2 Calculate group standings & allocate 3rd places
    print("Calculating group standings and third-place allocations...")
    group_standings = get_group_standings(group_simulations, consolidated_data, fixtures_list)
    best_thirds = get_best_third_placed_teams(group_standings)
    best_thirds_allocation = allocate_third_places(best_thirds)
    
    # Track resolved knockout match winners/losers
    match_results_resolved = {}
    
    qualified_set = set()
    for g, teams in group_standings.items():
        if len(teams) >= 2:
            qualified_set.add(teams[0]["team"])
            qualified_set.add(teams[1]["team"])
    for t in best_thirds:
        qualified_set.add(t["team"])
        
    # 7.3 Knockout Stage Simulation (matches 73 to 104)
    print("Simulating knockout stage matches...")
    with open("fixtures.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage = row['stage']
            if stage != 'group-stage':
                match_num = int(row['match_number'])
                date_str = row['date']
                kickoff_utc = row['kickoff_utc']
                home_placeholder = row['home_team']
                away_placeholder = row['away_team']
                
                # Resolve placeholder names to actual teams
                if match_num <= 88:
                    home, away = resolve_r32_teams(match_num, group_standings, best_thirds_allocation)
                else:
                    home = resolve_team_placeholder(home_placeholder, match_results_resolved)
                    away = resolve_team_placeholder(away_placeholder, match_results_resolved)
                    
                # Setup map references
                stats_h = teams_map.get(home, {"attack_strength": 1.0, "defense_strength": 1.0, "elo": 1500})
                stats_a = teams_map.get(away, {"attack_strength": 1.0, "defense_strength": 1.0, "elo": 1500})
                
                # Expected goals
                lambda_h = (stats_h["attack_strength"] * stats_a["defense_strength"]) / avg_defense
                lambda_a = (stats_a["attack_strength"] * stats_h["defense_strength"]) / avg_defense
                
                # Apply home advantage for host nations
                if home in ["Mexico", "Canada", "United States"]:
                    lambda_h *= 1.10
                    lambda_a /= 1.10
                    
                win_h, win_a, draw = 0.0, 0.0, 0.0
                over_1_5 = 0.0
                over_2_5 = 0.0
                btts = 0.0
                max_prob = -1.0
                best_score = (0, 0)
                
                for x in range(10):
                    probX = poisson_probability(x, lambda_h)
                    for y in range(10):
                        probY = poisson_probability(y, lambda_a)
                        probXY = probX * probY
                        
                        if x > y:
                            win_h += probXY
                        elif x < y:
                            win_a += probXY
                        else:
                            draw += probXY
                            
                        if x + y > 1:
                            over_1_5 += probXY
                        if x + y > 2:
                            over_2_5 += probXY
                        if x > 0 and y > 0:
                            btts += probXY
                            
                        if probXY > max_prob:
                            max_prob = probXY
                            best_score = (x, y)
                            
                # Normalize probabilities
                sum_prob = win_h + win_a + draw
                win_h /= sum_prob
                win_a /= sum_prob
                draw /= sum_prob
                
                is_alert = 1 if over_2_5 >= 0.70 else 0
                is_alert_1_5 = 1 if over_1_5 >= 0.85 else 0
                
                # Check for real results
                real_h = None
                real_a = None
                if match_num in real_results:
                    real_h = real_results[match_num]["home_score"]
                    real_a = real_results[match_num]["away_score"]
                    
                # Determine winner and loser
                home_wins = True
                if real_h is not None and real_a is not None:
                    if real_h > real_a:
                        home_wins = True
                    elif real_h < real_a:
                        home_wins = False
                    else: # real tie, ELO tiebreaker
                        home_wins = (stats_h["elo"] >= stats_a["elo"])
                else:
                    if best_score[0] > best_score[1]:
                        home_wins = True
                    elif best_score[0] < best_score[1]:
                        home_wins = False
                    else: # simulated tie, ELO tiebreaker
                        home_wins = (stats_h["elo"] >= stats_a["elo"])
                        
                winner = home if home_wins else away
                loser = away if home_wins else home
                match_results_resolved[match_num] = {"winner": winner, "loser": loser}
                
                # Generate cards
                home_yc, away_yc, home_rc, away_rc = get_deterministic_cards(home, away, match_num)
                
                # GAS is not defined for knockout stage
                gas_h, gas_desc_h = 0.0, "Mata-mata"
                gas_a, gas_desc_a = 0.0, "Mata-mata"
                is_gas_alert = 0
                
                sim_record = {
                    "match_number": match_num,
                    "date": date_str,
                    "kickoff_utc": kickoff_utc,
                    "group": "",
                    "stage": stage,
                    "home_team": home,
                    "away_team": away,
                    "expected_goals_home": round(lambda_h, 2),
                    "expected_goals_away": round(lambda_a, 2),
                    "prob_win_home": round(win_h, 3),
                    "prob_draw": round(draw, 3),
                    "prob_win_away": round(win_a, 3),
                    "prob_over_1_5": round(over_1_5, 3),
                    "prob_over_2_5": round(over_2_5, 3),
                    "prob_btts": round(btts, 3),
                    "predicted_score_home": best_score[0],
                    "predicted_score_away": best_score[1],
                    "is_over_1_5_alert": is_alert_1_5,
                    "is_over_2_5_alert": is_alert,
                    "real_score_home": real_h,
                    "real_score_away": real_a,
                    "gas_home": round(gas_h, 2),
                    "gas_away": round(gas_a, 2),
                    "gas_desc_home": gas_desc_h,
                    "gas_desc_away": gas_desc_a,
                    "is_gas_alert": is_gas_alert,
                    "yc_home": home_yc,
                    "yc_away": away_yc,
                    "rc_home": home_rc,
                    "rc_away": away_rc
                }
                group_simulations.append(sim_record)
                
                # Write to SQLite
                cursor.execute("""
                INSERT INTO group_stage_simulations (
                    match_number, match_date, group_name, stage, home_team, away_team,
                    expected_goals_home, expected_goals_away, prob_win_home, prob_draw, prob_win_away,
                    prob_over_1_5, prob_over_2_5, prob_btts, predicted_score_home, predicted_score_away, 
                    is_over_1_5_alert, is_over_2_5_alert, real_goals_home, real_goals_away, kickoff_utc,
                    gas_home, gas_away, gas_desc_home, gas_desc_away, is_gas_alert,
                    yc_home, yc_away, rc_home, rc_away
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_num, date_str, "", stage, home, away,
                    round(lambda_h, 2), round(lambda_a, 2), round(win_h, 3), round(draw, 3), round(win_a, 3),
                    round(over_1_5, 3), round(over_2_5, 3), round(btts, 3), best_score[0], best_score[1], 
                    is_alert_1_5, is_alert, real_h, real_a, kickoff_utc,
                    round(gas_h, 2), round(gas_a, 2), gas_desc_h, gas_desc_a, is_gas_alert,
                    home_yc, away_yc, home_rc, away_rc
                ))
                
    # Update teams_summary gas and status fields based on final outcomes
    for team_record in consolidated_data:
        team_name = team_record["team"]
        
        # Calculate their tournament status
        status_desc = get_elimination_status(team_name, qualified_set, match_results_resolved)
        
        # Update record
        team_record["gas_next_match"] = 0.0
        team_record["gas_desc_next_match"] = status_desc
        
        cursor.execute("""
        UPDATE teams_summary
        SET gas_next_match = 0.0, gas_desc_next_match = ?
        WHERE team = ?
        """, (status_desc, team_name))
        
    # Save simulations to JSON
    with open("group_stage_simulations.json", "w", encoding="utf-8") as f:
        json.dump(group_simulations, f, indent=2, ensure_ascii=False)
        
    # Commit changes to SQLite
    conn.commit()
    conn.close()
    
    # Save to JSON
    with open("world_cup_2026_teams.json", "w", encoding="utf-8") as f:
        json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
        
    print(f"Data pipeline finished! Created SQLite '{db_file}' and JSON 'world_cup_2026_teams.json'.")

    # Run HTML generation automatically
    try:
        import generate_dashboard
        generate_dashboard.generate_html()
    except Exception as e:
        print("Error generating dashboard:", e)

if __name__ == "__main__":
    main()
