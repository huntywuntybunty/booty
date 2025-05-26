import numpy as np
import pandas as pd
import json
import re
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from difflib import get_close_matches
from scipy.stats import poisson
from stats_logic import calculate_ewma, scale_ip_mean
from constants import (
    LEAGUE_AVG_PITCHER_K_PCT,
    LEAGUE_AVG_TEAM_K_PCT,
    LEAGUE_AVG_K,
    DATA_DIR,
    CACHE_DIR,
    FINAL_PITCHER_FILE,
    BATTER_STATS_FILE,
    TEAM_TRENDS_LHP_L21,
    TEAM_TRENDS_RHP_L21,
    TEAM_TRENDS_LHP_DELTA,
    TEAM_TRENDS_RHP_DELTA,
)
from preprocessor import (
    clean_name,
    parse_ip,
    get_batter_stats,
    preprocess_batter_from_lineup
)
from lineup_scraper import load_cached_lineup
from simulator import simulate_ks
from modifiers import (
    calculate_catcher_framing_modifier,
    get_park_modifier,
    get_platoon_modifier,
    calculate_team_trend_modifier,
    calculate_stuff_modifier,
    get_dynamic_weights,
    calculate_batter_vulnerability_mod,
)

vs_lhh_df = pd.read_csv("vs_LHH.csv")
vs_rhh_df = pd.read_csv("vs_RHH.csv")
PITCHER_DF = pd.read_csv(DATA_DIR / FINAL_PITCHER_FILE)

