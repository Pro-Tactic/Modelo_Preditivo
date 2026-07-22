import json
import os
import sys
import time
from datetime import datetime, timezone

import config
import espn_api
import parsers

STATE_PATH = os.path.join(config.DATA_DIR, "partida_ao_vivo.json")
LOG_PATH = os.path.join(config.OUTPUTS_DIR, "insights_log.jsonl")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def find_target_event(scoreboard):
    for event in scoreboard.get("events") or []:
        slug = (event.get("shortName") or event.get("name") or "").lower()
        competitors = (event.get("competitions") or [{}])[0].get("competitors") or []
        ids = {(c.get("team") or {}).get("id") for c in competitors}
        if {config.TEAM_ID_GOIAS, config.TEAM_ID_SPORT}.issubset(ids):
            return event
        if all(keyword in slug for keyword in config.MATCH_SLUG_KEYWORDS):
            return event
    return None


def build_state(event):
    competition = (event.get("competitions") or [{}])[0]
    status = competition.get("status") or {}
    status_type = status.get("type") or {}
    home = next((c for c in competition.get("competitors") or [] if c.get("homeAway") == "home"), {})
    away = next((c for c in competition.get("competitors") or [] if c.get("homeAway") == "away"), {})

    summary = espn_api.get_summary(event["id"])
    events = parsers.parse_events(summary)
    lineups = parsers.parse_lineups(summary)

    return {
        "event_id": event["id"],
        "updated_at": _now_iso(),
        "status": status_type.get("name"),
        "status_detail": status_type.get("detail"),
        "clock": status.get("displayClock"),
        "period": status.get("period"),
        "placar": {
            "casa": {"time": (home.get("team") or {}).get("displayName"), "gols": home.get("score")},
            "fora": {"time": (away.get("team") or {}).get("displayName"), "gols": away.get("score")},
        },
        "formacoes": {
            "casa": lineups.get("home", {}).get("formation"),
            "fora": lineups.get("away", {}).get("formation"),
        },
        "eventos": {
            "gols": events["goals"],
            "cartoes": events["cards"],
            "substituicoes": events["subs"],
        },
    }


def _event_signature(kind, item):
    return f"{kind}:{item.get('minute')}:{item.get('text')}"


def diff_new_events(previous, current):
    def signatures(state):
        found = set()
        if not state:
            return found
        eventos = state.get("eventos", {})
        for kind in ("gols", "cartoes", "substituicoes"):
            for item in eventos.get(kind, []):
                found.add(_event_signature(kind, item))
        return found

    old = signatures(previous)
    new_events = []
    eventos = current.get("eventos", {})
    for kind in ("gols", "cartoes", "substituicoes"):
        for item in eventos.get(kind, []):
            signature = _event_signature(kind, item)
            if signature not in old:
                new_events.append({"tipo": kind, **item})
    return new_events


def load_state():
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)


def log_event(new_event):
    os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
    record = {"logged_at": _now_iso(), **new_event}
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_once(event_id=None):
    previous = load_state()
    if event_id:
        event = {"id": event_id, "competitions": [{}]}
        current = build_state(event)
    else:
        scoreboard = espn_api.get_scoreboard()
        event = find_target_event(scoreboard)
        if not event:
            print(f"[{_now_iso()}] Partida Goias x Sport ainda nao encontrada no scoreboard.")
            return previous
        current = build_state(event)

    new_events = diff_new_events(previous, current)
    save_state(current)

    placar = current["placar"]
    print(
        f"[{current['clock'] or '--'}] {placar['casa']['time']} {placar['casa']['gols']}"
        f" x {placar['fora']['gols']} {placar['fora']['time']} ({current['status']})"
    )
    for new_event in new_events:
        print(f"  >> NOVO EVENTO [{new_event['tipo']}] {new_event.get('minute')} - {new_event.get('text')}")
        log_event(new_event)

    return current


def run_loop():
    print(f"Monitor ao vivo iniciado. Intervalo: {config.POLL_INTERVAL_SECONDS}s. Ctrl+C para parar.")
    while True:
        try:
            state = process_once()
            if state and state.get("status") in {"STATUS_FULL_TIME", "STATUS_FINAL"}:
                print("Partida encerrada. Encerrando monitor.")
                break
        except Exception as error:
            print(f"[{_now_iso()}] Falha no ciclo: {error}")
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        process_once()
    elif len(sys.argv) > 1 and sys.argv[1].startswith("--simulate="):
        process_once(event_id=sys.argv[1].split("=", 1)[1])
    else:
        run_loop()
