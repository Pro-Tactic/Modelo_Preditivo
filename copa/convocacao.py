from playwright.sync_api import sync_playwright
import pandas as pd

BASE_URL = "https://api.sofascore.com/api/v1"

TEAM_ID = [4748, 4819, 4725, 4789, 4820, 4757, 4752, 4781, 4724, 5164, 7229, 55827, 4711, 4481, 4698, 4713, 4704, 4705, 4717, 4715, 
           4699, 4718, 4475, 4688, 4695, 4700, 4714, 4479, 4778, 4758, 4739, 4729, 4691, 4764, 4768, 4736, 4753, 4823, 4770, 4735, 4766, 
           4834, 4741, 4792, 4767, 4771, 4723, 4784]

OUTPUT_FILE = "convocacao.csv"


# =========================================
# FETCH JSON
# =========================================

def fetch_json(page, url):

    try:

        return page.evaluate(
            """async (url) => {

                const res = await fetch(url);

                if (!res.ok) {
                    return null;
                }

                return await res.json();

            }""",
            url
        )

    except Exception as e:

        print(f"[ERRO FETCH] {e}")

        return None


# =========================================
# PEGAR JOGADORES
# =========================================

def get_players(
    page,
    team_id
):

    url = (
        f"{BASE_URL}/team/"
        f"{team_id}/players"
    )

    print(f"[BUSCANDO] {url}")

    data = fetch_json(
        page,
        url
    )

    if not data:
        return []

    return data.get(
        "players",
        []
    )

TEAM_NAMES = {
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
# =========================================
# MAIN
# =========================================

def main():

    rows = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        page.goto(
            "https://www.sofascore.com",
            wait_until="networkidle"
        )

        for team_id in TEAM_ID:
            players = get_players(
                page,
                team_id
            )

            print(
                f"{len(players)} jogadores encontrados"
            )

            for item in players:

                try:

                    player = item.get(
                        "player",
                        {}
                    )

                    team = item.get(
                        "team",
                        {}
                    )

                    rows.append({
                        "team_id":
                            team_id,

                        "selecao":
                            TEAM_NAMES.get(team_id),

                        "player_id":
                            player.get("id"),

                        "jogador":
                            player.get("name"),

                        "posicao":
                            player.get("position"),

                        "numero":
                            player.get("jerseyNumber"),

                        "altura":
                            player.get("height"),

                        "pe_preferido":
                            player.get("preferredFoot")
                    })

                except Exception as e:

                    print(
                        f"[ERRO] {e}"
                    )

        browser.close()

    if not rows:

        print(
            "Nenhum jogador encontrado"
        )

        return

    df = pd.DataFrame(rows)

    posicao_ordem = {
        "G": 1,          
        "D": 2,  
        "M": 3,  
        "F": 4   
    }

    df["ordem_posicao"] = (
        df["posicao"]
        .map(posicao_ordem)
        .fillna(99)
    )

    df = df.sort_values(
        by=[
            "selecao",
            "ordem_posicao",
            "jogador"
        ]
    )

    df = df.drop(
        columns=["ordem_posicao"]
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