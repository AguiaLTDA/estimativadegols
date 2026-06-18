from datetime import datetime
import urllib.request
import urllib.parse
import json
import ssl
import re
import csv
import os
import html
import subprocess

def fetch_wikipedia_html():
    url = "https://en.wikipedia.org/w/api.php?action=parse&page=2026_FIFA_World_Cup&format=json&prop=text"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    print("Fetching latest match data from Wikipedia...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['parse']['text']['*']
    except Exception as e:
        print(f"Error fetching Wikipedia page: {e}")
        return None

def main():
    html_content = fetch_wikipedia_html()
    if not html_content:
        print("Could not retrieve data. Aborting update.")
        return
        
    # Load fixtures to get stadium names and match numbers
    fixtures = []
    stadiums = set()
    if not os.path.exists("fixtures.csv"):
        print("Error: fixtures.csv not found in workspace.")
        return
        
    with open("fixtures.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fixtures.append(row)
            stadiums.add(row['stadium'])
            
    # Load existing real results or initialize empty dict
    real_results_file = "copa_2026_real_results.json"
    real_results = {}
    if os.path.exists(real_results_file):
        try:
            with open(real_results_file, "r", encoding="utf-8") as f:
                real_results = json.load(f)
        except Exception as e:
            print(f"Error loading existing results: {e}. Starting fresh.")
            
    # Find all footballbox divs
    box_starts = [m.start() for m in re.finditer(r'<div[^>]*class="[^"]*footballbox[^"]*"[^>]*>', html_content, re.IGNORECASE)]
    boxes = []
    for i in range(len(box_starts)):
        start = box_starts[i]
        end = box_starts[i+1] if i+1 < len(box_starts) else len(html_content)
        boxes.append(html_content[start:end])
        
    print(f"Found {len(boxes)} matches on Wikipedia.")
    
    updates_made = 0
    new_results_count = 0
    
    for idx, box in enumerate(boxes):
        unescaped_box = html.unescape(box)
        
        # 1. Extract Date (2026-MM-DD)
        date_match = re.search(r'\b2026-\d{2}-\d{2}\b', unescaped_box)
        if not date_match:
            continue
        date_str = date_match.group(0)
        
        # 2. Extract Stadium
        found_stadium = None
        for stad in stadiums:
            pattern = re.sub(r"[‘'’]", "[‘'’]", stad)
            if re.search(pattern, unescaped_box, re.IGNORECASE):
                found_stadium = stad
                break
                
        if not found_stadium:
            continue
            
        # 3. Find the unique match_number in fixtures.csv
        matched_fixtures = [f for f in fixtures if f['date'] == date_str and f['stadium'] == found_stadium]
        if len(matched_fixtures) != 1:
            continue
            
        fixture = matched_fixtures[0]
        match_number_str = fixture['match_number']
        
        # 4. Extract Score
        # Typically inside <th class="fscore">...</th>
        score_match = re.search(r'<th[^>]*class="[^"]*fscore[^"]*"[^>]*>(.*?)</th>', unescaped_box, re.DOTALL | re.IGNORECASE)
        if not score_match:
            continue
            
        # Clean up score tag content
        score_html = score_match.group(1)
        score_text = re.sub(r'<[^>]+>', ' ', score_html)
        score_text = re.sub(r'\s+', ' ', score_text).strip()
        score_clean = score_text.replace('\u2212', '-').replace('\u2013', '-').replace('\u2014', '-')
        
        # Check if score represents a finished match (e.g. "2-0", "1-1")
        match_score = re.match(r'^(\d+)\s*-\s*(\d+)$', score_clean)
        if match_score:
            home_score = int(match_score.group(1))
            away_score = int(match_score.group(2))
            
            # Check if this is new or updated
            match_key = str(match_number_str)
            existing_result = real_results.get(match_key)
            
            if not existing_result or existing_result['home_score'] != home_score or existing_result['away_score'] != away_score:
                if not existing_result:
                    new_results_count += 1
                    print(f"New result found for Match {match_key} ({fixture['home_team']} vs {fixture['away_team']}): {home_score}-{away_score}")
                else:
                    updates_made += 1
                    print(f"Updated result for Match {match_key} ({fixture['home_team']} vs {fixture['away_team']}): {existing_result['home_score']}-{existing_result['away_score']} -> {home_score}-{away_score}")
                
                real_results[match_key] = {
                    "home_score": home_score,
                    "away_score": away_score
                }
                
    # Save results to json
    if new_results_count > 0 or updates_made > 0:
        with open(real_results_file, "w", encoding="utf-8") as f:
            json.dump(real_results, f, indent=2, ensure_ascii=False)
        print(f"Saved {new_results_count} new results and {updates_made} updates to {real_results_file}.")
        
        # Run the data pipeline to recalculate everything
        print("Running data pipeline to regenerate database and dashboard...")
        try:
            result = subprocess.run(["python", "data_pipeline.py"], capture_output=True, text=True, check=True)
            print("Data pipeline executed successfully.")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print("Error executing data_pipeline.py:")
            print(e.stderr)
            return
            
        # Commit and push to GitHub automatically
        print("Committing and pushing updates to GitHub...")
        try:
            # Add changes
            subprocess.run(["git", "add", "."], check=True)
            # Commit changes
            commit_msg = f"Auto-update match results and dashboard: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            # Push changes
            subprocess.run(["git", "push"], check=True)
            print("Successfully committed and pushed changes to GitHub.")
        except subprocess.CalledProcessError as e:
            print(f"Error during git operations: {e}")
    else:
        print("No new results or updates found. Database is up to date.")

if __name__ == "__main__":
    main()
