import requests

import config

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "sport-ao-vivo/1.0"})


def _get(url, params=None):
    response = _SESSION.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def get_team_schedule(team_id, season=config.ESPN_SEASON):
    url = f"{config.ESPN_SITE_BASE}/{config.ESPN_LEAGUE}/teams/{team_id}/schedule"
    return _get(url, params={"season": season})


def get_summary(event_id):
    url = f"{config.ESPN_SITE_BASE}/{config.ESPN_LEAGUE}/summary"
    return _get(url, params={"event": event_id})


def get_scoreboard():
    url = f"{config.ESPN_SITE_BASE}/{config.ESPN_LEAGUE}/scoreboard"
    return _get(url)


def get_team_season_statistics(team_id, season=config.ESPN_SEASON):
    url = (
        f"{config.ESPN_CORE_BASE}/{config.ESPN_LEAGUE}/seasons/{season}"
        f"/teams/{team_id}/statistics"
    )
    return _get(url)
