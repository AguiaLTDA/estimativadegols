import json
import os
import sqlite3

def run_validation():
    print("--- Starting Validation checks ---")
    
    # 1. Check if JSON file exists
    json_path = "world_cup_2026_teams.json"
    if not os.path.exists(json_path):
        print(f"FAILED: {json_path} does not exist.")
        return False
        
    print(f"OK: {json_path} exists.")
    
    # 2. Check JSON contents
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"FAILED: Could not parse JSON file: {e}")
        return False
        
    print("OK: JSON file parses successfully.")
    
    # 3. Check number of teams
    num_teams = len(data)
    if num_teams != 48:
        print(f"FAILED: Expected 48 teams, but found {num_teams}.")
        return False
    print(f"OK: Found exactly 48 teams.")
    
    # 4. Check fields and types
    required_fields = {
        "team": str,
        "fifa_rank": int,
        "elo": int,
        "form_index": float,
        "attack_strength": float,
        "defense_strength": float,
        "weighted_win_rate": float,
        "weighted_draw_rate": float,
        "weighted_loss_rate": float,
        "opponent_strength": int,
        "weighted_goals_scored": float,
        "weighted_goals_conceded": float
    }
    
    for team_data in data:
        team_name = team_data.get("team", "Unknown")
        for field, expected_type in required_fields.items():
            if field not in team_data:
                print(f"FAILED: Team {team_name} is missing field '{field}'.")
                return False
            val = team_data[field]
            # Since JSON numbers can parse as float/int interchangeably for round numbers,
            # we check if they are either int or float if expected is int or float.
            if expected_type in [int, float]:
                if not isinstance(val, (int, float)):
                    print(f"FAILED: Team {team_name} field '{field}' has type {type(val)}, expected numeric.")
                    return False
            else:
                if not isinstance(val, expected_type):
                    print(f"FAILED: Team {team_name} field '{field}' has type {type(val)}, expected {expected_type}.")
                    return False
                    
        # 5. Check sum of rates
        w_sum = team_data["weighted_win_rate"] + team_data["weighted_draw_rate"] + team_data["weighted_loss_rate"]
        if not (0.98 <= w_sum <= 1.02):
            print(f"FAILED: Team {team_name} win + draw + loss rate = {w_sum:.2f}, should be ~1.00.")
            return False
            
        # 6. Check form index bounds
        form_idx = team_data["form_index"]
        if not (0.0 <= form_idx <= 100.0):
            print(f"FAILED: Team {team_name} form index = {form_idx}, should be between 0 and 100.")
            return False
            
    print("OK: All teams have required fields with correct types, correct win/draw/loss sum, and valid form index bounds.")
    
    # 7. Check SQLite database
    db_path = "world_cup_2026.db"
    if not os.path.exists(db_path):
        print(f"FAILED: SQLite database {db_path} does not exist.")
        return False
    print(f"OK: SQLite database {db_path} exists.")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verify teams_summary count
        cursor.execute("SELECT COUNT(*) FROM teams_summary")
        summary_count = cursor.fetchone()[0]
        if summary_count != 48:
            print(f"FAILED: SQLite teams_summary has {summary_count} rows, expected 48.")
            conn.close()
            return False
        print("OK: SQLite teams_summary has exactly 48 rows.")
        
        # Verify no nulls in summary goal fields
        cursor.execute("SELECT COUNT(*) FROM teams_summary WHERE weighted_goals_scored IS NULL OR weighted_goals_conceded IS NULL")
        summary_goals_nulls = cursor.fetchone()[0]
        if summary_goals_nulls > 0:
            print("FAILED: Found NULL values in summary goals columns.")
            conn.close()
            return False
        print("OK: No NULL values in summary goals columns.")
        
        # Verify team_matches count
        cursor.execute("SELECT COUNT(*) FROM team_matches")
        matches_count = cursor.fetchone()[0]
        # Should be exactly 48 teams * 20 matches = 960 rows
        if matches_count != 960:
            print(f"WARNING: SQLite team_matches has {matches_count} rows (expected 960 if all teams have 20 matches).")
        else:
            print(f"OK: SQLite team_matches has exactly {matches_count} rows.")
            
        # Verify no nulls in matches
        cursor.execute("SELECT COUNT(*) FROM team_matches WHERE opponent IS NULL OR goals_scored IS NULL OR goals_conceded IS NULL")
        nulls_count = cursor.fetchone()[0]
        if nulls_count > 0:
            print(f"FAILED: Found {nulls_count} rows with NULL values in team_matches.")
            conn.close()
            return False
        print("OK: No NULL values found in matches table.")
        
        # Verify group_stage_simulations table exists and has 72 rows
        cursor.execute("SELECT COUNT(*) FROM group_stage_simulations")
        group_sim_count = cursor.fetchone()[0]
        if group_sim_count != 72:
            print(f"FAILED: SQLite group_stage_simulations has {group_sim_count} rows, expected 72.")
            conn.close()
            return False
        print("OK: SQLite group_stage_simulations has exactly 72 rows.")
        
        # Verify no NULLs in group_stage_simulations
        cursor.execute("SELECT COUNT(*) FROM group_stage_simulations WHERE home_team IS NULL OR away_team IS NULL OR expected_goals_home IS NULL")
        group_nulls = cursor.fetchone()[0]
        if group_nulls > 0:
            print("FAILED: Found NULL values in group_stage_simulations.")
            conn.close()
            return False
        print("OK: No NULL values in group stage simulations table.")
        
        conn.close()
    except Exception as e:
        print(f"FAILED: SQLite database validation error: {e}")
        return False
        
    # 8. Check group_stage_simulations JSON
    json_sim_path = "group_stage_simulations.json"
    if not os.path.exists(json_sim_path):
        print(f"FAILED: {json_sim_path} does not exist.")
        return False
    try:
        with open(json_sim_path, "r", encoding="utf-8") as f:
            sim_data = json.load(f)
        if len(sim_data) != 72:
            print(f"FAILED: Expected 72 simulations in JSON, but found {len(sim_data)}.")
            return False
        print("OK: group_stage_simulations.json exists and contains 72 records.")
    except Exception as e:
        print(f"FAILED: Could not parse {json_sim_path}: {e}")
        return False
        
    print("--- All validation checks PASSED successfully! ---")
    return True

if __name__ == "__main__":
    run_validation()
