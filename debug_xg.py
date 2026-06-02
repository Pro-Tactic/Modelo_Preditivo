import pandas as pd
from collections import defaultdict
import math
from datetime import datetime
import numpy as np

jogos = pd.read_csv("copa/jogos.csv")
tabela_completa = pd.read_csv("copa/classificacao.csv")
jogos["data_jogo"] = pd.to_datetime(jogos["data_jogo"])

def peso_recencia(data_jogo, fator=0.001):
    dias = (datetime.now() - data_jogo).days
    return math.exp(-fator * max(0, dias))

def parse_resultado(resultado):
    try:
        g1, g2 = resultado.split("x")
        return int(g1.strip()), int(g2.strip())
    except:
        return 0, 0

ranking_selecoes = defaultdict(float)
for _, row in tabela_completa.iterrows():
    if row["jogos"] > 0 and row["liga"] != "Copa do Mundo FIFA 2026":
        liga_str = str(row["liga"]).upper()
        if "CONMEBOL" in liga_str or "COPA AMÉRICA" in liga_str:
            peso_conf = 3.0
        elif "UEFA" in liga_str or "EURO" in liga_str:
            peso_conf = 3.0
        elif "AFRICA" in liga_str or "CAF" in liga_str:
            peso_conf = 1.2
        elif "AFC" in liga_str or "ASIAN" in liga_str:
            peso_conf = 1.0
        elif "CONCACAF" in liga_str or "GOLD CUP" in liga_str:
            peso_conf = 1.0
        elif "OFC" in liga_str or "OCEANIA" in liga_str:
            peso_conf = 0.5
        else:
            peso_conf = 1.0
            
        ppg = (row["pontos"] / row["jogos"]) * peso_conf
        ranking_selecoes[row["time"]] = max(ranking_selecoes.get(row["time"], 0.5), ppg)

def obter_forca_time(time):
    gols_feitos = []
    gols_sofridos = []
    pesos = []
    df_time = jogos[(jogos["time_casa"] == time) | (jogos["time_fora"] == time)]
    if df_time.empty: return 1.0, 1.0 
    for _, row in df_time.iterrows():
        g1, g2 = parse_resultado(row["resultado"])
        peso = peso_recencia(row["data_jogo"])
        adv = row["time_fora"] if row["time_casa"] == time else row["time_casa"]
        ppg_adv = ranking_selecoes.get(adv, 0.5)
        peso_adv = 1.0 + (ppg_adv / 3.0) 
        peso_total = peso * peso_adv
        pesos.append(peso_total)
        if row["time_casa"] == time:
            gols_feitos.append(g1 * peso_total)
            gols_sofridos.append(g2 * peso_total / max(0.5, peso_adv))
        else:
            gols_feitos.append(g2 * peso_total)
            gols_sofridos.append(g1 * peso_total / max(0.5, peso_adv))
    soma_pesos = sum(pesos)
    if soma_pesos > 0:
        ataque = sum(gols_feitos) / soma_pesos
        defesa = sum(gols_sofridos) / soma_pesos
        return max(0.2, ataque), max(0.2, defesa)
    return 1.0, 1.0

forca_ataque_global = {}
forca_defesa_global = {}
for time in ["Brazil", "Haiti", "Croatia", "Ghana", "Cabo Verde", "Uruguay"]:
    atk, df = obter_forca_time(time)
    forca_ataque_global[time] = atk
    forca_defesa_global[time] = df

print("--- RANKINGS ---")
for t in ["Brazil", "Haiti", "Croatia", "Ghana", "Cabo Verde", "Uruguay"]:
    print(f"{t}: Rank={ranking_selecoes.get(t, 0.5):.2f} | Atk={forca_ataque_global[t]:.2f} | Def={forca_defesa_global[t]:.2f}")

print("\n--- XG SIMULATION ---")
def sim_xg(t1, t2):
    rk1 = ranking_selecoes.get(t1, 0.5)
    rk2 = ranking_selecoes.get(t2, 0.5)
    mult_t1 = (max(0.5, rk1) / max(0.5, rk2)) ** 0.6
    mult_t2 = (max(0.5, rk2) / max(0.5, rk1)) ** 0.6
    xg1 = (forca_ataque_global[t1] * forca_defesa_global[t2]) * mult_t1
    xg2 = (forca_ataque_global[t2] * forca_defesa_global[t1]) * mult_t2
    print(f"{t1} vs {t2} -> {t1} xG={xg1:.2f} (mult {mult_t1:.2f}) | {t2} xG={xg2:.2f} (mult {mult_t2:.2f})")


sim_xg("Brazil", "Haiti")
sim_xg("Croatia", "Ghana")
sim_xg("Cabo Verde", "Uruguay")
