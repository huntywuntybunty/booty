import numpy as np
import pandas as pd
from typing import Optional, Dict
import traceback
from difflib import get_close_matches
from constants import PARK_FACTORS, LEAGUE_AVG_TEAM_K_PCT

def calculate_ewma(values: list, alpha: float = 0.25) -> float:
    if not values:
        return 5.0
    weights = np.exp(-alpha * np.arange(len(values))[::-1])
    weights /= weights.sum()
    return float(np.dot(weights, values))

def get_column_name(df: pd.DataFrame, possible_names: list) -> Optional[str]:
    for name in possible_names:
        if name in df.columns:
            return name
    return None

def get_recent_team_row(team_name: str, df: pd.DataFrame) -> Optional[Dict]:
    try:
        if df.empty:
            return None
        team_col = get_column_name(df, ['Team', 'team', 'Tm', 'tm', 'TEAM'])
        if not team_col:
            return None
        team_name = str(team_name).strip().upper()
        df['_temp_team'] = df[team_col].astype(str).str.strip().str.upper()
        row = df[df['_temp_team'] == team_name]
        if not row.empty:
            return row.iloc[0].to_dict()
        candidates = df['_temp_team'].unique().tolist()
        close_matches = get_close_matches(team_name, candidates, n=1, cutoff=0.8)
        if close_matches:
            return df[df['_temp_team'] == close_matches[0]].iloc[0].to_dict()
        return None
    except Exception as e:
        print(f"⚠️ Team row lookup error: {str(e)}")
        return None
    finally:
        if '_temp_team' in df.columns:
            df.drop('_temp_team', axis=1, inplace=True)

def scale_ip_mean(
    base_ip: float,
    opponent: str,
    hand: str,
    park: str,
    l21_lhp: pd.DataFrame,
    l21_rhp: pd.DataFrame,
    delta_lhp: pd.DataFrame,
    delta_rhp: pd.DataFrame
) -> float:
    try:
        print(f"\n⚖️ Scaling IP for {opponent} at {park} ({hand}HP)")
        print(f"Initial IP: {base_ip:.2f}")

        recent_df = l21_lhp if hand == "L" else l21_rhp
        delta_df = delta_lhp if hand == "L" else delta_rhp

        recent_data = get_recent_team_row(opponent, recent_df)
        delta_data = get_recent_team_row(opponent, delta_df)

        ip_factor = 1.0

        # Park factor
        park_factor = PARK_FACTORS.get(park, 1.0)
        ip_factor *= park_factor
        print(f"Park Factor: {park_factor:.3f}")

        # K% scaling
        if recent_data:
            k_pct = recent_data.get("k_pct", recent_data.get("K%", LEAGUE_AVG_TEAM_K_PCT))
            if k_pct > 1.0:
                k_pct /= 100
            k_factor = (k_pct / LEAGUE_AVG_TEAM_K_PCT) ** 0.5
            ip_factor *= k_factor
            print(f"K% Factor: {k_factor:.3f} (Team K%: {k_pct:.3f})")
        else:
            print("⚠️ No recent team data available")

        # wRC+ delta scaling
        if delta_data:
            wrc_delta = delta_data.get("wRC+", delta_data.get("wrc_plus", 0))
            wrc_factor = (100 / (100 + wrc_delta)) ** 0.3
            ip_factor *= wrc_factor
            print(f"wRC+ Factor: {wrc_factor:.3f} (ΔwRC+: {wrc_delta:+.1f})")
        else:
            print("⚠️ No delta team data available")

        # Final adjustment
        scaled_ip = base_ip * np.clip(ip_factor, 0.8, 1.2)
        print(f"Final IP: {scaled_ip:.2f} (Total Factor: {ip_factor:.3f})")
        return scaled_ip

    except Exception as e:
        print(f"⚠️ IP scaling failed: {str(e)}")
        traceback.print_exc()
        return min(max(base_ip, 4.0), 6.5)  # Fallback logic
