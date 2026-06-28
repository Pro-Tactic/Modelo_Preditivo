import requests
import json
import pandas as pd
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "fase_grupos.csv")

URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings?season=2026"

def get_stat(stats, name):
    for s in stats:
        if s["name"] == name:
            return s["value"]
    return 0

def main():
    print("[BUSCA ESPN] Buscando classificação da Copa do Mundo 2026...")
    try:
        res = requests.get(URL, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"[ERRO] Falha ao conectar na API da ESPN: {e}")
        return

    rows = []
    
    for group in data.get("children", []):
        group_name = group.get("name", "")
        
        entries = group.get("standings", {}).get("entries", [])
        
        for entry in entries:
            team_name = entry.get("team", {}).get("displayName", "")
            stats = entry.get("stats", [])
            
            # Extract stats
            posicao = int(get_stat(stats, "rank"))
            jogos = int(get_stat(stats, "gamesPlayed"))
            vitorias = int(get_stat(stats, "wins"))
            empates = int(get_stat(stats, "ties"))
            derrotas = int(get_stat(stats, "losses"))
            gols_pro = int(get_stat(stats, "pointsFor"))
            gols_contra = int(get_stat(stats, "pointsAgainst"))
            saldo_gols = int(get_stat(stats, "pointDifferential"))
            pontos = int(get_stat(stats, "points"))
            
            rows.append({
                "torneio": "World Cup 2026",
                "grupo": group_name,
                "posicao": posicao,
                "selecao": team_name,
                "jogos": jogos,
                "vitorias": vitorias,
                "empates": empates,
                "derrotas": derrotas,
                "gols_pro": gols_pro,
                "gols_contra": gols_contra,
                "saldo_gols": saldo_gols,
                "pontos": pontos
            })
            
    if not rows:
        print("[AVISO] Nenhuma classificação encontrada.")
        return
        
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    
    print("\n======================")
    print("Classificação salva com sucesso!")
    print(f"Arquivo gerado: {OUTPUT_FILE}")
    print("======================")

if __name__ == "__main__":
    main()
