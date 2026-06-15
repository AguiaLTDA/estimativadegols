import csv
import json
import sqlite3
import os
import re
import math

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

    # Initialize Elo ratings
    elo = {} # team -> Elo rating
    
    processed_matches = []
    
    # Chronological simulation
    for idx, match in enumerate(all_matches):
        date_str = match['date']
        
        # We only consider matches up to local date (June 14, 2026)
        if date_str > "2026-06-14":
            continue
            
        home = normalize_name(match['home_team'])
        away = normalize_name(match['away_team'])
        
        # Skip matches without score
        if not match['home_score'] or match['home_score'] == 'NA':
            continue
        if not match['away_score'] or match['away_score'] == 'NA':
            continue
            
        home_score = int(match['home_score'])
        away_score = int(match['away_score'])
        
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
    
    # Create SQLite tables
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
        weighted_goals_conceded REAL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE group_stage_simulations (
        match_number INTEGER PRIMARY KEY,
        match_date TEXT,
        group_name TEXT,
        home_team TEXT,
        away_team TEXT,
        expected_goals_home REAL,
        expected_goals_away REAL,
        prob_win_home REAL,
        prob_draw REAL,
        prob_win_away REAL,
        prob_over_2_5 REAL,
        prob_btts REAL,
        predicted_score_home INTEGER,
        predicted_score_away INTEGER,
        is_over_2_5_alert INTEGER,
        real_goals_home INTEGER,
        real_goals_away INTEGER,
        kickoff_utc TEXT
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
    
    # Process each qualified team
    for team in sorted(qualified_teams):
        # Filter matches where this team played
        team_matches = []
        for m in processed_matches:
            if m['home_team'] == team or m['away_team'] == team:
                team_matches.append(m)
                
        # Sort by date ascending to get recent ones at the end
        team_matches.sort(key=lambda x: x['date'])
        
        # Take the last 20 matches
        N = len(team_matches)
        if N > 20:
            team_matches = team_matches[-20:]
            N = 20
            
        if N == 0:
            print(f"Warning: No matches found for {team} before June 14, 2026!")
            continue
            
        # Compute weights
        weights = []
        for i in range(1, N + 1):
            w = 0.40 + 0.60 * (i - 1) / max(1, N - 1)
            weights.append(w)
            
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
        
        # Insert summary record into SQLite
        cursor.execute("""
        INSERT INTO teams_summary (team, fifa_rank, elo, form_index, attack_strength, defense_strength, weighted_win_rate, weighted_draw_rate, weighted_loss_rate, opponent_strength, weighted_goals_scored, weighted_goals_conceded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (team, current_fifa, int(round(current_elo)), round(avg_form_index, 1), round(attack_strength, 2), round(defense_strength, 2), round(avg_win_rate, 2), round(avg_draw_rate, 2), round(avg_loss_rate, 2), int(round(avg_opp_elo)), round(avg_goals_scored, 2), round(avg_goals_conceded, 2)))
        
    # 7. Simulate World Cup 2026 group stage matches
    print("Simulating World Cup 2026 group stage matches...")
    
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
            
    print(f"Total resolved real results for group stage: {len(real_results)}")

    group_simulations = []
    
    # Calculate average defense strength across all 48 teams
    avg_defense = sum(t["defense_strength"] for t in consolidated_data) / len(consolidated_data)
    
    # Map teams by name for easy lookup
    teams_map = {t["team"]: t for t in consolidated_data}
    
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
                
                # Over 2.5 alert threshold is 70%
                is_alert = 1 if over_2_5 >= 0.70 else 0
                
                # Check for real results
                real_h = None
                real_a = None
                if match_num in real_results:
                    real_h = real_results[match_num]["home_score"]
                    real_a = real_results[match_num]["away_score"]
                
                sim_record = {
                    "match_number": match_num,
                    "date": date_str,
                    "kickoff_utc": kickoff_utc,
                    "group": group_name,
                    "home_team": home,
                    "away_team": away,
                    "expected_goals_home": round(lambda_h, 2),
                    "expected_goals_away": round(lambda_a, 2),
                    "prob_win_home": round(win_h, 3),
                    "prob_draw": round(draw, 3),
                    "prob_win_away": round(win_a, 3),
                    "prob_over_2_5": round(over_2_5, 3),
                    "prob_btts": round(btts, 3),
                    "predicted_score_home": best_score[0],
                    "predicted_score_away": best_score[1],
                    "is_over_2_5_alert": is_alert,
                    "real_score_home": real_h,
                    "real_score_away": real_a
                }
                group_simulations.append(sim_record)
                
                # Write to SQLite
                cursor.execute("""
                INSERT INTO group_stage_simulations (
                    match_number, match_date, group_name, home_team, away_team,
                    expected_goals_home, expected_goals_away, prob_win_home, prob_draw, prob_win_away,
                    prob_over_2_5, prob_btts, predicted_score_home, predicted_score_away, is_over_2_5_alert,
                    real_goals_home, real_goals_away, kickoff_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_num, date_str, group_name, home, away,
                    round(lambda_h, 2), round(lambda_a, 2), round(win_h, 3), round(draw, 3), round(win_a, 3),
                    round(over_2_5, 3), round(btts, 3), best_score[0], best_score[1], is_alert,
                    real_h, real_a, kickoff_utc
                ))
                
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
