import os

from dotenv import load_dotenv

load_dotenv()

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

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

MATCH_EVENT_ID = "401860248"

TIME_ANALISE = "Sport"
TECNICO_ANALISE = "Gilmar Dal Pozzo"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
FINAL_OUTPUT_DIR = os.path.join(BASE_DIR, "final-output")

STATE_PATH = os.path.join(DATA_DIR, "partida_ao_vivo.json")
EVENTS_LOG_PATH = os.path.join(OUTPUTS_DIR, "insights_log.jsonl")
INSIGHTS_LOG_PATH = os.path.join(OUTPUTS_DIR, "insights_ia.jsonl")
PREJOGO_REPORT_PATH = os.path.join(OUTPUTS_DIR, "relatorio_prejogo.md")
