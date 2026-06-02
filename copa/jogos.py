from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import pandas as pd

BASE_URL = "https://api.sofascore.com/api/v1"

OUTPUT_FILE = "jogos.csv"

TARGET_TEAMS = {
    4748: "Brazil",
    4819: "Argentina",
    4725: "Uruguay",
    4789: "Paraguay",
    4820: "Colombia",
    4757: "Ecuador",
    4752: "Canada",
    4781: "Mexico",
    4724: "USA",
    5164: "Panama",
    7229: "Haiti",
    55827: "Curaçao",
    4711: "Germany",
    4481: "France",
    4698: "Spain",
    4713: "England",
    4704: "Portugal",
    4705: "Netherlands",
    4717: "Belgium",
    4715: "Croatia",
    4699: "Switzerland",
    4718: "Austria",
    4475: "Norway",
    4688: "Sweden",
    4695: "Scotland",
    4700: "Türkiye",
    4714: "Czechia",
    4479: "Bosnia & Herzegovina",
    4778: "Morocco",
    4758: "Egypt",
    4739: "Senegal",
    4729: "Tunisia",
    4691: "Algeria",
    4764: "Ghana",
    4768: "Côte d'Ivoire",
    4736: "South Africa",
    4753: "Cabo Verde",
    4823: "DR Congo",
    4770: "Japan",
    4735: "South Korea",
    4766: "Iran",
    4834: "Saudi Arabia",
    4741: "Australia",
    4792: "Qatar",
    4767: "Iraq",
    4771: "Jordan",
    4723: "Uzbekistan",
    4784: "New Zealand"
}

MIN_DATE = pd.Timestamp("2023-01-01")

# =========================================
# FETCH JSON
# =========================================

def fetch_json(page, url):

    try:

        return page.evaluate(
            """async (url) => {

                const res = await fetch(url);

                if (!res.ok) return null;

                return await res.json();

            }""",
            url
        )

    except Exception:

        return None

# =========================================
# PEGAR EVENTOS DOS TIMES
# =========================================

def get_target_team_events(page):

    collected = {
        4748: [],
        4819: [],
        4725: [],
        4789: [],
        4820: [],
        4757: [],
        4752: [],
        4781: [],
        4724: [],
        5164: [],
        7229: [],
        55827: [],
        4711: [],
        4481: [],
        4698: [],
        4713: [],
        4704: [],
        4705: [],
        4717: [],
        4715: [],
        4699: [],
        4718: [],
        4475: [],
        4688: [],
        4695: [],
        4700: [],
        4714: [],
        4479: [],
        4778: [],
        4758: [],
        4739: [],
        4729: [],
        4691: [],
        4764: [],
        4768: [],
        4736: [],
        4753: [],
        4823: [],
        4770: [],
        4735: [],
        4766: [],
        4834: [],
        4741: [],
        4792: [],
        4767: [],
        4771: [],
        4723: [],
        4784: []
    }

    seen_event_ids = set()

    current = datetime.now().date()

    while True:

        print(f"[BUSCA] {current}")

        if pd.Timestamp(current) < MIN_DATE:
            break

        url = (
            f"{BASE_URL}/sport/football/"
            f"scheduled-events/{current}"
        )

        data = fetch_json(page, url)

        if data:

            for event in data.get("events", []):

                try:

                    if event["status"]["type"] != "finished":
                        continue

                    event_date = pd.to_datetime(
                        event["startTimestamp"],
                        unit="s"
                    )

                    if event_date < MIN_DATE:
                        continue

                    home_id = event["homeTeam"]["id"]
                    away_id = event["awayTeam"]["id"]

                    for team_id in TARGET_TEAMS.keys():

                        if (
                            home_id == team_id
                            or away_id == team_id
                        ):

                            if event["id"] not in seen_event_ids:

                                collected[team_id].append(
                                    event
                                )

                                seen_event_ids.add(
                                    event["id"]
                                )

                                print(
                                    f"[COLETA] "
                                    f"{TARGET_TEAMS[team_id]} "
                                    f"- "
                                    f"{event['homeTeam']['name']} "
                                    f"x "
                                    f"{event['awayTeam']['name']}"
                                )

                except Exception:
                    continue

        current = current - pd.Timedelta(days=1)

        time.sleep(0.4)

    return collected

# =========================================
# TITULARES
# =========================================

def extract_starters(lineups):

    home_starters = []
    away_starters = []

    home_data = lineups.get("home", {})
    away_data = lineups.get("away", {})

    for p in home_data.get("players", []):

        if not p.get("substitute", False):

            home_starters.append(
                p["player"]["name"]
            )

    for p in away_data.get("players", []):

        if not p.get("substitute", False):

            away_starters.append(
                p["player"]["name"]
            )

    return home_starters, away_starters

# =========================================
# FORMAÇÕES
# =========================================

def extract_formations(lineups):

    home_formation = (
        lineups.get("home", {})
        .get("formation")
    )

    away_formation = (
        lineups.get("away", {})
        .get("formation")
    )

    return home_formation, away_formation

# =========================================
# SUBSTITUIÇÕES
# =========================================

def extract_substitutions(incidents):

    subs = []

    for item in incidents.get("incidents", []):

        if item.get("incidentType") == "substitution":

            team_side = item.get("isHome", False)

            side = (
                "CASA"
                if team_side
                else "FORA"
            )

            minute = item.get("time")

            player_in = (
                item.get("playerIn", {})
                .get("name")
            )

            player_out = (
                item.get("playerOut", {})
                .get("name")
            )

            subs.append(
                f"[{side}] "
                f"{minute}' "
                f"{player_in} entrou "
                f"no lugar de {player_out}"
            )

    return subs

