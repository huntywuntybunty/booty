import requests
import json
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import unicodedata
import time
import traceback

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def load_manual_overrides() -> Dict[str, str]:
    """Load manual player ID overrides from a file"""
    override_path = Path("manual_overrides.json")
    if override_path.exists():
        try:
            with open(override_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[⚠️] Error loading manual overrides: {e}")
    return {}

def save_to_manual_overrides(name: str, player_id: str):
    """Save a manual override to the file"""
    overrides = load_manual_overrides()
    overrides[name] = player_id
    
    try:
        with open("manual_overrides.json", "w") as f:
            json.dump(overrides, f, indent=2)
        print(f"✅ Saved override for {name}")
    except Exception as e:
        print(f"❌ Failed to save override: {e}")

def find_player_id_interactive(name: str) -> Optional[str]:
    """Interactive helper to find a player ID"""
    print(f"\n🔍 Could not automatically find ID for {name}")
    print("Searching MLB API for possible matches...")
    
    search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={name}"
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if not data.get('people'):
                print("No matching players found in API search")
                return None
            
            print("\nPossible matches found:")
            players = data['people']
            for i, player in enumerate(players, 1):
                full_name = f"{player.get('firstName', '')} {player.get('lastName', '')}"
                print(f"{i}. {full_name} (ID: {player['id']})")
            
            while True:
                selection = input("\nEnter number to use (or 0 to skip): ").strip()
                if selection == '0':
                    return None
                if not selection.isdigit():
                    print("Please enter a number")
                    continue
                
                selection_idx = int(selection) - 1
                if 0 <= selection_idx < len(players):
                    return str(players[selection_idx]['id'])
                print(f"Please enter a number between 1 and {len(players)}")
    
    except Exception as e:
        print(f"Error during interactive search: {e}")
        traceback.print_exc()
    
    return None

def get_player_info(name: str) -> dict:
    """Get player info with team data from K scraper output"""
    try:
        with open("todays_pitcher_teams.json", "r") as f:
            props_teams = json.load(f)
        
        correct_team = props_teams.get(name)
        if correct_team:
            print(f"[✅] Found props team for {name}: {correct_team}")
            return {'team': correct_team, 'hand': None}
        else:
            print(f"[⚠️] {name} not found in props teams file")
            return {'team': 'UNK', 'hand': None}
            
    except FileNotFoundError:
        print(f"[❌] todays_pitcher_teams.json not found! Run K scraper first.")
        return {'team': 'UNK', 'hand': None}
    except Exception as e:
        print(f"[❌] Error reading props teams: {e}")
        return {'team': 'UNK', 'hand': None}

def normalize_name(name: str) -> str:
    """Normalize player name for better matching"""
    # Remove accents and special characters
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])
    
    # Common name replacements
    replacements = {
        'José': 'Jose',
        'Cristopher': 'Christopher',
        'Cristian': 'Christian',
        'Zebby': 'Zebulon',
        'A.J.': 'AJ',
        'J.P.': 'JP',
        'D.J.': 'DJ'
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    return name.strip()

def get_player_id_advanced(name: str) -> Optional[str]:
    """Advanced player ID lookup with multiple strategies"""
    # Check manual overrides first
    manual_overrides = load_manual_overrides()
    if name in manual_overrides:
        print(f"   Using manual override ID for {name}: {manual_overrides[name]}")
        return manual_overrides[name]
    
    # Strategy 1: Try exact name first
    player_id = search_mlb_api(name)
    if player_id:
        return player_id
    
    # Strategy 2: Try normalized name
    normalized = normalize_name(name)
    if normalized != name:
        print(f"   Trying normalized: {normalized}")
        player_id = search_mlb_api(normalized)
        if player_id:
            return player_id
    
    # Strategy 3: Try name variations
    name_parts = name.split()
    if len(name_parts) >= 2:
        variations = [
            f"{name_parts[0]} {name_parts[-1]}",  # First + Last
            f"{name_parts[-1]}, {name_parts[0]}",  # Last, First
            name_parts[-1],  # Last name only
        ]
        
        # Add middle name variations if exists
        if len(name_parts) > 2:
            variations.extend([
                f"{name_parts[0]} {name_parts[1]}",  # First + Middle
                " ".join(name_parts[:2]),  # First two names
            ])
        
        for variation in variations:
            if variation != name:
                print(f"   Trying variation: {variation}")
                player_id = search_mlb_api(variation)
                if player_id:
                    return player_id
    
    # Strategy 4: Try with common nickname expansions
    nickname_map = {
        'Jake': 'Jacob',
        'Mike': 'Michael',
        'Tony': 'Anthony',
        'Chris': 'Christopher',
        'Matt': 'Matthew',
        'Alex': 'Alexander',
        'Nick': 'Nicholas'
    }
    
    first_name = name_parts[0] if name_parts else ""
    if first_name in nickname_map:
        full_name = name.replace(first_name, nickname_map[first_name])
        print(f"   Trying full name: {full_name}")
        player_id = search_mlb_api(full_name)
        if player_id:
            return player_id
    
    # Strategy 5: Try reverse nickname lookup
    for nick, full in nickname_map.items():
        if first_name == full:
            nick_name = name.replace(first_name, nick)
            print(f"   Trying nickname: {nick_name}")
            player_id = search_mlb_api(nick_name)
            if player_id:
                return player_id
    
    print(f"[❌] All search strategies failed for {name}")
    return None

def search_mlb_api(search_name: str) -> Optional[str]:
    """Search MLB API for player"""
    try:
        clean_name = re.sub(r'[^a-zA-Z\s]', '', search_name).strip()
        if not clean_name:
            return None
            
        search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={clean_name}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            for player in data.get('people', []):
                full_name = f"{player.get('firstName', '')} {player.get('lastName', '')}"
                
                # Check if this is a good match
                if is_name_match(search_name, full_name):
                    print(f"   ✅ MATCH: {search_name} → {full_name} (ID: {player['id']})")
                    return str(player['id'])
        
        time.sleep(0.1)  # Rate limiting
        return None
        
    except Exception as e:
        print(f"   ❌ API error: {e}")
        return None

def is_name_match(search_name: str, full_name: str) -> bool:
    """More strict name matching to avoid wrong players"""
    search_lower = search_name.lower()
    full_lower = full_name.lower()
    
    # Exact match
    if search_lower == full_lower:
        return True
    
    search_parts = [p for p in search_lower.split() if len(p) > 1]
    full_parts = [p for p in full_lower.split() if len(p) > 1]
    
    if not search_parts or not full_parts:
        return False
    
    # STRICT: Last name must match exactly
    if search_parts[-1] != full_parts[-1]:
        return False
    
    # STRICT: First name must match (not just initial)
    if len(search_parts) >= 1 and len(full_parts) >= 1:
        search_first = search_parts[0]
        full_first = full_parts[0]
        
        # Exact first name match OR known nickname mapping
        nickname_map = {
            'jake': 'jacob',
            'zach': 'zachary', 
            'chris': 'christopher',
            'mike': 'michael',
            'tony': 'anthony'
        }
        
        if (search_first == full_first or 
            nickname_map.get(search_first) == full_first or
            nickname_map.get(full_first) == search_first):
            return True
    
    return False

def get_pitcher_logs(player_id: str, season: int = 2025) -> tuple:
    """DEBUG: Get pitcher game logs with detailed logging"""
    try:
        print(f"   [DEBUG] Getting logs for player ID: {player_id}")
        
        # Get player details first for handedness
        player_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"
        player_response = requests.get(player_url, headers=HEADERS, timeout=10)
        
        hand = None
        if player_response.status_code == 200:
            player_data = player_response.json()
            if player_data.get('people'):
                person = player_data['people'][0]
                pitch_hand = person.get('pitchHand', {})
                hand = pitch_hand.get('code') if pitch_hand else None
                print(f"   [DEBUG] Found handedness: {hand}")
        
        # Get game logs with detailed debugging
        stats_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"
        params = {
            'stats': 'gameLog',
            'gameType': 'R', 
            'season': season,
            'group': 'pitching'
        }
        
        print(f"   [DEBUG] Requesting: {stats_url}")
        print(f"   [DEBUG] Params: {params}")
        
        response = requests.get(stats_url, params=params, headers=HEADERS, timeout=10)
        print(f"   [DEBUG] Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [DEBUG] Response keys: {list(data.keys())}")
            
            if 'stats' in data:
                print(f"   [DEBUG] Found {len(data['stats'])} stat groups")
                for i, stat_group in enumerate(data['stats']):
                    splits = stat_group.get('splits', [])
                    print(f"   [DEBUG] Stat group {i}: {len(splits)} splits")
            
            logs = []
            
            for stat_group in data.get('stats', []):
                for split in stat_group.get('splits', []):
                    stat = split.get('stat', {})
                    game = split.get('game', {})
                    
                    innings_pitched = stat.get('inningsPitched', '0.0')
                    strikeouts = stat.get('strikeOuts', 0)
                    
                    print(f"   [DEBUG] Game: IP={innings_pitched}, K={strikeouts}")
                    
                    if innings_pitched != '0.0':
                        logs.append({
                            'gamePk': game.get('gamePk'),
                            'strikeouts': strikeouts,
                            'innings_pitched': innings_pitched
                        })
            
            print(f"   [DEBUG] Total valid games found: {len(logs)}")
            return logs, hand
        else:
            print(f"   [DEBUG] API request failed: {response.status_code}")
            print(f"   [DEBUG] Response text: {response.text[:200]}")
            return [], hand
            
    except Exception as e:
        print(f"   [DEBUG] Exception: {e}")
        traceback.print_exc()
    
    return [], None

def save_pitcher_cache(pitcher_name: str, handedness: str, logs: list, team: str, cache_dir: Path = Path("cache")):
    """Save pitcher data to cache - only cache if we have data"""
    
    # Don't cache empty results
    if not logs:
        print(f"[⚠️] Not caching {pitcher_name} - no games found")
        return
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{pitcher_name.replace(' ', '_').lower()}_2025.json"
    
    cache_data = {
        "name": pitcher_name,
        "hand": handedness,
        "team": team,
        "logs": logs,
        "cached_at": datetime.now().isoformat()
    }
    
    with open(path, "w") as f:
        json.dump(cache_data, f, indent=2)
    
    hand_display = handedness if handedness else "UNKNOWN"
    print(f"[💾] Cached {pitcher_name} ({team}) - {len(logs)} games, {hand_display}-handed")

def get_recent_ks_and_ip(pitcher_name: str, season: int = 2025):
    """Get recent strikeouts and innings pitched for a pitcher"""
    print(f"\n[🔍] Processing {pitcher_name}...")
    
    # Get team from props data
    player_info = get_player_info(pitcher_name)
    props_team = player_info['team']
    
    if props_team == 'UNK':
        print(f"[❌] {pitcher_name} not found in props data - skipping")
        return [], [], None, "UNK", []
    
    # Check cache (only load if it has games)
    safe_name = pitcher_name.replace(" ", "_").lower()
    cache_path = Path("cache") / f"{safe_name}_2025.json"
    
    if cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                cached_data = json.load(f)
            
            logs = cached_data.get("logs", [])
            
            # Only use cache if it has actual game data
            if logs:
                hand = cached_data.get("hand")
                ks = [log["strikeouts"] for log in logs]
                ip = [log["innings_pitched"] for log in logs]
                
                hand_display = hand if hand else "UNKNOWN"
                print(f"[✅] Loaded from cache: {len(logs)} games, team: {props_team}, hand: {hand_display}")
                return ks, ip, hand, props_team, logs
            else:
                print(f"[🗑️] Removing empty cache for {pitcher_name}")
                cache_path.unlink()  # Delete empty cache
                
        except Exception as e:
            print(f"[⚠️] Cache error for {pitcher_name}: {e}")
    
    # Fetch fresh data
    print(f"[🌐] Fetching fresh data for {pitcher_name}...")
    
    player_id = get_player_id_advanced(pitcher_name)
    if not player_id:
        print(f"[❌] Could not find MLB ID for {pitcher_name}")
        if input("Try interactive search? (y/n): ").lower() == 'y':
            player_id = find_player_id_interactive(pitcher_name)
            if player_id:
                if input("Save this ID to manual overrides? (y/n): ").lower() == 'y':
                    save_to_manual_overrides(pitcher_name, player_id)
            else:
                return [], [], None, props_team, []
        else:
            return [], [], None, props_team, []
    
    logs, hand = get_pitcher_logs(player_id, season)
    
    # Save to cache (only if we have data)
    if logs:
        save_pitcher_cache(pitcher_name, hand, logs, props_team)
    
    ks = [log["strikeouts"] for log in logs]
    ip = [log["innings_pitched"] for log in logs]
    
    return ks, ip, hand, props_team, logs

if __name__ == "__main__":
    print("=== MLB SCRAPER: DEBUG VERSION ===")
    
    try:
        with open("todays_pitcher_teams.json", "r") as f:
            pitcher_teams = json.load(f)
        
        print(f"📋 Found {len(pitcher_teams)} pitchers to process")
        
        successful_count = 0
        failed_count = 0
        missing_hand_count = 0
        
        for i, pitcher_name in enumerate(pitcher_teams.keys(), 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(pitcher_teams)}] Processing: {pitcher_name}")
            
            ks, ip, hand, team, logs = get_recent_ks_and_ip(pitcher_name)
            
            if logs:
                hand_display = hand if hand else "UNKNOWN"
                print(f"✅ {pitcher_name} ({team}): {len(logs)} games, {hand_display}-handed")
                if ks:
                    recent_ks = ks[-5:] if len(ks) >= 5 else ks
                    print(f"   Recent K's: {recent_ks}")
                successful_count += 1
                
                if hand is None:
                    missing_hand_count += 1
            else:
                print(f"❌ {pitcher_name} ({team}): No data found")
                failed_count += 1
        
        print(f"\n{'='*60}")
        print(f"🎉 PROCESSING COMPLETE!")
        print(f"✅ Successful: {successful_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"⚠️ Missing handedness: {missing_hand_count}")
        
    except FileNotFoundError:
        print("❌ todays_pitcher_teams.json not found! Run K scraper first.")
    except Exception as e:
        print(f"❌ Error processing pitchers: {e}")
