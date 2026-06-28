import time
from datetime import datetime, timedelta
import pandas as pd
import os
import requests

# Força o caminho ser na mesma pasta do script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "jogos.csv")
MIN_DATE = pd.Timestamp("2026-06-01")

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

def get_espn_matches(current_date, retries=3):
    date_str = current_date.strftime("%Y%m%d")
    url = f"https://site.web.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={date_str}"
    
    for _ in range(retries):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json().get("events", [])
        except Exception as e:
            print(f"[AVISO] Falha ao buscar scoreboard para {date_str}, tentando novamente... ({e})")
            time.sleep(2)
    print(f"[ERRO] Falha definitiva para {date_str}.")
    return []

def get_espn_summary(event_id, retries=3):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={event_id}"
    for _ in range(retries):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"[AVISO] Falha ao buscar summary {event_id}, tentando novamente... ({e})")
            time.sleep(2)
    print(f"[ERRO] Falha definitiva ao buscar summary {event_id}.")
    return {}

def extract_formations(summary):
    home_form = ""
    away_form = ""
    rosters = summary.get("rosters", [])
    if len(rosters) >= 2:
        home_form = rosters[0].get("formation", "")
        away_form = rosters[1].get("formation", "")
    return home_form, away_form

def extract_starters(summary):
    home_starters = []
    away_starters = []
    rosters = summary.get("rosters", [])
    
    if len(rosters) >= 1:
        for p in rosters[0].get("roster", []):
            if p.get("starter", False):
                home_starters.append(p.get("athlete", {}).get("displayName", ""))
                
    if len(rosters) >= 2:
        for p in rosters[1].get("roster", []):
            if p.get("starter", False):
                away_starters.append(p.get("athlete", {}).get("displayName", ""))
                
    return home_starters, away_starters

def extract_events(summary, home_team, away_team):
    subs = []
    gols = []
    assists = []
    
    for ev in summary.get("keyEvents", []):
        type_name = ev.get("type", {}).get("type", "").lower()
        minute = ev.get("clock", {}).get("displayValue", "")
        team_name = ev.get("team", {}).get("displayName", "")
        
        side = "CASA" if team_name == home_team else ("FORA" if team_name == away_team else "DESCONHECIDO")
        
        if "substitution" in type_name or "sub" in type_name:
            participants = ev.get("participants", [])
            player_in = participants[0].get("athlete", {}).get("displayName", "") if len(participants) > 0 else ""
            player_out = participants[1].get("athlete", {}).get("displayName", "") if len(participants) > 1 else ""
            if player_in and player_out:
                subs.append(f"[{side}] {minute} {player_in} entrou no lugar de {player_out}")
            
        elif "goal" in type_name:
            participants = ev.get("participants", [])
            scorer = participants[0].get("athlete", {}).get("displayName", "") if len(participants) > 0 else ""
            if scorer:
                gols.append(f"[{side}] {minute} {scorer}")
            
            if len(participants) > 1:
                assist = participants[1].get("athlete", {}).get("displayName", "")
                if assist:
                    assists.append(f"[{side}] {minute} {assist} -> {scorer}")

    return subs, gols, assists

def main():
    rows = []
    # Começa da data atual
    current_date = datetime.now()
    
    seen_event_ids = set()

    while True:
        print(f"[BUSCA ESPN] {current_date.strftime('%Y-%m-%d')}")
        if pd.Timestamp(current_date.date()) < MIN_DATE:
            break
            
        events = get_espn_matches(current_date)
        
        for event in events:
            competitors = event.get("competitions", [{}])[0].get("competitors", [])
            if len(competitors) < 2:
                continue
                
            home_team = competitors[0].get("team", {}).get("name", "")
            away_team = competitors[1].get("team", {}).get("name", "")
            
            matched_teams = [t for t in TARGET_TEAMS.values() if t.lower() in home_team.lower() or t.lower() in away_team.lower()]
            
            if matched_teams:
                event_id = event["id"]
                if event_id in seen_event_ids:
                    continue
                seen_event_ids.add(event_id)
                
                status_type = event.get("status", {}).get("type", {}).get("name", "")
                if status_type not in ["STATUS_FINAL", "STATUS_FULL_TIME"]:
                    continue # Só pegar jogos que já acabaram
                
                print(f"   [COLETA] {home_team} x {away_team}")
                
                home_score = competitors[0].get("score", "0")
                away_score = competitors[1].get("score", "0")
                resultado = f"{home_score} x {away_score}"
                
                date_str = event.get("date", "")
                if date_str:
                    try:
                        data_jogo = pd.to_datetime(date_str).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        data_jogo = current_date.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    data_jogo = current_date.strftime("%Y-%m-%d %H:%M:%S")
                    
                tournament = event.get("season", {}).get("slug", "fifa.world")
                
                summary = get_espn_summary(event_id)
                
                home_form, away_form = extract_formations(summary)
                home_starters, away_starters = extract_starters(summary)
                subs, gols, assists = extract_events(summary, home_team, away_team)
                
                for team_name in matched_teams:
                    rows.append({
                        "time_referencia": team_name,
                        "competicao": tournament,
                        "pais_competicao": "World",
                        "data_jogo": data_jogo,
                        "time_casa": home_team,
                        "time_fora": away_team,
                        "jogo": f"{home_team} x {away_team}",
                        "resultado": resultado,
                        "formacao_casa": home_form,
                        "formacao_fora": away_form,
                        "titulares_casa": " | ".join(home_starters),
                        "titulares_fora": " | ".join(away_starters),
                        "substituicoes": " | ".join(subs),
                        "gols": " | ".join(gols),
                        "assistencias": " | ".join(assists)
                    })
                    
        current_date = current_date - timedelta(days=1)
        time.sleep(0.5)

    df_new = pd.DataFrame(rows)

    if not df_new.empty:
        df_new["data_jogo"] = pd.to_datetime(df_new["data_jogo"])
        
        if os.path.exists(OUTPUT_FILE):
            df_old = pd.read_csv(OUTPUT_FILE)
            df_old["data_jogo"] = pd.to_datetime(df_old["data_jogo"])
            
            # Combina e remove duplicados usando data e jogo para ter certeza
            df = pd.concat([df_old, df_new], ignore_index=True)
            df = df.drop_duplicates(subset=["data_jogo", "time_casa", "time_fora", "time_referencia"], keep="last")
        else:
            df = df_new

        df = df.sort_values(by="data_jogo", ascending=False)
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

        print(f"\\n======================")
        print(f"Coleta Concluída via ESPN API!")
        print(f"Foram adicionados {len(df_new)} registros novos ou atualizados.")
        print(f"Arquivo {OUTPUT_FILE} atualizado com sucesso.")
        print(f"======================")
    else:
        print(f"\\n======================")
        print(f"Nenhum jogo finalizado encontrado para os times alvo a partir de 01/06/2026.")
        print(f"======================")

if __name__ == "__main__":
    main()
