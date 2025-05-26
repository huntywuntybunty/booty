import re
from difflib import get_close_matches
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from constants import DATA_DIR
import traceback


def get_column_name(df, possible_names):
    """Return the first matching column name from a list of possibilities."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

def clean_name(name: str) -> str:
    """Normalize player names for consistent matching"""
    if not isinstance(name, str):
        return ""
    
    # Convert to lowercase and remove non-alphabetic characters
    name = re.sub(r'[^a-zA-Z]', '', name.lower())
    
    # Handle common nicknames and abbreviations
    nickname_map = {
        'vladimirguerrerojr': 'vladimirguerrero',
        'ronaldacuna': 'ronaldacunajr',
        'mikeozuna': 'marcellozuna',
        'mikeharris': 'michaelharrisii',
        # Add more common mappings as needed
    }
    return nickname_map.get(name, name)

# Extended nickname mapping for better matching
NICKNAME_MAP = {
    'vladimirguerrerojr': 'vladimirguerrero',
    'ronaldacuna': 'ronaldacunajr',
    'mikeozuna': 'marcellozuna',
    'mikeharris': 'michaelharrisii',
    'joshsmith': 'joshuasmith',
    'miketrout': 'michaeltrout',
    'chrisrodriguez': 'christianrodriguez',
    'nickmartinez': 'nicholasmartinez'
}

# League average stats by pitch type
LEAGUE_AVG_STATS = {
    "Breaking": {
        "k_percent": 0.25,
        "woba": 0.320,
        "whiff_percent": 0.30,
        "put_away": 0.18
    },
    "Fastball": {
        "k_percent": 0.18,
        "woba": 0.350,
        "whiff_percent": 0.15,
        "put_away": 0.12
    },
    "Offspeed": {
        "k_percent": 0.22,
        "woba": 0.330,
        "whiff_percent": 0.25,
        "put_away": 0.16
    }
}

# Pitch type mapping
PITCH_MAPPING = {
    "SL": "Breaking", "CU": "Breaking", "KC": "Breaking",
    "FF": "Fastball", "SI": "Fastball", "FC": "Fastball",
    "CH": "Offspeed", "FS": "Offspeed", "KN": "Offspeed"
}

class BatterStatsLoader:
    """Singleton class to load and manage batter stats"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_data()
        return cls._instance
    
    def _load_data(self):
        """Load batter stats with multiple fallback options"""
        self.stats_df = pd.DataFrame()
        self.match_stats = {'total': 0, 'matched': 0}
        
        paths_to_try = [
            DATA_DIR / "filled_batter_stats.csv",
            DATA_DIR / "batter_stats.csv",
            Path("fallback_batter_stats.csv")
        ]
        
        for path in paths_to_try:
            try:
                self.stats_df = pd.read_csv(path)
                self.stats_df['clean_name'] = self.stats_df['name'].apply(self._clean_name)
                print(f"✅ Loaded batter stats from {path} ({len(self.stats_df)} players)")
                break
            except Exception as e:
                print(f"⚠️ Failed to load {path}: {str(e)}")
        
        if self.stats_df.empty:
            print("❌ No batter stats available - using defaults only")

    @staticmethod
    def _clean_name(name: str) -> str:
        """Normalize names for matching"""
        if not isinstance(name, str):
            return ""
        
        # Basic cleaning
        name = re.sub(r'[^a-zA-Z]', '', name.lower())
        
        # Apply nickname mapping
        return NICKNAME_MAP.get(name, name)

# Initialize the loader when module loads
batter_loader = BatterStatsLoader()

