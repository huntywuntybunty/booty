import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from difflib import get_close_matches
from constants import CATCHER_FRAMING_DICT, PARK_FACTORS, LEAGUE_AVG_TEAM_K_PCT, TEAM_ABBREV_MAP
from stats_logic import get_column_name
from preprocessor import clean_name
from modifiers import get_dynamic_platoon_modifier

def get_recent_team_row(team_name: str, df: pd.DataFrame) -> Optional[dict]:
    try:
        team_col = get_column_name(df, ['Team', 'team', 'Tm', 'tm'])
        if not team_col:
            print(f"⚠️ No team column found in DataFrame (columns: {df.columns.tolist()})")
            return None
        team_name = team_name.strip().upper()
        df['_temp_team'] = df[team_col].astype(str).str.strip().str.upper()
        row = df[df['_temp_team'] == team_name]
        if not row.empty:
            return row.iloc[0].to_dict()
        close = get_close_matches(team_name, df['_temp_team'].unique().tolist(), n=1, cutoff=0.8)
        if close:
            return df[df['_temp_team'] == close[0]].iloc[0].to_dict()
        return None
    except Exception as e:
        print(f"⚠️ Error getting team row: {str(e)}")
        return None
    finally:
        if '_temp_team' in df.columns:
            df.drop('_temp_team', axis=1, inplace=True)

def calculate_catcher_framing_modifier(catcher_name: str) -> float:
    mod = CATCHER_FRAMING_DICT.get(catcher_name, 0.0)
    percent_mod = mod * -3.94
    multiplier = 1 + (percent_mod / 100.0)
    print(f"[Framing] {catcher_name} framing: {mod:+.2f} runs → {percent_mod:+.2f}% → Modifier: {multiplier:.3f}")
    return np.clip(multiplier, 0.95, 1.05)

def get_stuff_plus(pitcher_row) -> float:
    val = pitcher_row.get("Stuff+") or pitcher_row.get("stuff+")
    return 100.0 if pd.isna(val) else float(val)

def get_park_modifier(park_name: str) -> float:
    if not isinstance(park_name, str):
        print("[Park] Invalid input type for park name")
        return 1.0
    normalized = park_name.strip().lower()
    for official_name, mod in PARK_FACTORS.items():
        if normalized in official_name.lower():
            print(f"[Park] Modifier for {official_name}: {mod:.3f}")
            return mod
    print(f"[Park] No park factor found for '{park_name}' — defaulting to 1.000")
    return 1.0

def get_dynamic_platoon_modifier(pitcher_name: str, pitcher_hand: str, batter_hand: str,
                                  vs_lhh_df: pd.DataFrame, vs_rhh_df: pd.DataFrame,
                                  league_avg_k_pct: float = 0.215) -> float:
    pitcher_name = pitcher_name.strip()

    df = vs_lhh_df if batter_hand == "L" else vs_rhh_df

    try:
        pitcher_row = df[df["Name"] == pitcher_name].iloc[0]
        k_pct = pitcher_row["K%"]
    except IndexError:
        return 1.0  # fallback

    # Compute delta from league average, bounded
    delta = max(min(k_pct - league_avg_k_pct, 0.03), -0.03)  # cap at +/- 3%

    return 1.0 + delta


def calculate_team_trend_modifier(team_name, pitcher_hand, l21_lhp_df, l21_rhp_df, delta_lhp_df, delta_rhp_df):
    try:
        if pitcher_hand == "L":
            recent_df, delta_df = l21_lhp_df, delta_lhp_df
        else:
            recent_df, delta_df = l21_rhp_df, delta_rhp_df

        team_recent = get_recent_team_row(team_name, recent_df)
        team_delta = get_recent_team_row(team_name, delta_df)

        if team_recent is None or team_delta is None:
            raise ValueError("No team data found")

        rec_k = team_recent.get("k_pct", LEAGUE_AVG_TEAM_K_PCT)
        if rec_k > 1.0:  # Normalize if value is percentage
            rec_k /= 100
        delta_k = team_delta.get("k_pct", 0.00)

        trend_mod = 0.98 + 0.25 * (rec_k / LEAGUE_AVG_TEAM_K_PCT) + delta_k
        return np.clip(trend_mod, 0.85, 1.15)

    except Exception as e:
        print(f"[Trend] Using fallback modifier for {team_name} - {str(e)}")
        return 1.05 if pitcher_hand == "L" else 1.02

def get_dynamic_weights(pitcher_hand, pitch_types):
    weights = [0.3, 0.25, 0.25, 0.2, 0.2]
    if len(set(pitch_types)) == 1:
        weights[4] += 0.1
        weights[0] -= 0.05
        weights[2] -= 0.05
    return weights

