from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"

# File paths
FINAL_PITCHER_FILE = "FINAL_PITCHER_DATA.csv"
BATTER_STATS_FILE = "filled_batter_stats.csv"
TEAM_TRENDS_LHP_L21 = DATA_DIR / "team_trends_lhp_l21.csv"
TEAM_TRENDS_RHP_L21 = DATA_DIR / "team_trends_rhp_l21.csv"
TEAM_TRENDS_LHP_DELTA = DATA_DIR / "team_trends_lhp_delta.csv"
TEAM_TRENDS_RHP_DELTA = DATA_DIR / "team_trends_rhp_delta.csv"

FRAMING_IMPACT_PER_RUN = 0.039  # 3.9% K rate change per framing run
FRAMING_RUNS_PER_GAME_FACTOR = 1 / 9  # Convert per-9 innings to per-game impact
CATCHER_FRAMING_FILE = DATA_DIR / "catcher-framing-2025.csv"

# Strikeout constants
LEAGUE_AVG_PITCHER_K_PCT = 0.225  # Individual pitcher average
LEAGUE_AVG_TEAM_K_PCT = 0.195     # Team vs pitcher-handedness average
LEAGUE_AVG_K = 6.5


TEAM_ABBREV_MAP = {
    # American League
    'BAL': ['BAL', 'BLT', 'BALT', 'BALTI'],  # Baltimore Orioles
    'BOS': ['BOS', 'BRS', 'BOST', 'REDSX'],  # Boston Red Sox
    'NYY': ['NYY', 'NYA', 'NY', 'YANKS'],    # New York Yankees
    'TBR': ['TBR', 'TBA', 'TB', 'RAYS'],     # Tampa Bay Rays
    'TOR': ['TOR', 'TO', 'BLUEJ', 'JAYS'],   # Toronto Blue Jays
    
    'CWS': ['CWS', 'CHW', 'SOX', 'WHITESOX'], # Chicago White Sox
    'CLE': ['CLE', 'CLV', 'CLI', 'GUARD'],   # Cleveland Guardians
    'DET': ['DET', 'DT', 'TIGERS'],          # Detroit Tigers
    'KCR': ['KCR', 'KC', 'ROYALS'],          # Kansas City Royals
    'MIN': ['MIN', 'MN', 'TWINS'],           # Minnesota Twins
    
    'HOU': ['HOU', 'HST', 'ASTROS'],         # Houston Astros
    'LAA': ['LAA', 'ANA', 'ANGELS'],         # Los Angeles Angels
    'OAK': ['OAK', 'OAS', 'ATHLETICS'],      # Oakland Athletics
    'SEA': ['SEA', 'SE', 'MARINERS'],        # Seattle Mariners
    'TEX': ['TEX', 'TEXA', 'RANGERS'],       # Texas Rangers
    
    # National League
    'ATL': ['ATL', 'AT', 'BRAVES'],          # Atlanta Braves
    'MIA': ['MIA', 'FLA', 'MARLINS'],        # Miami Marlins
    'NYM': ['NYM', 'NYN', 'METS'],           # New York Mets
    'PHI': ['PHI', 'PHIL', 'PHILLIES'],      # Philadelphia Phillies
    'WSN': ['WSN', 'WSH', 'WAS', 'NATS'],    # Washington Nationals
    
    'CHC': ['CHC', 'CHN', 'CUBS'],           # Chicago Cubs
    'CIN': ['CIN', 'REDS'],                  # Cincinnati Reds
    'MIL': ['MIL', 'MLW', 'BREWERS'],        # Milwaukee Brewers
    'PIT': ['PIT', 'PITT', 'PIRATES'],       # Pittsburgh Pirates
    'STL': ['STL', 'SL', 'CARDINALS'],       # St. Louis Cardinals
    
    'ARI': ['ARI', 'AZ', 'DBACKS'],          # Arizona Diamondbacks
    'COL': ['COL', 'CO', 'ROCKIES'],         # Colorado Rockies
    'LAD': ['LAD', 'LA', 'DODGERS'],         # Los Angeles Dodgers
    'SDP': ['SDP', 'SD', 'PADRES'],          # San Diego Padres
    'SFG': ['SFG', 'SF', 'GIANTS'],          # San Francisco Giants
}

# Reverse mapping for lookup
TEAM_ABBREV_REVERSE_MAP = {}
for official, variants in TEAM_ABBREV_MAP.items():
    for variant in variants:
        TEAM_ABBREV_REVERSE_MAP[variant] = official

