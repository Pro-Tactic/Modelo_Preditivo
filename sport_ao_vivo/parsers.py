import re

SCORING_TYPES = {"goal", "own-goal", "penalty-goal", "penalty - scored"}
YELLOW_TYPES = {"yellow-card", "yellow card"}
RED_TYPES = {"red-card", "red card", "yellow-red-card"}
SUB_TYPES = {"substitution", "sub"}

NAME_ALIASES = {
    "Machado": "Filipe Machado",
    "Esli Garcia": "Esli García",
    "Pedro": "Pedro Martins",
    "Marcelo": "Marcelo Ajul",
}


def _resolve_name(name):
    if not name:
        return name
    return NAME_ALIASES.get(name, name)


def _event_type(event):
    type_info = event.get("type") or {}
    return (type_info.get("type") or type_info.get("text") or "").lower()


def parse_minute(display, period):
    display = (display or "").strip()
    base = 0
    extra = 0
    match = re.match(r"(\d+)'?(?:\+(\d+))?", display)
    if match:
        base = int(match.group(1))
        extra = int(match.group(2)) if match.group(2) else 0
    minute = base + extra
    period_number = period if isinstance(period, int) else (period or {}).get("number")
    half = "1T" if period_number == 1 else "2T" if period_number == 2 else "OT"
    return minute, half, display or None


def minute_bucket(minute):
    if minute <= 0:
        return "0-15"
    if minute <= 15:
        return "0-15"
    if minute <= 30:
        return "16-30"
    if minute <= 45:
        return "31-45"
    if minute <= 60:
        return "46-60"
    if minute <= 75:
        return "61-75"
    if minute <= 90:
        return "76-90"
    return "90+"


def parse_lineups(summary):
    lineups = {}
    for roster in summary.get("rosters") or []:
        side = roster.get("homeAway")
        team = (roster.get("team") or {}).get("displayName")
        team_id = (roster.get("team") or {}).get("id")
        starters = []
        bench = []
        for player in roster.get("roster") or []:
            name = (player.get("athlete") or {}).get("displayName")
            if not name:
                continue
            name = _resolve_name(name)
            
            # Tenta pegar a posição do jogador para dar contexto à IA
            pos = (player.get("position") or {}).get("abbreviation")
            display_name = f"{name} ({pos})" if pos else name
            
            if player.get("starter"):
                starters.append(display_name)
            else:
                bench.append(display_name)
        lineups[side] = {
            "team": team,
            "team_id": team_id,
            "formation": roster.get("formation"),
            "starters": starters,
            "bench": bench,
        }
    return lineups


def _extract_scorer(text):
    match = re.search(r"\.\s+([^()]+?)\s+\(", text)
    name = match.group(1).strip() if match else text
    return _resolve_name(name)


def _extract_assist(text):
    match = re.search(r"Assisted by ([^.]+?)(?: following| with|\.)", text)
    name = match.group(1).strip() if match else None
    return _resolve_name(name) if name else None


def _extract_card_player(text):
    match = re.match(r"([^()]+?)\s+\(", text)
    name = match.group(1).strip() if match else None
    return _resolve_name(name) if name else None


def _extract_sub(text):
    match = re.search(r"([^.]+?)\s+replaces\s+([^.]+?)(?:\s+because of (.+?))?\.", text)
    if not match:
        return None, None, None
    player_in = match.group(1).strip()
    player_out = match.group(2).strip()
    reason = match.group(3).strip() if match.group(3) else None
    return _resolve_name(player_in), _resolve_name(player_out), reason


def parse_events(summary):
    goals = []
    cards = []
    subs = []
    for event in summary.get("keyEvents") or []:
        etype = _event_type(event)
        text = (event.get("text") or "").strip()
        minute, half, minute_display = parse_minute(
            (event.get("clock") or {}).get("displayValue"), event.get("period")
        )
        team_id = (event.get("team") or {}).get("id")
        if event.get("scoringPlay") or etype in SCORING_TYPES:
            goals.append(
                {
                    "minute": minute,
                    "minute_display": minute_display,
                    "half": half,
                    "bucket": minute_bucket(minute),
                    "team_id": team_id,
                    "scorer": _extract_scorer(text),
                    "assist": _extract_assist(text),
                    "own_goal": "own" in etype,
                    "penalty": "penalty" in etype or "penalty" in text.lower(),
                    "text": text,
                }
            )
        elif etype in SUB_TYPES:
            player_in, player_out, reason = _extract_sub(text)
            subs.append(
                {
                    "minute": minute,
                    "minute_display": minute_display,
                    "half": half,
                    "team_id": team_id,
                    "player_in": player_in,
                    "player_out": player_out,
                    "reason": reason,
                    "text": text,
                }
            )
        elif etype in YELLOW_TYPES or etype in RED_TYPES:
            color = "vermelho" if etype in RED_TYPES else "amarelo"
            cards.append(
                {
                    "minute": minute,
                    "minute_display": minute_display,
                    "half": half,
                    "bucket": minute_bucket(minute),
                    "team_id": team_id,
                    "color": color,
                    "player": _extract_card_player(text),
                    "text": text,
                }
            )
    return {"goals": goals, "cards": cards, "subs": subs}


def parse_team_stats(summary):
    stats = {}
    for team in (summary.get("boxscore") or {}).get("teams") or []:
        team_id = (team.get("team") or {}).get("id")
        values = {}
        for stat in team.get("statistics") or []:
            values[stat.get("name")] = stat.get("displayValue")
        stats[team_id] = values
    return stats


def parse_h2h(summary):
    games = []
    seen = set()
    for block in summary.get("headToHeadGames") or []:
        for event in block.get("events") or []:
            game_id = event.get("id")
            if game_id in seen:
                continue
            seen.add(game_id)
            games.append(
                {
                    "game_id": game_id,
                    "date": event.get("gameDate"),
                    "competition": event.get("competitionName"),
                    "home_team_id": event.get("homeTeamId"),
                    "away_team_id": event.get("awayTeamId"),
                    "home_score": event.get("homeTeamScore"),
                    "away_score": event.get("awayTeamScore"),
                    "result": event.get("gameResult"),
                    "score": event.get("score"),
                }
            )
    return games
