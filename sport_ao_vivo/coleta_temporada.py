import csv
import json
import os
import sys
import time

import config
import espn_api
import parsers

CSV_FIELDS = [
    "time_referencia",
    "competicao",
    "event_id",
    "data_jogo",
    "status",
    "time_casa",
    "time_fora",
    "resultado",
    "formacao_casa",
    "formacao_fora",
    "titulares_casa",
    "titulares_fora",
    "substituicoes",
    "gols",
    "assistencias",
    "cartoes",
    "posse_casa",
    "posse_fora",
    "finalizacoes_casa",
    "finalizacoes_fora",
]

FINISHED_STATUSES = {"STATUS_FULL_TIME", "STATUS_FINAL"}


def _competitor(competition, home_away):
    for competitor in competition.get("competitors") or []:
        if competitor.get("homeAway") == home_away:
            return competitor
    return {}


def _score(competitor):
    score = competitor.get("score")
    if isinstance(score, dict):
        return score.get("displayValue") or score.get("value")
    return score


def _side_of(team_id, home_id, away_id):
    if team_id == home_id:
        return "casa"
    if team_id == away_id:
        return "fora"
    return None


def build_match_record(reference_team_name, event):
    competition = (event.get("competitions") or [{}])[0]
    home = _competitor(competition, "home")
    away = _competitor(competition, "away")
    home_id = (home.get("team") or {}).get("id")
    away_id = (away.get("team") or {}).get("id")
    status = ((competition.get("status") or {}).get("type") or {}).get("name")

    summary = espn_api.get_summary(event["id"])
    lineups = parsers.parse_lineups(summary)
    events = parsers.parse_events(summary)
    stats = parsers.parse_team_stats(summary)

    for collection in events.values():
        for item in collection:
            item["side"] = _side_of(item.get("team_id"), home_id, away_id)

    home_line = lineups.get("home", {})
    away_line = lineups.get("away", {})

    return {
        "time_referencia": reference_team_name,
        "competicao": f"Serie B {config.ESPN_SEASON}",
        "event_id": event["id"],
        "data_jogo": event.get("date"),
        "status": status,
        "casa": {
            "team_id": home_id,
            "nome": (home.get("team") or {}).get("displayName"),
            "gols": _score(home),
            "mando": "casa",
            "formacao": home_line.get("formation"),
            "titulares": home_line.get("starters") or [],
            "reservas": home_line.get("bench") or [],
            "estatisticas": stats.get(home_id, {}),
        },
        "fora": {
            "team_id": away_id,
            "nome": (away.get("team") or {}).get("displayName"),
            "gols": _score(away),
            "mando": "fora",
            "formacao": away_line.get("formation"),
            "titulares": away_line.get("starters") or [],
            "reservas": away_line.get("bench") or [],
            "estatisticas": stats.get(away_id, {}),
        },
        "gols": events["goals"],
        "cartoes": events["cards"],
        "substituicoes": events["subs"],
    }


def record_to_csv_row(record):
    home = record["casa"]
    away = record["fora"]
    home_id = home["team_id"]
    away_id = away["team_id"]

    def goals_for(team_id):
        return "; ".join(
            f"{g['minute_display'] or g['minute']} {g['scorer']}"
            for g in record["gols"]
            if g["team_id"] == team_id
        )

    def assists_for(team_id):
        return "; ".join(
            g["assist"] for g in record["gols"] if g["team_id"] == team_id and g["assist"]
        )

    return {
        "time_referencia": record["time_referencia"],
        "competicao": record["competicao"],
        "event_id": record["event_id"],
        "data_jogo": record["data_jogo"],
        "status": record["status"],
        "time_casa": home["nome"],
        "time_fora": away["nome"],
        "resultado": f"{home['gols']} x {away['gols']}",
        "formacao_casa": home["formacao"],
        "formacao_fora": away["formacao"],
        "titulares_casa": ", ".join(home["titulares"]),
        "titulares_fora": ", ".join(away["titulares"]),
        "substituicoes": "; ".join(
            f"{s['minute_display'] or s['minute']} {s['text']}" for s in record["substituicoes"]
        ),
        "gols": f"CASA[{goals_for(home_id)}] FORA[{goals_for(away_id)}]",
        "assistencias": f"CASA[{assists_for(home_id)}] FORA[{assists_for(away_id)}]",
        "cartoes": "; ".join(
            f"{c['minute_display'] or c['minute']} [{c['color']}] {c['text']}"
            for c in record["cartoes"]
        ),
        "posse_casa": home["estatisticas"].get("possessionPct"),
        "posse_fora": away["estatisticas"].get("possessionPct"),
        "finalizacoes_casa": home["estatisticas"].get("totalShots"),
        "finalizacoes_fora": away["estatisticas"].get("totalShots"),
    }


def collect_team(reference_team_name, team_id, only_finished=True, limit=None):
    schedule = espn_api.get_team_schedule(team_id)
    events = schedule.get("events") or []
    records = []
    for event in events:
        competition = (event.get("competitions") or [{}])[0]
        status = ((competition.get("status") or {}).get("type") or {}).get("name")
        if only_finished and status not in FINISHED_STATUSES:
            continue
        try:
            records.append(build_match_record(reference_team_name, event))
        except Exception as error:
            print(f"  ! falha no evento {event.get('id')}: {error}")
        if limit and len(records) >= limit:
            break
        time.sleep(0.4)
    return records


def write_csv(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(record_to_csv_row(record))


def run(limit=None):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    outputs = {
        "Goias": os.path.join(config.DATA_DIR, "goias_temporada.csv"),
        "Sport": os.path.join(config.DATA_DIR, "sport_temporada.csv"),
    }
    structured = {}
    for name, team_id in config.TEAMS.items():
        print(f"Coletando temporada de {name} (id {team_id}) ...")
        records = collect_team(name, team_id, limit=limit)
        write_csv(outputs[name], records)
        structured[name] = records
        print(f"  -> {len(records)} jogos salvos em {outputs[name]}")

    structured_path = os.path.join(config.DATA_DIR, "jogos_estruturado.json")
    with open(structured_path, "w", encoding="utf-8") as handle:
        json.dump(structured, handle, ensure_ascii=False, indent=2)
    print(f"  -> estrutura completa salva em {structured_path}")


if __name__ == "__main__":
    parsed_limit = None
    if len(sys.argv) > 1 and sys.argv[1].startswith("--limit="):
        parsed_limit = int(sys.argv[1].split("=", 1)[1])
    run(limit=parsed_limit)