def normalize_team_abbrev(team_input: str) -> str:
    """
    Normalize any team abbreviation to the official 3-letter code.
    Handles case variations and common alternate abbreviations.
    
    Args:
        team_input: Any team abbreviation or name variation
        
    Returns:
        Official 3-letter team abbreviation or None if not found
    """
    if not team_input:
        return None
        
    # Clean input
    cleaned = str(team_input).strip().upper()
    
    # Direct match first
    if cleaned in TEAM_ABBREV_REVERSE_MAP:
        return TEAM_ABBREV_REVERSE_MAP[cleaned]
    
    # Try removing non-alphas (e.g., "NY-M" -> "NYM")
    alpha_only = ''.join(c for c in cleaned if c.isalpha())
    if alpha_only in TEAM_ABBREV_REVERSE_MAP:
        return TEAM_ABBREV_REVERSE_MAP[alpha_only]
    
    # Try common substitutions
    substitutions = {
        'NYY': ['YANKEES', 'YANKS'],
        'BOS': ['REDSOX', 'RED SOX'],
        'CHC': ['CUBS'],
        'CHW': ['WHITESOX', 'WHITE SOX'],
        # Add more as needed
    }
    
    for official, names in substitutions.items():
        if cleaned in names:
            return official
            
    return None  # No match found


# Stuff+ baseline
LEAGUE_AVG_STUFF = 100

# Comprehensive league averages
LEAGUE_AVG = {
    'k_pct': 0.225,
    'whiff_pct': 0.275,
    'xwoba': 0.315,
    'strikeouts': 6.75,
    'innings_pitched': 5.5
}

# Vulnerability weights
VULN_WEIGHTS = {
    'k_pct': 0.62,
    'whiff_pct': 0.31,
    'xwoba': -0.07
}

# Park effects
PARK_EFFECTS = {
    'Coors Field': 0.95,
    'Great American Ball Park': 1.05,
    'T-Mobile Park': 1.03,
    'Oracle Park': 0.97,
    'Yankee Stadium': 0.98
}

# Platoon matchups
PLATOON_MATCHUPS = {
    ('L', 'L'): 0.93,
    ('L', 'R'): 1.07,
    ('R', 'R'): 0.95,
    ('R', 'L'): 1.05
}

# Pitch categories
PITCH_CATEGORY_MAP = {
    "FF": "Fastball",
    "SL": "Slider",
    "CU": "Curveball",
    "CH": "Changeup",
    "SI": "Sinker",
    "FC": "Cutter",
    "FS": "Splitter"
}

# Park-specific K% modifiers (empirically derived or flat 1.0 fallback)
PARK_FACTORS = {
    "Angel Stadium": 0.980,
    "Busch Stadium": 0.970,
    "Chase Field": 1.030,
    "Citizens Bank Park": 1.020,
    "Citi Field": 1.030,
    "Comerica Park": 0.950,
    "Coors Field": 0.930,
    "Dodger Stadium": 1.000,
    "Fenway Park": 0.960,
    "Globe Life Field": 0.980,
    "Great American Ball Park": 1.070,
    "Guaranteed Rate Field": 1.050,
    "Kauffman Stadium": 0.960,
    "loanDepot Park": 0.970,
    "Minute Maid Park": 1.010,
    "Nationals Park": 1.020,
    "Oakland Coliseum": 0.940,
    "Oracle Park": 1.030,
    "Petco Park": 0.970,
    "PNC Park": 1.000,
    "Progressive Field": 0.990,
    "Rogers Centre": 1.000,
    "T-Mobile Park": 0.980,
    "Target Field": 1.000,
    "Tropicana Field": 0.980,
    "Truist Park": 1.030,
    "Wrigley Field": 1.010,
    "Yankee Stadium": 1.050,
    "American Family Field": 1.020,
    "Oriole Park at Camden Yards": 1.010
}


# Path configuration
DATA_DIR = Path("data")  # Directory where batter stats CSV is stored