def get_batter_stats(name: str, pitch_type: str) -> Dict:
    """
    Get batter stats with advanced matching logic.
    Returns dict with stats and matching metadata.
    """
    batter_loader.match_stats['total'] += 1
    pitch_type = pitch_type.capitalize()
    
    if batter_loader.stats_df.empty:
        return {**LEAGUE_AVG_STATS[pitch_type], "matched": False}
    
    clean_search = batter_loader._clean_name(name)
    
    try:
        # Strategy 1: Exact match
        exact_match = batter_loader.stats_df[
            batter_loader.stats_df['clean_name'] == clean_search
        ]
        if len(exact_match) == 1:
            batter_loader.match_stats['matched'] += 1
            return _format_stats(exact_match.iloc[0], pitch_type, True)
        
        # Strategy 2: First Last -> FLast
        if ' ' in name:
            parts = name.split()
            flast = f"{parts[0][0].lower()}{''.join(parts[1:]).lower()}"
            flast_match = batter_loader.stats_df[
                batter_loader.stats_df['clean_name'] == flast
            ]
            if len(flast_match) == 1:
                batter_loader.match_stats['matched'] += 1
                return _format_stats(flast_match.iloc[0], pitch_type, True)
        
        # Strategy 3: Fuzzy matching
        matches = get_close_matches(
            clean_search,
            batter_loader.stats_df['clean_name'],
            n=1,
            cutoff=0.85
        )
        if matches:
            fuzzy_match = batter_loader.stats_df[
                batter_loader.stats_df['clean_name'] == matches[0]
            ]
            if len(fuzzy_match) == 1:
                batter_loader.match_stats['matched'] += 1
                return _format_stats(fuzzy_match.iloc[0], pitch_type, True)
    
    except Exception as e:
        print(f"⚠️ Matching error for {name}: {str(e)}")
        traceback.print_exc()
    
    return {**LEAGUE_AVG_STATS[pitch_type], "matched": False}

def _format_stats(row: pd.Series, pitch_type: str, matched: bool) -> Dict:
    """Format batter stats from DataFrame row"""
    return {
        "name": row['name'],
        "k_percent": row[f'k_percent_{pitch_type}'],
        "woba": row[f'woba_{pitch_type}'],
        "whiff_percent": row[f'whiff_percent_{pitch_type}'],
        "put_away": row[f'put_away_{pitch_type}'],
        "player_id": row.get('player_id'),
        "matched": matched
    }

def preprocess_batter_from_lineup(batter: Dict) -> Dict:
    """Add defensive checks and improved name cleaning"""
    if not isinstance(batter, dict):
        return default_batter_stats()
        
    # Improved name cleaning
    raw_name = batter.get("name", "").strip()
    clean_name = re.sub(r'[^a-zA-Z.]', '', raw_name).lower()
    
    # Handle cases like "A. McCutchen" -> "andrew mccutchen"
    if '.' in clean_name:
        clean_name = expand_initials(clean_name)
    
    # Rest of processing...
    
    try:
        batter_name = batter.get("name", "Unknown")
        batter_hand = batter.get("hand", "R")
        pitch_category = PITCH_MAPPING.get(putaway_pitch, "Breaking")
        
        stats = get_batter_stats(batter_name, pitch_category)
        
        return {
            "name": batter_name,
            "hand": batter_hand,
            "k_percent": stats["k_percent"],
            "woba": stats["woba"],
            "whiff_percent": stats["whiff_percent"],
            "put_away": stats["put_away"],
            "player_id": stats.get("player_id"),
            "matched": stats["matched"],
            "pitch_type": pitch_category
        }
        
    except Exception as e:
        print(f"❌ Critical error processing batter {batter.get('name', 'Unknown')}:")
        traceback.print_exc()
        return {
            "name": batter.get("name", "Unknown"),
            "hand": batter.get("hand", "R"),
            **LEAGUE_AVG_STATS["Breaking"],
            "matched": False,
            "pitch_type": "Breaking"
        }

def print_batter_match_summary():
    """Print detailed matching statistics"""
    if batter_loader.match_stats['total'] > 0:
        match_rate = (batter_loader.match_stats['matched'] / 
                     batter_loader.match_stats['total']) * 100
        print(f"\n🔍 Batter Matching Summary:")
        print(f"  Total Batters: {batter_loader.match_stats['total']}")
        print(f"  Matched: {batter_loader.match_stats['matched']}")
        print(f"  Match Rate: {match_rate:.1f}%")

def parse_ip(ip_str) -> float:
    """
    Convert innings pitched string to decimal:
    '6.1' → 6.333, '7.2' → 7.667, '5' → 5.0, etc.
    Gracefully handles edge cases.
    """
    try:
        # Case 1: It's already a number
        if isinstance(ip_str, (int, float)):
            return float(ip_str)

        # Case 2: It's a string
        if isinstance(ip_str, str):
            ip_str = ip_str.strip()
            if "." in ip_str:
                whole, frac = ip_str.split(".")
                whole = int(whole)
                if frac == "1":
                    return whole + 1/3
                elif frac == "2":
                    return whole + 2/3
                else:
                    return float(whole)  # default fallback
            else:
                return float(ip_str)

    except Exception as e:
        print(f"⚠️ parse_ip() error for input: {ip_str} → {e}")

    return 0.0

