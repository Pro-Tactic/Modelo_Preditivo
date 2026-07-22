import os

ESPN_LEAGUE = "bra.2"
ESPN_SEASON = 2026

ESPN_SITE_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_CORE_BASE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues"

TEAMS = {
    "Goias": "3395",
    "Sport": "7635",
}

TEAM_ID_GOIAS = TEAMS["Goias"]
TEAM_ID_SPORT = TEAMS["Sport"]

MATCH_SLUG_KEYWORDS = ("goias", "sport")

POLL_INTERVAL_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 25

THESPORTSDB_TEAM_GOIAS = None
THESPORTSDB_TEAM_SPORT = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

MATCH_EVENT_ID = "401860248"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
FINAL_OUTPUT_DIR = os.path.join(BASE_DIR, "final-output")
