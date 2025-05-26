import json
import time
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

def get_current_date():
    return datetime.today().strftime("%Y-%m-%d")

def get_current_timestamp():
    return datetime.now().isoformat()

def scrape_lineups():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)

    try:
        print("🚀 Loading page...")
        driver.get("https://www.rotowire.com/baseball/daily-lineups.php")
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        driver.quit()

    lineup_blocks = soup.select("div.lineup:not(.is-tools) div.lineup__main")
    print(f"✅ Found {len(lineup_blocks)} lineup blocks")
    team_lineups = {}

    for block in lineup_blocks:
        lineup_container = block.find_parent("div", class_="lineup")
        team_block = lineup_container.select("div.lineup__abbr")

        for side_index, side in enumerate(["is-visit", "is-home"]):
            team_ul = block.select_one(f"ul.lineup__list.{side}")
            if not team_ul:
                continue

            team_abbr = team_block[side_index].get_text(strip=True) if len(team_block) > side_index else "???"

            players = []
            for player_li in team_ul.select("li.lineup__player"):
                name_tag = player_li.find("a")
                bats_tag = player_li.find("span", class_="lineup__bats")

                name = name_tag.get_text(strip=True) if name_tag else "Unknown"
                bats = bats_tag.get_text(strip=True) if bats_tag else "R"
                players.append({"name": name, "hand": bats})

            team_lineups[team_abbr] = {
                "lineup": players,
                "pitcher": "",  # handled by mlb_scraper.py
                "hand": "R",    # fallback
                "last_updated": get_current_timestamp()
            }

    for team, data in team_lineups.items():
        path = CACHE_DIR / f"{team}_{get_current_date()}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    print(f"✅ Saved {len(team_lineups)} team lineups to cache/")
    return team_lineups


def load_cached_lineup(opponent_abbr: str) -> dict:
    """
    Load the cached lineup JSON for a given team (e.g., 'NYY') on today's date.
    """
    cache_path = CACHE_DIR / f"{opponent_abbr}_{get_current_date()}.json"
    if not cache_path.exists():
        raise FileNotFoundError(f"[!] No cached lineup found for {opponent_abbr} on {get_current_date()}")
    
    with open(cache_path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    scrape_lineups()

# --- Safe fallback fetch function (only used if cache fails) ---
import requests
from bs4 import BeautifulSoup

def fetch_lineup_from_rotowire(opponent_team):
    print(f"[RotoWire] Attempting to fetch lineup for {opponent_team}")
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    response = requests.get(url)
    if not response.ok:
        raise RuntimeError(f"[RotoWire] Failed to fetch lineup page for {opponent_team}")

    soup = BeautifulSoup(response.text, "html.parser")
    containers = soup.find_all("div", class_="lineup")

    for container in containers:
        team_header = container.find("div", class_="lineup__team")
        if team_header and opponent_team.lower() in team_header.text.lower():
            players = container.find_all("div", class_="lineup__player")
            lineup = []
            for player in players:
                name_tag = player.find("a", class_="player-name")
                hand_tag = player.find("span", class_="lineup__bats")
                if name_tag and hand_tag:
                    lineup.append({
                        "name": name_tag.text.strip(),
                        "hand": hand_tag.text.strip()[0]
                    })
            return lineup

    raise ValueError(f"[RotoWire] Could not find lineup for {opponent_team}")