# =========================================
# GOLS + ASSISTÊNCIAS
# =========================================

def extract_goals_assists(incidents):

    gols = []

    assists = []

    for item in incidents.get("incidents", []):

        if item.get("incidentType") == "goal":

            scorer = (
                item.get("player", {})
                .get("name")
            )

            assist = (
                item.get("assist1", {})
                .get("name")
            )

            minute = item.get("time")

            added_time = item.get(
                "addedTime",
                0
            )

            side = (
                "CASA"
                if item.get("isHome", False)
                else "FORA"
            )

            if added_time and added_time > 0:

                minute_str = (
                    f"{minute}+{added_time}'"
                )

            else:

                minute_str = f"{minute}'"

            if scorer:

                gols.append(
                    f"[{side}] "
                    f"{minute_str} "
                    f"{scorer}"
                )

            if assist:

                assists.append(
                    f"[{side}] "
                    f"{minute_str} "
                    f"{assist} -> {scorer}"
                )

    return gols, assists

# =========================================
# MAIN
# =========================================

def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            slow_mo=100
        )

        page = browser.new_page()

        page.goto(
            "https://www.sofascore.com",
            wait_until="networkidle"
        )

        collected_events = get_target_team_events(page)

        rows = []

        for team_id, events in collected_events.items():

            team_name = TARGET_TEAMS[team_id]

            print(
                f"\n[PROCESSANDO] "
                f"{team_name}"
            )

            for i, event in enumerate(events, start=1):

                try:

                    event_id = event["id"]

                    home_team = (
                        event["homeTeam"]["name"]
                    )

                    away_team = (
                        event["awayTeam"]["name"]
                    )

                    tournament = (
                        event.get("tournament", {})
                        .get("name")
                    )

                    country = (
                        event.get("tournament", {})
                        .get("category", {})
                        .get("name")
                    )

                    home_score = (
                        event["homeScore"]["current"]
                    )

                    away_score = (
                        event["awayScore"]["current"]
                    )

                    resultado = (
                        f"{home_score} x "
                        f"{away_score}"
                    )

                    data_jogo = pd.to_datetime(
                        event["startTimestamp"],
                        unit="s"
                    ).strftime("%Y-%m-%d %H:%M")

                    print(
                        f"[{i}/{len(events)}] "
                        f"{home_team} x {away_team}"
                    )

                    # =====================
                    # LINEUPS
                    # =====================

                    lineups_url = (
                        f"{BASE_URL}/event/"
                        f"{event_id}/lineups"
                    )

                    lineups = fetch_json(
                        page,
                        lineups_url
                    )

                    if not lineups:
                        raise Exception(
                            "Lineups não encontrado"
                        )

                    # =====================
                    # INCIDENTES
                    # =====================

                    incidents_url = (
                        f"{BASE_URL}/event/"
                        f"{event_id}/incidents"
                    )

                    incidents = fetch_json(
                        page,
                        incidents_url
                    )

                    if not incidents:

                        incidents = {
                            "incidents": []
                        }

                    # =====================
                    # EXTRAÇÕES
                    # =====================

                    (
                        home_starters,
                        away_starters
                    ) = extract_starters(
                        lineups
                    )

                    (
                        home_formation,
                        away_formation
                    ) = extract_formations(
                        lineups
                    )

                    substituicoes = (
                        extract_substitutions(
                            incidents
                        )
                    )

                    gols, assists = (
                        extract_goals_assists(
                            incidents
                        )
                    )

                    # =====================
                    # ROW
                    # =====================

                    rows.append({

                        "time_referencia":
                            team_name,

                        "competicao":
                            tournament,

                        "pais_competicao":
                            country,

                        "data_jogo":
                            data_jogo,

                        "time_casa":
                            home_team,

                        "time_fora":
                            away_team,

                        "jogo":
                            f"{home_team} x "
                            f"{away_team}",

                        "resultado":
                            resultado,

                        "formacao_casa":
                            home_formation,

                        "formacao_fora":
                            away_formation,

                        "titulares_casa":
                            " | ".join(
                                home_starters
                            ),

                        "titulares_fora":
                            " | ".join(
                                away_starters
                            ),

                        "substituicoes":
                            " | ".join(
                                substituicoes
                            ),

                        "gols":
                            " | ".join(
                                gols
                            ),

                        "assistencias":
                            " | ".join(
                                assists
                            )
                    })

                    time.sleep(1)

                except Exception as e:

                    print(
                        f"[ERRO] "
                        f"Partida {event_id}: {e}"
                    )

                    time.sleep(1.5)

        browser.close()

        # =====================================
        # DATAFRAME
        # =====================================

        df = pd.DataFrame(rows)

        df["data_jogo"] = pd.to_datetime(
            df["data_jogo"]
        )

        df = df.sort_values(
            by="data_jogo",
            ascending=False
        )

        df.to_csv(
            OUTPUT_FILE,
            index=False,
            encoding="utf-8-sig"
        )

        print("\n======================")
        print("CSV salvo com sucesso")
        print(f"Arquivo: {OUTPUT_FILE}")
        print("======================")

if __name__ == "__main__":
    main()