from pathlib import Path
import pandas as pd
import json
import sys
import traceback

# Import required modules
try:
    from k_scraper import StrikeoutScraper
    from models import project_strikeouts
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class StrikeoutOrchestrator:
    def __init__(self):
        print("🎯 Initializing StrikeoutOrchestrator...")
        self.scraper = StrikeoutScraper()
        
        # Team schedule mappings for finding opponents
        self.team_schedule = {
            'NYY': 'BOS', 'BOS': 'NYY',
            'LAD': 'SFG', 'SFG': 'LAD', 
            'HOU': 'TEX', 'TEX': 'HOU',
            'ATL': 'MIA', 'MIA': 'ATL',
            'WSH': 'PHI', 'PHI': 'WSH',
            'KC': 'CWS', 'CWS': 'KC',
            'PIT': 'MIL', 'MIL': 'PIT',
            'NYM': 'CHC', 'CHC': 'NYM',
            'SD': 'COL', 'COL': 'SD',
            'TB': 'BAL', 'BAL': 'TB',
            'SEA': 'LAA', 'LAA': 'SEA',
            'STL': 'CIN', 'CIN': 'STL',
            'MIN': 'DET', 'DET': 'MIN',
            'TOR': 'ARI', 'ARI': 'TOR'
        }
        
        # Park mappings
        self.team_parks = {
            'NYY': 'Yankee Stadium', 'BOS': 'Fenway Park',
            'LAD': 'Dodger Stadium', 'SFG': 'Oracle Park',
            'HOU': 'Minute Maid Park', 'TEX': 'Globe Life Field',
            'ATL': 'Truist Park', 'MIA': 'loanDepot park',
            'WSH': 'Nationals Park', 'PHI': 'Citizens Bank Park',
            'KC': 'Kauffman Stadium', 'CWS': 'Guaranteed Rate Field',
            'PIT': 'PNC Park', 'MIL': 'American Family Field',
            'NYM': 'Citi Field', 'CHC': 'Wrigley Field',
            'SD': 'Petco Park', 'COL': 'Coors Field',
            'TB': 'Tropicana Field', 'BAL': 'Oriole Park',
            'SEA': 'T-Mobile Park', 'LAA': 'Angel Stadium',
            'STL': 'Busch Stadium', 'CIN': 'Great American Ball Park',
            'MIN': 'Target Field', 'DET': 'Comerica Park',
            'TOR': 'Rogers Centre', 'ARI': 'Chase Field'
        }

    def _find_opponent(self, team: str) -> str:
        """Find opponent team for today's games"""
        return self.team_schedule.get(team, 'Unknown')

    def _get_park_for_team(self, team: str) -> str:
        """Get home park for team"""
        return self.team_parks.get(team, 'Unknown Park')

    def _get_projection(self, pitcher: str, opponent_team: str, park: str) -> dict:
        """Get strikeout projection for pitcher"""
        try:
            return project_strikeouts(pitcher, opponent_team, park)
        except Exception as e:
            print(f"❌ Projection error for {pitcher}: {e}")
            return None

    def _calculate_edge(self, prop: dict, projection: dict) -> dict:
        """Calculate betting edge as percentage"""
        if not projection:
            return {'edge': 0, 'recommendation': 'SKIP', 'projected_ks': 0}
        
        line = prop['line']
        projected = projection['mean']
        
        # Calculate percentage difference
        edge_pct = ((projected - line) / line) * 100
        
        # Determine recommendation based on edge
        if edge_pct > 10:  # 10%+ edge
            recommendation = 'OVER'
        elif edge_pct < -10:  # -10%+ edge  
            recommendation = 'UNDER'
        else:
            recommendation = 'PASS'
        
        return {
            'projected_ks': round(projected, 2),
            'edge': round(edge_pct, 2),
            'recommendation': recommendation
        }

    def _precache_pitchers(self, pitcher_names: list):
        """Pre-cache pitcher data"""
        print(f"⚡ Pre-caching {len(pitcher_names)} pitchers...")
        # Assume MLB scraper already ran and cached the data
        pass

    def _save_output(self, projections: list):
        """Save projections to JSON"""
        try:
            with open("projections.json", "w") as f:
                json.dump(projections, f, indent=2)
            print("💾 Saved projections.json")
        except Exception as e:
            print(f"❌ Save error: {e}")

    def _save_simple_csv(self, projections: list):
        """Save beautifully formatted CSV output"""
        try:
            # Create clean DataFrame with better column names
            clean_data = []
            for proj in projections:
                clean_data.append({
                    'Pitcher': proj['pitcher'],
                    'Team': proj['team'],
                    'Strikeout Line': proj['line'],
                    'Projection': round(proj.get('projected_ks', 0), 2),
                    'Edge %': round(proj.get('edge', 0), 2),
                    'Recommendation': proj.get('recommendation', 'PASS')
                })
            
            df = pd.DataFrame(clean_data)
            
            # Sort by Edge % descending (highest edge first)
            df = df.sort_values('Edge %', ascending=False).reset_index(drop=True)
            
            # Save to CSV
            df.to_csv("strikeout_projections.csv", index=False)
            print("💾 Saved strikeout_projections.csv")
            
            return df
            
        except Exception as e:
            print(f"❌ CSV save error: {e}")
            return pd.DataFrame()

    def _show_summary(self, projections: list):
        """Show beautifully formatted betting summary"""
        # Create and sort DataFrame
        clean_data = []
        for proj in projections:
            clean_data.append({
                'Pitcher': proj['pitcher'],
                'Team': proj['team'],
                'Line': proj['line'],
                'Projection': round(proj.get('projected_ks', 0), 2),
                'Edge %': round(proj.get('edge', 0), 2),
                'Recommendation': proj.get('recommendation', 'PASS')
            })
        
        df = pd.DataFrame(clean_data)
        df = df.sort_values('Edge %', ascending=False).reset_index(drop=True)
        
        print(f"\n📊 STRIKEOUT PROJECTIONS SUMMARY:")
        print("=" * 80)
        
        # Display formatted table
        print(f"{'Pitcher':<18} {'Team':<4} {'Line':<4} {'Proj':<4} {'Edge %':<7} {'Rec':<6}")
        print("-" * 80)
        
        for _, row in df.iterrows():
            edge_color = "🔺" if row['Edge %'] > 10 else "🔻" if row['Edge %'] < -10 else "➡️"
            print(f"{row['Pitcher']:<18} {row['Team']:<4} {row['Line']:<4} {row['Projection']:<4} {edge_color}{row['Edge %']:>6.1f}% {row['Recommendation']:<6}")
        
        # Show top recommendations
        print("\n🎯 TOP BETTING OPPORTUNITIES:")
        
        # Best OVER bets (highest positive edge)
        overs = df[df['Edge %'] > 5].head(3)
        if not overs.empty:
            print("\n🔺 BEST OVERS:")
            for _, row in overs.iterrows():
                print(f"   {row['Pitcher']} ({row['Team']}) O{row['Line']} - Proj: {row['Projection']} (+{row['Edge %']:.1f}%)")
        
        # Best UNDER bets (lowest negative edge, but significant)
        unders = df[df['Edge %'] < -5].tail(3)
        if not unders.empty:
            print("\n🔻 BEST UNDERS:")
            for _, row in unders.iterrows():
                print(f"   {row['Pitcher']} ({row['Team']}) U{row['Line']} - Proj: {row['Projection']} ({row['Edge %']:.1f}%)")
        
        print("=" * 80)

    def run(self):
        """End-to-end workflow execution"""
        print("=== STRIKEOUT PIPELINE STARTING ===")
        
        # STEP 1: Get fresh props data (this creates todays_pitcher_teams.json)
        print("\n🎰 Getting strikeout props...")
        try:
            props_df = self.scraper.get_current_props()  # Use your working K scraper
            if props_df.empty:
                print("❌ No props found - check K scraper")
                return
            
            print(f"✅ Found {len(props_df)} props")
            
            # Verify team mappings file was created
            if not Path("todays_pitcher_teams.json").exists():
                print("❌ Team mappings file not created by K scraper")
                return
                
        except Exception as e:
            print(f"❌ Failed to get props: {e}")
            return

        # STEP 2: Pre-cache all pitchers (this will use the team mappings)
        print("\n⚡ Pre-caching pitcher data...")
        pitcher_names = props_df['pitcher'].unique().tolist()
        self._precache_pitchers(pitcher_names)

        # STEP 2.5: Validate cached data has proper hand/team info
        print("\n🔍 Validating cached pitcher data...")
        valid_pitchers = []
        
        for pitcher in pitcher_names:
            try:
                safe_name = pitcher.replace(" ", "_").lower()
                cache_path = Path("cache") / f"{safe_name}_2025.json"
                
                if cache_path.exists():
                    with open(cache_path, "r") as f:
                        data = json.load(f)
                    
                    logs = data.get("logs", [])
                    hand = data.get("hand")
                    team = data.get("team")
                    
                    if logs and hand and team != "UNK":
                        valid_pitchers.append(pitcher)
                        print(f"   ✅ {pitcher}: {len(logs)} games, {hand}-handed, {team}")
                    else:
                        print(f"   ❌ {pitcher}: Missing data (logs={len(logs)}, hand={hand}, team={team})")
                else:
                    print(f"   ❌ {pitcher}: No cache file")
                    
            except Exception as e:
                print(f"   ❌ {pitcher}: Cache error - {e}")

        print(f"\n📊 Valid pitchers: {len(valid_pitchers)}/{len(pitcher_names)}")

        # STEP 3: Process each prop
        projections = []
        for _, prop in props_df.iterrows():
            try:
                pitcher = prop['pitcher']
                pitcher_team = prop['team']  # Get team directly from props DataFrame
                
                # Skip if pitcher doesn't have valid cached data
                if pitcher not in valid_pitchers:
                    print(f"\n⚠️ Skipping {pitcher} - invalid cache data")
                    continue
                
                print(f"\n🔮 Processing {pitcher} ({pitcher_team})...")
                
                opponent_team = self._find_opponent(pitcher_team)
                if opponent_team in ('Unknown', 'UNK'):
                    print(f"⚠️ Could not determine opponent for {pitcher}")
                    continue

                park = self._get_park_for_team(pitcher_team)
                print(f"   {pitcher_team} vs {opponent_team} at {park}")

                # Get projection
                projection = self._get_projection(pitcher, opponent_team, park)
                if not projection:
                    print(f"⚠️ No projection for {pitcher}")
                    continue

                # Calculate edge
                edge_data = self._calculate_edge(prop.to_dict(), projection)
                
                projections.append({
                    **prop.to_dict(),
                    **edge_data,
                    'opponent': opponent_team,
                    'park': park
                })

            except Exception as e:
                print(f"⚠️ Failed processing {prop.get('pitcher', 'Unknown')}: {str(e)[:200]}")
                continue

        # STEP 4: Output results
        if projections:
            print(f"\n✅ Processing complete! Generated {len(projections)} projections")
            self._save_output(projections)
            self._save_simple_csv(projections)
            self._show_summary(projections)
        else:
            print("\n❌ No valid projections generated")


# In orchestrator.py, add validation:
def _validate_projection_data(self, projection):
    if not projection:
        return False
        
    # Check if modifiers are at extreme values
    mods = projection.get('modifiers', {})
    if any(v == 1.25 or v == 0.8 for v in mods.values()):
        print(f"⚠️ Extreme modifier values for {projection['pitcher']}")
        return False
        
    # Check if using too many default batter values
    if projection.get('batter_vuln', 1.15) == 1.15:
        print(f"⚠️ Using default batter values for {projection['pitcher']}")
        return False
        
    return True

# MAIN EXECUTION BLOCK
if __name__ == "__main__":
    print("🚀 Starting orchestrator...")
    
    try:
        orchestrator = StrikeoutOrchestrator()
        orchestrator.run()
        print("\n🎉 Orchestrator complete!")
        
    except Exception as e:
        print(f"💥 FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