# Default batter values by pitch type
DEFAULT_BATTER_STATS = {
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


# Comprehensive Team Mapping System
TEAM_SYSTEM = {
    # Standard 3-letter abbreviations (primary keys)
    'ARI': {
        'full_name': 'Arizona Diamondbacks',
        'alternate_names': ['D-backs', 'Dbacks', 'Diamondbacks', 'Arizona'],
        'park': 'Chase Field',
        'city': 'Phoenix',
        'league': 'NL',
        'division': 'West'
    },
    'ATL': {
        'full_name': 'Atlanta Braves',
        'alternate_names': ['Braves'],
        'park': 'Truist Park',
        'city': 'Atlanta',
        'league': 'NL',
        'division': 'East'
    },
    'BAL': {
        'full_name': 'Baltimore Orioles',
        'alternate_names': ['O\'s', 'Os', 'Orioles', 'Baltimore'],
        'park': 'Oriole Park at Camden Yards',
        'city': 'Baltimore',
        'league': 'AL',
        'division': 'East'
    },
    'BOS': {
        'full_name': 'Boston Red Sox',
        'alternate_names': ['Red Sox', 'BoSox', 'Boston'],
        'park': 'Fenway Park',
        'city': 'Boston',
        'league': 'AL',
        'division': 'East'
    },
    'CHC': {
        'full_name': 'Chicago Cubs',
        'alternate_names': ['Cubs', 'Chicago NL'],
        'park': 'Wrigley Field',
        'city': 'Chicago',
        'league': 'NL',
        'division': 'Central'
    },
    'CWS': {
        'full_name': 'Chicago White Sox',
        'alternate_names': ['White Sox', 'Pale Hose', 'Chicago AL'],
        'park': 'Guaranteed Rate Field',
        'city': 'Chicago',
        'league': 'AL',
        'division': 'Central'
    },
    'CIN': {
        'full_name': 'Cincinnati Reds',
        'alternate_names': ['Reds', 'Redlegs', 'Cincinnati'],
        'park': 'Great American Ball Park',
        'city': 'Cincinnati',
        'league': 'NL',
        'division': 'Central'
    },
    'CLE': {
        'full_name': 'Cleveland Guardians',
        'alternate_names': ['Guardians', 'Indians', 'Tribe', 'Cleveland'],
        'park': 'Progressive Field',
        'city': 'Cleveland',
        'league': 'AL',
        'division': 'Central'
    },
    'COL': {
        'full_name': 'Colorado Rockies',
        'alternate_names': ['Rockies', 'Colorado'],
        'park': 'Coors Field',
        'city': 'Denver',
        'league': 'NL',
        'division': 'West'
    },
    'DET': {
        'full_name': 'Detroit Tigers',
        'alternate_names': ['Tigers', 'Detroit'],
        'park': 'Comerica Park',
        'city': 'Detroit',
        'league': 'AL',
        'division': 'Central'
    },
    'HOU': {
        'full_name': 'Houston Astros',
        'alternate_names': ['Astros', 'Stros', 'Houston'],
        'park': 'Minute Maid Park',
        'city': 'Houston',
        'league': 'AL',
        'division': 'West'
    },
    'KC': {
        'full_name': 'Kansas City Royals',
        'alternate_names': ['Royals', 'KC', 'Kansas City'],
        'park': 'Kauffman Stadium',
        'city': 'Kansas City',
        'league': 'AL',
        'division': 'Central'
    },
    'LAA': {
        'full_name': 'Los Angeles Angels',
        'alternate_names': ['Angels', 'Halos', 'LA Angels', 'Anaheim Angels'],
        'park': 'Angel Stadium',
        'city': 'Anaheim',
        'league': 'AL',
        'division': 'West'
    },
    'LAD': {
        'full_name': 'Los Angeles Dodgers',
        'alternate_names': ['Dodgers', 'LA', 'Los Angeles'],
        'park': 'Dodger Stadium',
        'city': 'Los Angeles',
        'league': 'NL',
        'division': 'West'
    },
    'MIA': {
        'full_name': 'Miami Marlins',
        'alternate_names': ['Marlins', 'Florida Marlins', 'Miami'],
        'park': 'LoanDepot Park',
        'city': 'Miami',
        'league': 'NL',
        'division': 'East'
    },
    'MIL': {
        'full_name': 'Milwaukee Brewers',
        'alternate_names': ['Brewers', 'Brew Crew', 'Milwaukee'],
        'park': 'American Family Field',
        'city': 'Milwaukee',
        'league': 'NL',
        'division': 'Central'
    },
    'MIN': {
        'full_name': 'Minnesota Twins',
        'alternate_names': ['Twins', 'Minnesota'],
        'park': 'Target Field',
        'city': 'Minneapolis',
        'league': 'AL',
        'division': 'Central'
    },
    'NYM': {
        'full_name': 'New York Mets',
        'alternate_names': ['Mets', 'New York NL'],
        'park': 'Citi Field',
        'city': 'New York',
        'league': 'NL',
        'division': 'East'
    },
    'NYY': {
        'full_name': 'New York Yankees',
        'alternate_names': ['Yankees', 'Yanks', 'Bronx Bombers', 'New York AL'],
        'park': 'Yankee Stadium',
        'city': 'New York',
        'league': 'AL',
        'division': 'East'
    },
    'OAK': {
        'full_name': 'Oakland Athletics',
        'alternate_names': ['Athletics', 'A\'s', 'As', 'Oakland'],
        'park': 'Oakland Coliseum',
        'city': 'Oakland',
        'league': 'AL',
        'division': 'West'
    },
    'PHI': {
        'full_name': 'Philadelphia Phillies',
        'alternate_names': ['Phillies', 'Phils', 'Philadelphia'],
        'park': 'Citizens Bank Park',
        'city': 'Philadelphia',
        'league': 'NL',
        'division': 'East'
    },
    'PIT': {
        'full_name': 'Pittsburgh Pirates',
        'alternate_names': ['Pirates', 'Bucs', 'Pittsburgh'],
        'park': 'PNC Park',
        'city': 'Pittsburgh',
        'league': 'NL',
        'division': 'Central'
    },
    'SD': {
        'full_name': 'San Diego Padres',
        'alternate_names': ['Padres', 'Friars', 'San Diego'],
        'park': 'Petco Park',
        'city': 'San Diego',
        'league': 'NL',
        'division': 'West'
    },
    'SF': {
        'full_name': 'San Francisco Giants',
        'alternate_names': ['Giants', 'SF', 'San Francisco'],
        'park': 'Oracle Park',
        'city': 'San Francisco',
        'league': 'NL',
        'division': 'West'
    },
    'SEA': {
        'full_name': 'Seattle Mariners',
        'alternate_names': ['Mariners', 'M\'s', 'Ms', 'Seattle'],
        'park': 'T-Mobile Park',
        'city': 'Seattle',
        'league': 'AL',
        'division': 'West'
    },
    'STL': {
        'full_name': 'St. Louis Cardinals',
        'alternate_names': ['Cardinals', 'Cards', 'Redbirds', 'St. Louis'],
        'park': 'Busch Stadium',
        'city': 'St. Louis',
        'league': 'NL',
        'division': 'Central'
    },
    'TB': {
        'full_name': 'Tampa Bay Rays',
        'alternate_names': ['Rays', 'Devil Rays', 'Tampa', 'Tampa Bay'],
        'park': 'Tropicana Field',
        'city': 'St. Petersburg',
        'league': 'AL',
        'division': 'East'
    },
    'TEX': {
        'full_name': 'Texas Rangers',
        'alternate_names': ['Rangers', 'Texas'],
        'park': 'Globe Life Field',
        'city': 'Arlington',
        'league': 'AL',
        'division': 'West'
    },
    'TOR': {
        'full_name': 'Toronto Blue Jays',
        'alternate_names': ['Blue Jays', 'Jays', 'Toronto'],
        'park': 'Rogers Centre',
        'city': 'Toronto',
        'league': 'AL',
        'division': 'East'
    },
    'WSH': {
        'full_name': 'Washington Nationals',
        'alternate_names': ['Nationals', 'Nats', 'Washington', 'Expos'],
        'park': 'Nationals Park',
        'city': 'Washington',
        'league': 'NL',
        'division': 'East'
    }
}

# Helper mappings for quick lookups
TEAM_ABBR_MAPPING = {abbr: abbr for abbr in TEAM_SYSTEM}
TEAM_NAME_TO_ABBR = {}
TEAM_TO_PARK = {}

# Build reverse mappings
for abbr, data in TEAM_SYSTEM.items():
    TEAM_NAME_TO_ABBR[data['full_name'].lower()] = abbr
    TEAM_TO_PARK[abbr] = data['park']
    
    for name in data['alternate_names']:
        TEAM_NAME_TO_ABBR[name.lower()] = abbr

# Special cases (common abbreviations)
TEAM_ABBR_MAPPING.update({
    'WAS': 'WSH',  # Washington
    'SF': 'SFG',   # San Francisco
    'LA': 'LAD',   # Los Angeles Dodgers
    'ANA': 'LAA',  # Anaheim/Los Angeles Angels
    'FLA': 'MIA'   # Florida Marlins (historical)
})

# Cache setup
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


CATCHER_FRAMING_DICT = {
    "Jonah Heim": 0.00,
    "Logan O'Hoppe": -0.33,
    "Francisco Alvarez": -0.22,
    "Connor Wong": 0.11,
    "Korey Lee": 0.00,
    "Jose Trevino": 0.00,
    "Henry Davis": -0.11,
    "Salvador Perez": 0.11,
    "Keibert Ruiz": -0.44,
    "Sean Murphy": 0.00,
    "Kyle Higashioka": 0.11,
    "Cal Raleigh": 0.22,
    "Patrick Bailey": 0.44,
    "Yainer Diaz": -0.22,
    "Gabriel Moreno": 0.33
}
