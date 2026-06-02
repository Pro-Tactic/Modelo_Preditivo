from playwright.sync_api import sync_playwright
import pandas as pd
import time

BASE_URL = "https://api.sofascore.com/api/v1"

OUTPUT_FILE = "classificacao.csv"
KNOCKOUT_FILE = "mata_mata.csv"

LEAGUES = [
    {
        "liga": "Africa Cup of Nations",
        "tournament_id": 270
    },
    {
        "liga": "World Cup Qual. CAF",
        "tournament_id": 308
    },
    {
        "liga": "World Cup Qual. CONMEBOL",
        "tournament_id": 295
    },
    {
        "liga": "Copa América",
        "tournament_id": 133
    },
    {
        "liga": "OFC Men's Nations Cup",
        "tournament_id": 22716
    },
    {
        "liga": "World Cup Qual. OFC",
        "tournament_id": 309
    },
    {
        "liga": "EURO",
        "tournament_id": 1
    },
    {
        "liga": "World Cup Qual. UEFA",
        "tournament_id": 11
    },
    {
        "liga": "CONCACAF Gold Cup",
        "tournament_id": 140
    },
    {
        "liga": "World Cup Qual. CONCACAF",
        "tournament_id": 14
    },
    {
        "liga": "World Cup Qual. AFC",
        "tournament_id": 308
    },
    {
        "liga": "AFC Asian Cup",
        "tournament_id": 246
    },
    {
        "liga": "UEFA Nations League",
        "tournament_id": 10783
    },
    {
        "liga": "CONCACAF Nations League",
        "tournament_id": 14100
    },
    {
        "liga": "Copa do Mundo FIFA 2026",
        "tournament_id": 16
    }
]


def get_events(
    page,
    tournament_id,
    season_id
):

    endpoints = [

        f"{BASE_URL}/unique-tournament/{tournament_id}/season/{season_id}/events",

        f"{BASE_URL}/unique-tournament/{tournament_id}/season/{season_id}/events/last/0"

    ]

    for url in endpoints:

        data = fetch_json(page, url)

        if data and data.get("events"):

            return data["events"]

    return []


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
# PEGAR TEMPORADA MAIS RECENTE
# =========================================

def get_latest_season_id(
    page,
    tournament_id
):

    url = (
        f"{BASE_URL}/unique-tournament/"
        f"{tournament_id}/seasons"
    )

    data = fetch_json(page, url)

    if not data:
        return None

    seasons = data.get(
        "seasons",
        []
    )

    if not seasons:
        return None

    # pega temporada mais recente
    latest = seasons[0]

    return latest["id"]

# =========================================
# PEGAR CLASSIFICAÇÃO
# =========================================

def get_standings(
    page,
    tournament_id,
    season_id
):

    url = (
        f"{BASE_URL}/unique-tournament/"
        f"{tournament_id}/season/"
        f"{season_id}/standings/total"
    )

    print(url)

    data = fetch_json(page, url)

    if not data:
        return []

    standings = data.get(
        "standings",
        []
    )

    if not standings:
        return []

    all_rows = []

    for standing in standings:

        group_name = standing.get(
            "name",
            "Tabela Geral"
        )

        rows = standing.get(
            "rows",
            []
        )

        for row in rows:

            row["group_name"] = group_name

            all_rows.append(row)

    return all_rows

# =========================================
# MAIN
# =========================================

def main():

    rows = []
    knockout_rows = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        page.goto(
            "https://www.sofascore.com",
            wait_until="networkidle"
        )

        for league in LEAGUES:

            league_name = league["liga"]

            tournament_id = (
                league["tournament_id"]
            )

            print(
                f"\n[BUSCANDO] "
                f"{league_name}"
            )

            # pega season automaticamente
            season_id = get_latest_season_id(
                page,
                tournament_id
            )

            print(
                f"Season ID: {season_id}"
            )

            if not season_id:
                continue

            standings = get_standings(
                page,
                tournament_id,
                season_id
            )

            events = get_events(
                page,
                tournament_id,
                season_id
            )

            print(
                f"{len(standings)} times encontrados"
            )

            for team in standings:

                try:

                    rows.append({

                        "liga":
                            league_name,

                        "grupo":
                            team.get(
                                "group_name",
                                "Geral"
                            ),

                        "posicao":
                            team.get("position"),

                        "time":
                            team["team"]["name"],

                        "jogos":
                            team.get("matches"),

                        "vitorias":
                            team.get("wins"),

                        "empates":
                            team.get("draws"),

                        "derrotas":
                            team.get("losses"),

                        "gols_pro":
                            team.get("scoresFor"),

                        "gols_contra":
                            team.get("scoresAgainst"),

                        "saldo":
                            team.get("scoreDiff"),

                        "pontos":
                            team.get("points")

                    })

                except Exception as e:

                    print(
                        f"[ERRO] {e}"
                    )

            for event in events:
                try:

                    round_info = (
                        event.get("roundInfo")
                        or
                        event.get("tournamentRound")
                        or
                        {}
                    )

                    phase = (
                        round_info.get("name")
                        or
                        round_info.get("round")
                        or
                        "Desconhecida"
                    )

                    phase_lower = str(phase).lower()

                    knockout_keywords = [

                        "quarter",
                        "semi",
                        "final",
                        "playoff",
                        "round of 16",
                        "eighth",
                        "knockout",
                        "elimination"

                    ]

                    if not any(
                        keyword in phase_lower
                        for keyword in knockout_keywords
                    ):
                        continue

                    home = (
                        event.get("homeTeam", {})
                        .get("name")
                    )

                    away = (
                        event.get("awayTeam", {})
                        .get("name")
                    )

                    home_score = (
                        event.get("homeScore", {})
                        .get("current")
                    )

                    away_score = (
                        event.get("awayScore", {})
                        .get("current")
                    )

                    winner = ""

                    winner_code = event.get("winnerCode")

                    if winner_code == 1:
                        winner = home

                    elif winner_code == 2:
                        winner = away

                    knockout_rows.append({

                        "liga": league_name,

                        "fase": phase,

                        "mandante": home,

                        "visitante": away,

                        "gols_mandante": home_score,

                        "gols_visitante": away_score,

                        "placar":
                            f"{home_score}-{away_score}",

                        "classificado": winner

                    })

                except Exception as e:

                    print(
                        f"[ERRO MATA-MATA] {e}"
                    )

            time.sleep(1)

        browser.close()

    if len(rows) == 0:

        print(
            "\nNenhuma tabela encontrada"
        )

        return

    df = pd.DataFrame(rows)

    df = df.sort_values(
        by=[
            "liga",
            "grupo",
            "posicao"
        ]
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    if len(knockout_rows):

        knockout_df = pd.DataFrame(
            knockout_rows
        )

        knockout_df.to_csv(

            KNOCKOUT_FILE,

            index=False,

            encoding="utf-8-sig"

        )

        print(
            f"Arquivo: {KNOCKOUT_FILE}"
        )

    print("\n======================")
    print("CSV salvo com sucesso")
    print(f"Arquivo: {OUTPUT_FILE}")
    print("======================")

if __name__ == "__main__":
    main()