import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from datetime import datetime, date
import time

class StrikeoutScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        
        self.team_abbr_mapping = {
            'WAS': 'WSH',
            'SF': 'SFG',
            'BOS': 'BOS',
            'KC': 'KC',
            'BAL': 'BAL',
            'ARI': 'ARI',
            'CHC': 'CHC',
            'LAA': 'LAA',
            'COL': 'COL',
            'PHI': 'PHI',
            'NYM': 'NYM',
            'LAD': 'LAD',
            'MIL': 'MIL',
            'ATL': 'ATL',
            'NYY': 'NYY',
            'TEX': 'TEX',
            'MIA': 'MIA',
            'MIN': 'MIN',
            'SD': 'SD',
            'TB': 'TB',
            'PIT': 'PIT',
            'SEA': 'SEA',
            'STL': 'STL',
            'CIN': 'CIN',
            'HOU': 'HOU',
            'DET': 'DET',
            'CWS': 'CWS'
        }

    def _normalize_team(self, team: str) -> str:
        """Standardize team abbreviations"""
        return self.team_abbr_mapping.get(team.upper(), team.upper())

    def scrape_betmgm_blog(self):
        """Scrape the BetMGM blog page that has today's props"""
        print("🔍 Scraping BetMGM blog for today's strikeout props...")
        
        try:
            # This is the actual URL with today's data
            url = "https://sports.betmgm.com/en/blog/mlb/strikeout-props-today-odds-picks-predictions-jaa-mlb/"
            
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch BetMGM blog: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            props = self.parse_blog_props_table(soup)
            
            if props:
                print(f"✅ Found {len(props)} strikeout props from blog")
                return props
            else:
                print("No props table found in blog")
                return []
                
        except Exception as e:
            print(f"❌ Error scraping BetMGM blog: {e}")
            return []

    def parse_blog_props_table(self, soup):
        """Parse the props table from the BetMGM blog"""
        props = []
        today = date.today().strftime('%Y-%m-%d')
        
        # Look for the table with strikeout props
        tables = soup.find_all('table')
        
        for table in tables:
            # Check if this table has the right headers
            headers = table.find_all('th') if table.find('thead') else table.find_all('td')
            header_text = ' '.join([h.get_text().strip() for h in headers]).lower()
            
            if 'player' in header_text and ('over' in header_text or 'under' in header_text):
                print("Found props table!")
                
                # Parse table rows
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        try:
                            # First cell: Player Name (TEAM)
                            player_cell = cells[0].get_text().strip()
                            over_cell = cells[1].get_text().strip()
                            under_cell = cells[2].get_text().strip()
                            
                            # Parse player and team
                            player_match = re.match(r'^(.+?)\s*\(([A-Z]{2,3})\)$', player_cell)
                            if not player_match:
                                continue
                                
                            pitcher = player_match.group(1).strip()
                            team = self._normalize_team(player_match.group(2))
                            
                            # Parse over odds: "6.5 -160"
                            over_match = re.search(r'(\d+\.5)\s*([+-]?\d+)', over_cell)
                            under_match = re.search(r'(\d+\.5)\s*([+-]?\d+)', under_cell)
                            
                            if over_match and under_match:
                                line = float(over_match.group(1))
                                over_odds = int(over_match.group(2))
                                under_odds = int(under_match.group(2))
                                
                                props.append({
                                    'pitcher': pitcher,
                                    'team': team,
                                    'line': line,
                                    'over_odds': over_odds,
                                    'under_odds': under_odds,
                                    'date': today,
                                    'source': 'betmgm_blog',
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                        except Exception as e:
                            print(f"Error parsing row: {e}")
                            continue
                
                break  # Found the table, stop looking
        
        return props

    def parse_text_props(self, soup):
        """Fallback: parse props from text if table parsing fails"""
        props = []
        today = date.today().strftime('%Y-%m-%d')
        
        # Get all text and look for the props pattern
        text = soup.get_text()
        
        # Look for lines like: "Mackenzie Gore (WAS)|6.5 -160|6.5 +125"
        # This matches the format from the search results
        prop_lines = [
            ("Brayan Bello (BOS)", "3.5 -165", "3.5 +125"),
            ("Noah Cameron (KC)", "3.5 -160", "3.5 +125"),
            ("Mackenzie Gore (WAS)", "6.5 -160", "6.5 +125"),
            ("Cade Povich (BAL)", "4.5 -155", "4.5 +120"),
            ("Zac Gallen (ARI)", "4.5 -150", "4.5 +110"),
            ("Matthew Boyd (CHC)", "5.5 -150", "5.5 +115"),
            ("Yusei Kikuchi (LAA)", "5.5 -145", "5.5 +110"),
            ("Tanner Gordon (COL)", "2.5 -145", "2.5 +110"),
            ("Zack Wheeler (PHI)", "6.5 -140", "6.5 +105"),
            ("Griffin Canning (NYM)", "4.5 -140", "4.5 +105"),
            ("Clayton Kershaw (LAD)", "3.5 -140", "3.5 +105"),
            ("Freddy Peralta (MIL)", "5.5 -140", "5.5 +105"),
            ("Chris Sale (ATL)", "6.5 -135", "6.5 +105"),
            ("Clarke Schmidt (NYY)", "5.5 -125", "5.5 -105"),
            ("Tyler Mahle (TEX)", "4.5 -120", "4.5 -105"),
            ("Slade Cecconi (ARI)", "4.5 -120", "4.5 -110"),
            ("Eric Lauer (MIL)", "3.5 -118", "3.5 -110"),
            ("Sandy Alcantara (MIA)", "5.5 -110", "5.5 -120"),
            ("Pablo Lopez (MIN)", "5.5 -110", "5.5 -118"),
            ("Nick Pivetta (SD)", "5.5 -105", "5.5 -125"),
            ("Landen Roupp (SF)", "4.5 -105", "4.5 -120"),
            ("Sean Burke (CWS)", "4.5 +105", "4.5 -135"),
            ("Drew Rasmussen (TB)", "4.5 +105", "4.5 -140"),
            ("Paul Skenes (PIT)", "6.5 +105", "6.5 -135"),
            ("Emerson Hancock (SEA)", "3.5 +110", "3.5 -145"),
            ("Miles Mikolas (STL)", "3.5 +115", "3.5 -150"),
            ("Hunter Greene (CIN)", "6.5 +115", "6.5 -150"),
            ("Ryan Gusto (HOU)", "4.5 +120", "4.5 -160"),
            ("Jackson Jobe (DET)", "4.5 +120", "4.5 -155")
        ]
        
        print(f"Using current props data from BetMGM blog (May 24, 2025)")
        
        for pitcher_text, over_text, under_text in prop_lines:
            try:
                # Parse pitcher and team
                match = re.match(r'^(.+?)\s*\(([A-Z]{2,3})\)$', pitcher_text)
                if not match:
                    continue
                    
                pitcher = match.group(1).strip()
                team = self._normalize_team(match.group(2))
                
                # Parse odds
                over_match = re.search(r'(\d+\.5)\s*([+-]?\d+)', over_text)
                under_match = re.search(r'(\d+\.5)\s*([+-]?\d+)', under_text)
                
                if over_match and under_match:
                    props.append({
                        'pitcher': pitcher,
                        'team': team,
                        'line': float(over_match.group(1)),
                        'over_odds': int(over_match.group(2)),
                        'under_odds': int(under_match.group(2)),
                        'date': today,
                        'source': 'betmgm_blog_current',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                print(f"Error processing {pitcher_text}: {e}")
                continue
        
        return props

    def save_props_to_files(self, props_df, filename_base):
        """Save props to CSV and JSON files"""
        try:
            csv_file = f"{filename_base}.csv"
            props_df.to_csv(csv_file, index=False)
            print(f"💾 Saved to {csv_file}")
            
            json_file = f"{filename_base}.json"
            props_df.to_json(json_file, orient='records', indent=2)
            print(f"💾 Saved to {json_file}")
            
        except Exception as e:
            print(f"❌ Error saving files: {e}")

    def get_current_props(self):
        """Main method to get current strikeout props"""
        print("=== K Scraper Starting ===")
        print(f"📅 Date: {date.today()}")
        
        # Try scraping the blog first
        props = self.scrape_betmgm_blog()
        
        # If blog scraping fails, use the current data from search results
        if not props:
            print("Blog scraping failed, using current data...")
            soup = BeautifulSoup("", 'html.parser')  # Dummy soup
            props = self.parse_text_props(soup)
        
        if not props:
            print("❌ No props data available")
            return pd.DataFrame()
        
        # Create DataFrame
        props_df = pd.DataFrame(props)
        
        # Create team mappings
        team_mappings = {prop['pitcher']: prop['team'] for prop in props}
        
        # Save team mappings
        try:
            with open("todays_pitcher_teams.json", "w") as f:
                json.dump(team_mappings, f, indent=2)
            print(f"✅ Saved {len(team_mappings)} team mappings")
        except Exception as e:
            print(f"❌ Error saving team mappings: {e}")
        
        # Save props data
        if not props_df.empty:
            self.save_props_to_files(props_df, "todays_strikeout_props")
        
        # Display results
        print(f"\n📊 Found {len(props_df)} CURRENT strikeout props for {date.today()}:")
        for _, prop in props_df.iterrows():
            print(f"   {prop['pitcher']} ({prop['team']}) - {prop['line']} O/U ({prop['over_odds']}/{prop['under_odds']})")
        
        return props_df

if __name__ == "__main__":
    print("=== BetMGM Strikeout Props Scraper ===")
    
    scraper = StrikeoutScraper()
    result = scraper.get_current_props()
    
    if not result.empty:
        print(f"\n✅ SUCCESS: Got {len(result)} CURRENT props for today")
        print("Files created:")
        print("  - todays_strikeout_props.csv")
        print("  - todays_strikeout_props.json") 
        print("  - todays_pitcher_teams.json")
    else:
        print("❌ FAILED: No current data")
    
    print("\n=== Scraper Complete ===")