def calculate_stuff_modifier(pitcher_row: dict, logs: list) -> float:
    """
    Calculate pitcher stuff modifier with improved weighting and dynamic adjustments.
    
    Args:
        pitcher_row: Dictionary containing pitcher stats
        logs: List of recent game logs
        
    Returns:
        Stuff modifier between 0.85 and 1.20
    """
    # Get metrics with safe defaults
    stuff_plus = pitcher_row.get("Stuff+", 100.0)
    k_pct = pitcher_row.get("k_pct", 0.22)
    swstr = pitcher_row.get("SwStr%", 0.105)
    csw = pitcher_row.get("CSW%", 0.27)
    velo = pitcher_row.get("FBv", 92.0)  # Average fastball velocity
    chase = pitcher_row.get("O-Swing%", 0.30)
    z_contact = pitcher_row.get("Z-Contact%", 0.88)
    
    # Calculate component scores with dynamic scaling
    stuff_score = (stuff_plus - 100) / 125  # More conservative scaling than /100
    velo_score = (velo - 92) * 0.008  # +0.8% per mph above 92
    
    # Recent performance adjustment (last 3 games)
    recent_k_rate = np.mean([log.get('strikeouts', 0)/log.get('innings_pitched', 1) 
                           for log in logs[-3:]]) if logs else k_pct
    recent_factor = np.clip(recent_k_rate / k_pct, 0.9, 1.1)
    
    # Calculate metrics with league-average baselines
    k_score = (k_pct - 0.22) * 1.2 * recent_factor
    swstr_score = (swstr - 0.11) * 0.7
    chase_whiff = (chase - 0.28) * 0.5 - (z_contact - 0.87) * 0.5
    
    # Calculate total with improved weighting
    total = (
        stuff_score * 0.35 +  # Increased from 0.3
        velo_score * 0.15 +   # New velocity component
        k_score * 0.8 +       # Reduced from 1.0
        swstr_score * 0.6 +   # Reduced from 0.8
        chase_whiff * 0.4 +   # Reduced from 0.6
        (csw - 0.27) * 0.3    # Added CSW% component
    )
    
    # Apply modifier with narrower bounds
    final_mod = np.clip(1 + total, 0.85, 1.20)  # Was 0.80-1.25
    
    # Diagnostic output
    print("\n[Stuff] Breakdown:")
    print(f"  Stuff+: {stuff_plus:.1f} → {stuff_score:+.3f}")
    print(f"  FB Velo: {velo:.1f} mph → {velo_score:+.3f}")
    print(f"  K%: {k_pct:.3f} (Recent: {recent_k_rate:.3f}) → {k_score:+.3f}")
    print(f"  SwStr%: {swstr:.3f} → {swstr_score:+.3f}")
    print(f"  Chase-Whiff: {chase_whiff:+.3f}")
    print(f"  CSW%: {csw:.3f} → {(csw-0.27)*0.3:+.3f}")
    print(f"  Final Modifier: {final_mod:.3f}")
    
    return final_mod


def calculate_batter_vulnerability_mod(
    batters: List[Dict], 
    pitch_type: str, 
    pitcher_hand: str,
    pitcher_quality: float = 1.0  # 0.8-1.2 scale of pitcher dominance
) -> float:
    """
    Calculate batter vulnerability modifier with improved weighting and adjustments.
    
    Args:
        batters: List of batter dictionaries with stats
        pitch_type: Type of pitch being thrown (Breaking/Fastball/Offspeed)
        pitcher_hand: 'L' or 'R'
        pitcher_quality: Multiplier for pitcher skill (default 1.0)
    
    Returns:
        Vulnerability modifier (0.85-1.15 range)
    """
    if not batters or not isinstance(batters, list):
        return 1.0
    
    modifiers = []
    match_stats = {"matched": 0, "default": 0}
    league_avgs = {
        "Breaking": {"k": 0.25, "woba": 0.320, "whiff": 0.30, "putaway": 0.18},
        "Fastball": {"k": 0.18, "woba": 0.350, "whiff": 0.15, "putaway": 0.12},
        "Offspeed": {"k": 0.22, "woba": 0.330, "whiff": 0.25, "putaway": 0.16}
    }
    
    # Get league averages for this pitch type
    avg = league_avgs.get(pitch_type, league_avgs["Breaking"])
    
    for batter in batters:
        if not isinstance(batter, dict):
            continue
            
        # Get batter handedness with fallback
        batter_hand = batter.get("hand", "R")
        
        # Get pitch-specific stats with league average fallbacks
        k_pct = batter.get("k_percent", avg["k"])
        woba = batter.get("woba", avg["woba"])
        whiff = batter.get("whiff_percent", avg["whiff"])
        putaway = batter.get("put_away", avg["putaway"])
        
        # Track matching stats
        if batter.get("matched", False):
            match_stats["matched"] += 1
        else:
            match_stats["default"] += 1
        
        # Calculate platoon advantage
        platoon_boost = 1.1 if pitcher_hand != batter_hand else 0.95
        
        # Improved vulnerability score with better weighting:
        # 30% K%, 25% whiff%, 15% putaway, 30% wOBA
        vulnerability_score = (
            0.30 * (k_pct - avg["k"]) +      # K% above average
            0.25 * (whiff - avg["whiff"]) +   # Whiff% above average
            0.15 * (putaway - avg["putaway"]) - # Putaway above average
            0.30 * (woba - avg["woba"])       # wOBA below average
        ) * platoon_boost * pitcher_quality
        
        # Convert to modifier with more conservative scaling
        mod = np.clip(1 + vulnerability_score * 1.8, 0.85, 1.15)
        
        # Debug output
        print(f"[Batter] {batter.get('name', 'Unknown')} ({batter_hand}) vs {pitcher_hand}HP | "
              f"K%: {k_pct:.3f} (Lg: {avg['k']:.3f}) | "
              f"wOBA: {woba:.3f} (Lg: {avg['woba']:.3f}) | "
              f"Mod: {mod:.3f}")
        
        modifiers.append(mod)
    
    # Calculate final modifier
    if not modifiers:
        return 1.0
    
    final_mod = float(np.mean(modifiers))
    
    # Match rate reporting
    total = match_stats["matched"] + match_stats["default"]
    if total > 0:
        match_rate = (match_stats["matched"] / total) * 100
        print(f"[Batter] Match Rate: {match_rate:.1f}% | "
              f"Final Vuln Mod: {final_mod:.3f}")
    
    return final_mod