def get_column_name(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
    """Find the correct column name from a list of possibilities"""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

def load_normalized_trend_df(path: Path) -> pd.DataFrame:
    """Load and normalize trend data columns"""
    df = pd.read_csv(path)
    df.columns = (
        df.columns.str.lower()
        .str.replace("%", "pct")
        .str.replace("+", "plus")
        .str.strip()
    )
    return df

def get_recent_ks_and_ip(pitcher_name: str) -> Tuple[List[float], List[float], str, str, List[Dict]]:
    """Get recent strikeouts and innings pitched from cache"""
    safe_name = pitcher_name.replace(" ", "_").lower()
    cache_path = CACHE_DIR / f"{safe_name}_2025.json"
    
    if not cache_path.exists():
        raise FileNotFoundError(f"No cache file found for {pitcher_name}. Run MLB scraper first.")

    with open(cache_path, "r") as f:
        data = json.load(f)

    logs = data.get("logs", [])
    ks = [log.get("strikeouts", 0) for log in logs]
    ip = [parse_ip(log.get("innings_pitched", 0)) for log in logs]
    
    hand = data.get("hand", "R")
    team = data.get("team", "UNK")
    
    print(f"[✅] Loaded {pitcher_name}: {len(logs)} games, {hand}-handed, plays for {team}")
    
    return ks, ip, hand, team, logs

def get_putaway_pitch(pitcher_name: str, pitcher_df: pd.DataFrame, opponent_lineup: List[Dict]) -> str:
    """Determine pitcher's best putaway pitch based on lineup handedness"""
    name_col = get_column_name(pitcher_df, ['Name', 'name', 'pitcher_name', 'player_name'])
    if not name_col:
        print(f"[⚠️] No name column found in pitcher DataFrame, using default SL")
        return "SL"
    
    row = pitcher_df[pitcher_df[name_col].str.strip().str.lower() == pitcher_name.lower()]
    if row.empty:
        print(f"[⚠️] {pitcher_name} not found in pitcher DataFrame, using default SL")
        return "SL"

    row = row.iloc[0]
    n_left = sum(1 for b in opponent_lineup if b.get("hand", "R") == "L")
    n_right = len(opponent_lineup) - n_left

    lhb_col = get_column_name(pitcher_df, ['Putaway vs LHB', 'putaway_vs_lhb', 'LHB_putaway'])
    rhb_col = get_column_name(pitcher_df, ['Putaway vs RHB', 'putaway_vs_rhb', 'RHB_putaway'])
    
    if lhb_col and rhb_col:
        putaway = row[lhb_col] if n_left > n_right else row[rhb_col]
    else:
        print(f"[⚠️] Putaway pitch columns not found, using default SL")
        putaway = "SL"
    
    print(f"[🎯] {pitcher_name} putaway pitch: {putaway} (vs {n_left}L/{n_right}R)")
    return putaway

def project_strikeouts(pitcher_name: str, opponent_team: str, park: str) -> Optional[Dict]:
    """Main projection function with complete error handling"""
    print(f"\n🧠 Projecting {pitcher_name} vs {opponent_team} at {park}...")

    try:
        ks_logs, ip_logs, pitcher_hand, pitcher_team, logs = get_recent_ks_and_ip(pitcher_name)
    except FileNotFoundError as e:
        print(f"[❌] {e}")
        return None

    framing_mod = calculate_catcher_framing_modifier(pitcher_team)
    print(f"✅ Pulled logs for {pitcher_name}: {len(ks_logs)} starts, {pitcher_hand}-handed")

    try:
        lineup_data = load_cached_lineup(opponent_team)
        print(f"✅ Loaded cached lineup for {opponent_team}")
    except Exception as e:
        print(f"[❌] Failed to load cached lineup for {opponent_team}: {e}")
        return None

    pitcher_df = pd.read_csv(DATA_DIR / FINAL_PITCHER_FILE)
    print(f"📂 Pitcher file loaded: {pitcher_df.shape}")

    raw_lineup = lineup_data.get("lineup", [])
    opponent_lineup = [preprocess_batter_from_lineup(b) for b in raw_lineup if isinstance(b, dict)]

    if not opponent_lineup:
        print("[❌] No valid batters found in lineup")
        return None

    print(f"[✅] Processed {len(opponent_lineup)} batters from lineup")
    team_lookup_name = opponent_team.strip()
    print(f"📛 Team lookup key: {team_lookup_name}")

    # Load appropriate trend data
    if pitcher_hand == "L":
        trend_df = pd.read_csv(TEAM_TRENDS_LHP_L21)
    else:
        trend_df = pd.read_csv(TEAM_TRENDS_RHP_L21)

    try:
        team_k_pct = trend_df[trend_df['Team'] == opponent_team]['K%'].values[0]
        if pd.isna(team_k_pct):
            raise ValueError("K% is NaN")
        print(f"✅ Found trend data for {opponent_team}")
    except (IndexError, ValueError):
        print(f"[❌] No valid trend data for {opponent_team}, using league average.")
        print(f"[DEBUG] Available teams: {sorted(trend_df['Team'].unique())}")
        team_k_pct = LEAGUE_AVG_TEAM_K_PCT

    print(f"\n🔍 Matchup Modifier Components:")
    print(f" Team K%: {team_k_pct*100:.1f}% | League: {LEAGUE_AVG_TEAM_K_PCT*100}%")

    # Calculate all modifiers
    matchup_mod = np.clip(0.9 + 0.2 * (team_k_pct / LEAGUE_AVG_TEAM_K_PCT), 0.85, 1.15)
    platoon_mod = np.mean([get_platoon_modifier(pitcher_hand, b.get("hand", "R")) for b in opponent_lineup])
    park_mod = get_park_modifier(park)

    l21_lhp_df = load_normalized_trend_df(TEAM_TRENDS_LHP_L21)
    l21_rhp_df = load_normalized_trend_df(TEAM_TRENDS_RHP_L21)
    delta_lhp_df = load_normalized_trend_df(TEAM_TRENDS_LHP_DELTA)
    delta_rhp_df = load_normalized_trend_df(TEAM_TRENDS_RHP_DELTA)

    team_trend_mod = calculate_team_trend_modifier(
        team_lookup_name,
        pitcher_hand,
        l21_lhp_df,
        l21_rhp_df,
        delta_lhp_df,
        delta_rhp_df,
    )

    # Find pitcher in DataFrame
    name_col = get_column_name(pitcher_df, ['Name', 'name', 'pitcher_name', 'player_name'])
    if not name_col:
        print(f"[❌] No name column found in pitcher DataFrame")
        return None

    # Try exact match (case-insensitive, trimmed)
    pitcher_rows = pitcher_df[pitcher_df[name_col].astype(str).str.strip().str.lower() == pitcher_name.lower()]

    if pitcher_rows.empty:
        print(f"[⚠️] No exact match for '{pitcher_name}'. Trying fuzzy match...")
        candidates = pitcher_df[name_col].astype(str).str.strip().str.lower().tolist()
        close_matches = get_close_matches(pitcher_name.lower(), candidates, n=3, cutoff=0.6)

        for match in close_matches:
            match_rows = pitcher_df[pitcher_df[name_col].astype(str).str.strip().str.lower() == match]
            if not match_rows.empty:
                pitcher_rows = match_rows
                print(f"[✅] Fuzzy matched to: {match}")
                break

        if pitcher_rows.empty:
            print(f"[❌] No fuzzy match found for '{pitcher_name}'")
            return None

    pitcher_row = pitcher_rows.iloc[0]
    print(f"[✅] Found pitcher: {pitcher_row[name_col]}")

    # Calculate modifier components
    putaway_pitch = get_putaway_pitch(pitcher_name, pitcher_df, opponent_lineup)
    stuff_mod = calculate_stuff_modifier(pitcher_row, logs)
    weights = get_dynamic_weights(pitcher_hand, [putaway_pitch])
    print(f"⚙️ Modifier Weights: {weights}")

    base_ks = calculate_ewma(ks_logs) if ks_logs else LEAGUE_AVG_K
    base_ip = calculate_ewma(ip_logs) if ip_logs else 5.0
    
    try:
        scaled_ip = scale_ip_mean(
            base_ip,
            opponent_team,
            pitcher_hand,
            park,
            l21_lhp_df,
            l21_rhp_df,
            delta_lhp_df,
            delta_rhp_df
        )
    except Exception as e:
        print(f"[⚠️] IP scaling failed, using base IP: {str(e)}")
        scaled_ip = base_ip

    dispersion = np.std(ks_logs[-5:]) if len(ks_logs) >= 5 else 1.0
    batter_vuln_mod = calculate_batter_vulnerability_mod(opponent_lineup, putaway_pitch, pitcher_hand)

    # Calculate total modifier
    total_mod = 1.0 + sum([
        (matchup_mod - 1) * weights[0],
        (platoon_mod - 1) * weights[1],
        (park_mod - 1) * weights[2],
        (team_trend_mod - 1) * weights[3],
        (batter_vuln_mod - 1) * weights[4],
    ])
    total_mod = np.clip(total_mod * stuff_mod * framing_mod, 0.85, 1.15)

    # Final calculations
    adjusted_mean = base_ks * total_mod
    samples = simulate_ks(adjusted_mean, dispersion, scaled_ip)

    print("\n🧪 Modifier Breakdown:")
    print(f"matchup_mod: {matchup_mod:.3f}")
    print(f"platoon_mod: {platoon_mod:.3f}")
    print(f"park_mod: {park_mod:.3f}")
    print(f"team_mod: {team_trend_mod:.3f}")
    print(f"stuff_mod: {stuff_mod:.3f}")
    print(f"batter_vuln_mod: {batter_vuln_mod:.3f}")
    print(f"framing_mod: {framing_mod:.3f}")
    print(f"weights: {weights}")
    print(f"total_mod: {total_mod:.3f}")
    print(f"adjusted_mean: {adjusted_mean:.2f}")

    return {
        "pitcher": pitcher_name,
        "mean": round(adjusted_mean, 2),
        "ip_ewma": round(base_ip, 2),
        "distribution": {
            "25th": np.percentile(samples, 25),
            "50th": np.percentile(samples, 50),
            "75th": np.percentile(samples, 75),
            "95th": np.percentile(samples, 95)
        },
        "prob_over_5.5": round(np.mean(samples > 5.5) * 100, 2),
        "prob_over_6.5": round(np.mean(samples > 6.5) * 100, 2),
        "prob_over_7.5": round(np.mean(samples > 7.5) * 100, 2)
    }
