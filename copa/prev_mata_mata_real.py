import pandas as pd
import numpy as np
from collections import defaultdict
import mlflow
import os
import sys
import json

# Adicionar diretório do script ao path para importar motor_simulacao
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import motor_simulacao

# =========================================================
# CONFIGURAÇÕES
# =========================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    SIMULACOES = config_data.get("SIMULACOES", 50000)
except FileNotFoundError:
    print(f"Aviso: config.json não encontrado. Usando 50000 simulações.")
    SIMULACOES = 50000

# =========================================================
# BASELINE DE GOLS/ASSISTS DA FASE DE GRUPOS (DADOS REAIS)
# =========================================================
artilheiros_base = {}
assistentes_base = {}

try:
    df_art_base = pd.read_csv(os.path.join(SCRIPT_DIR, "outputs", "artilheiros_fase_grupos.csv"))
    for _, row in df_art_base.iterrows():
        artilheiros_base[row["Jogador"]] = row["Gols"]
    print(f"[OK] Baseline de artilheiros carregado: {len(artilheiros_base)} jogadores")
except FileNotFoundError:
    print("[AVISO] artilheiros_fase_grupos.csv não encontrado. Rodando sem baseline de gols.")

try:
    df_ass_base = pd.read_csv(os.path.join(SCRIPT_DIR, "outputs", "assistentes_fase_grupos.csv"))
    for _, row in df_ass_base.iterrows():
        assistentes_base[row["Jogador"]] = row["Assistencias"]
    print(f"[OK] Baseline de assistentes carregado: {len(assistentes_base)} jogadores")
except FileNotFoundError:
    print("[AVISO] assistentes_fase_grupos.csv não encontrado. Rodando sem baseline de assists.")

# =========================================================
# CHAVEAMENTO FIXO REAL - COPA DO MUNDO 2026
# =========================================================
# 16 jogos da primeira fase do mata-mata
# Pares adjacentes se encontram nas oitavas:
#   Jogo 1 vs Jogo 2 → Oitavas 1
#   Jogo 3 vs Jogo 4 → Oitavas 2  (etc.)
R1_MATCHES = [
    ("South Africa",  "Canada"),             # J1  → Oitavas 1
    ("Netherlands",   "Morocco"),            # J2  → Oitavas 1
    ("Germany",       "Paraguay"),           # J3  → Oitavas 2
    ("France",        "Sweden"),             # J4  → Oitavas 2
    ("Brazil",        "Japan"),              # J5  → Oitavas 3
    ("Ivory Coast",   "Norway"),             # J6  → Oitavas 3
    ("Mexico",        "Ecuador"),            # J7  → Oitavas 4
    ("England",       "Congo DR"),           # J8  → Oitavas 4
    ("Portugal",      "Croatia"),            # J9  → Oitavas 5
    ("Spain",         "Austria"),            # J10 → Oitavas 5
    ("United States", "Bosnia-Herzegovina"), # J11 → Oitavas 6
    ("Belgium",       "Senegal"),            # J12 → Oitavas 6
    ("Argentina",     "Cape Verde"),         # J13 → Oitavas 7
    ("Australia",     "Egypt"),              # J14 → Oitavas 7
    ("Switzerland",   "Algeria"),            # J15 → Oitavas 8
    ("Colombia",      "Ghana"),              # J16 → Oitavas 8
]

# Quartas: Q1=O1xO2, Q2=O5xO6, Q3=O3xO4, Q4=O7xO8
# (índices nos oitavas_winners: 0,1,4,5,2,3,6,7)
QUARTAS_IDX = [
    (0, 1),  # Q1: W(Oitavas1) x W(Oitavas2)  → [Africa do Sul/Canada vs NL/Marrocos] vs [Alemanha/Paraguai vs Franca/Suecia]
    (4, 5),  # Q2: W(Oitavas5) x W(Oitavas6)  → [Portugal/Croacia vs Espanha/Austria] vs [EUA/Bosnia vs Belgica/Senegal]
    (2, 3),  # Q3: W(Oitavas3) x W(Oitavas4)  → [Brasil/Japao vs C.Marfim/Noruega] vs [Mexico/Equador vs Inglaterra/Congo DR]
    (6, 7),  # Q4: W(Oitavas7) x W(Oitavas8)  → [Argentina/Cabo Verde vs Australia/Egito] vs [Suica/Argelia vs Colombia/Gana]
]

# Semis: S1=Q1xQ2, S2=Q3xQ4
SEMIS_IDX = [
    (0, 1),  # S1: W(Q1) x W(Q2)
    (2, 3),  # S2: W(Q3) x W(Q4)
]

TIMES_MATA_MATA = sorted(set(t for pair in R1_MATCHES for t in pair))

# =========================================================
# FUNÇÃO AUXILIAR: SIMULAR CONFRONTO DE MATA-MATA
# =========================================================
def simular_confronto(t1, t2, art_sim, ass_sim):
    """Simula jogo eliminatório completo (90 min → prorrog → pênaltis).
    Registra artilheiros e assistentes. Retorna vencedor."""
    g1, g2 = motor_simulacao.simular_jogo(t1, t2)
    
    for _ in range(g1):
        art = motor_simulacao.sortear_jogador_evento(t1, "gol")
        ass = motor_simulacao.sortear_jogador_evento(t1, "assistencia")
        art_sim[f"{art} ({t1})"] += 1
        if art != ass:
            ass_sim[f"{ass} ({t1})"] += 1
    
    for _ in range(g2):
        art = motor_simulacao.sortear_jogador_evento(t2, "gol")
        ass = motor_simulacao.sortear_jogador_evento(t2, "assistencia")
        art_sim[f"{art} ({t2})"] += 1
        if art != ass:
            ass_sim[f"{ass} ({t2})"] += 1
    
    if g1 > g2:
        return t1
    elif g2 > g1:
        return t2
    
    # Prorrogação (30 min extras)
    gp1, gp2 = motor_simulacao.simular_prorrogacao(t1, t2)
    
    for _ in range(gp1):
        art = motor_simulacao.sortear_jogador_evento(t1, "gol")
        art_sim[f"{art} ({t1})"] += 1
        if np.random.random() < 0.75:
            ass = motor_simulacao.sortear_jogador_evento(t1, "assistencia")
            if art != ass:
                ass_sim[f"{ass} ({t1})"] += 1
    
    for _ in range(gp2):
        art = motor_simulacao.sortear_jogador_evento(t2, "gol")
        art_sim[f"{art} ({t2})"] += 1
        if np.random.random() < 0.75:
            ass = motor_simulacao.sortear_jogador_evento(t2, "assistencia")
            if art != ass:
                ass_sim[f"{ass} ({t2})"] += 1
    
    if gp1 > gp2:
        return t1
    elif gp2 > gp1:
        return t2
    
    # Pênaltis (morte súbita após 5 cobranças)
    return motor_simulacao.simular_penaltis(t1, t2)


# =========================================================
# MOTOR PRINCIPAL - MONTE CARLO
# =========================================================
if __name__ == "__main__":
    print(f"{'='*68}")
    print(f"  [COPA 2026]  PREVISAO MATA-MATA | COPA DO MUNDO 2026")
    print(f"  {SIMULACOES:,} simulacoes Monte Carlo")
    print(f"  Peso fase de grupos: 2.00 (maximo)")
    print(f"{'='*68}\n")
    
    mlflow.set_tracking_uri("sqlite:///mlruns.db")
    mlflow.set_experiment("Previsao_Mata_Mata_Real_Copa2026")
    
    # Contadores por fase
    resultados = {
        time: {"r1": 0, "oitavas": 0, "quartas": 0, "semi": 0, "final": 0, "campeao": 0}
        for time in TIMES_MATA_MATA
    }
    
    # Artilheiros e assistentes acumulados das simulações do mata-mata
    artilheiros_acum = defaultdict(int)
    assistentes_acum = defaultdict(int)
    
    # Placares mais prováveis dos R1 matches (top 3 por confronto)
    placares_r1 = defaultdict(lambda: defaultdict(int))
    
    with mlflow.start_run():
        mlflow.log_param("simulacoes", SIMULACOES)
        mlflow.log_param("peso_group_stage", 2.00)
        mlflow.log_param("times_no_bracket", len(TIMES_MATA_MATA))
        
        for sim in range(SIMULACOES):
            if sim % 10000 == 0 and sim > 0:
                print(f"  [{sim:,}/{SIMULACOES:,}] simulações concluídas...")
            
            motor_simulacao.reset_estado_markov()
            art_sim = defaultdict(int)
            ass_sim = defaultdict(int)
            
            # ── ROUND 1: 16 jogos fixos ───────────────────────────────
            r1_winners = []
            for i, (t1, t2) in enumerate(R1_MATCHES):
                g1, g2 = motor_simulacao.simular_jogo(t1, t2)
                
                # Registrar artilheiros/assists
                for _ in range(g1):
                    art = motor_simulacao.sortear_jogador_evento(t1, "gol")
                    ass = motor_simulacao.sortear_jogador_evento(t1, "assistencia")
                    art_sim[f"{art} ({t1})"] += 1
                    if art != ass:
                        ass_sim[f"{ass} ({t1})"] += 1
                for _ in range(g2):
                    art = motor_simulacao.sortear_jogador_evento(t2, "gol")
                    ass = motor_simulacao.sortear_jogador_evento(t2, "assistencia")
                    art_sim[f"{art} ({t2})"] += 1
                    if art != ass:
                        ass_sim[f"{ass} ({t2})"] += 1
                
                # Placares R1
                placares_r1[f"{t1} x {t2}"][f"{g1}x{g2}"] += 1
                
                if g1 > g2:
                    venc = t1
                elif g2 > g1:
                    venc = t2
                else:
                    gp1, gp2 = motor_simulacao.simular_prorrogacao(t1, t2)
                    if gp1 > gp2:
                        venc = t1
                    elif gp2 > gp1:
                        venc = t2
                    else:
                        venc = motor_simulacao.simular_penaltis(t1, t2)
                
                r1_winners.append(venc)
                resultados[venc]["r1"] += 1
            
            # ── OITAVAS: 8 jogos (pares adjacentes de r1_winners) ─────
            oitavas_winners = []
            for i in range(0, 16, 2):
                venc = simular_confronto(r1_winners[i], r1_winners[i+1], art_sim, ass_sim)
                oitavas_winners.append(venc)
                resultados[venc]["oitavas"] += 1
            
            # ── QUARTAS: 4 jogos com chaveamento real ─────────────────
            qf_winners = []
            for (ia, ib) in QUARTAS_IDX:
                venc = simular_confronto(oitavas_winners[ia], oitavas_winners[ib], art_sim, ass_sim)
                qf_winners.append(venc)
                resultados[venc]["quartas"] += 1
            
            # ── SEMIS: 2 jogos ─────────────────────────────────────────
            sf_winners = []
            for (ia, ib) in SEMIS_IDX:
                venc = simular_confronto(qf_winners[ia], qf_winners[ib], art_sim, ass_sim)
                sf_winners.append(venc)
                resultados[venc]["semi"] += 1
            
            # ── FINAL ─────────────────────────────────────────────────
            for f in sf_winners:
                resultados[f]["final"] += 1
            
            campeao = simular_confronto(sf_winners[0], sf_winners[1], art_sim, ass_sim)
            resultados[campeao]["campeao"] += 1
            
            # Acumular artilheiros/assists totais
            for k, v in art_sim.items():
                artilheiros_acum[k] += v
            for k, v in ass_sim.items():
                assistentes_acum[k] += v
        
        # =========================================================
        # CONSOLIDAÇÃO E OUTPUTS
        # =========================================================
        print(f"\n[INFO] Consolidando {SIMULACOES:,} simulações e gerando outputs...\n")
        os.makedirs(os.path.join(SCRIPT_DIR, "outputs"), exist_ok=True)
        
        # ── Chances por fase ──────────────────────────────────────────
        dados_chances = []
        for time in TIMES_MATA_MATA:
            dados_chances.append({
                "Seleção": time,
                "Passa 1ª Fase (%)":  round((resultados[time]["r1"]      / SIMULACOES) * 100, 2),
                "Oitavas (%)":        round((resultados[time]["oitavas"]  / SIMULACOES) * 100, 2),
                "Quartas (%)":        round((resultados[time]["quartas"]  / SIMULACOES) * 100, 2),
                "Semifinal (%)":      round((resultados[time]["semi"]     / SIMULACOES) * 100, 2),
                "Final (%)":          round((resultados[time]["final"]    / SIMULACOES) * 100, 2),
                "Campeão (%)":        round((resultados[time]["campeao"]  / SIMULACOES) * 100, 2),
            })
        
        df_chances = pd.DataFrame(dados_chances).sort_values("Campeão (%)", ascending=False)
        path_chances = os.path.join(SCRIPT_DIR, "outputs", "mata_mata_real_chances.csv")
        df_chances.to_csv(path_chances, index=False, encoding="utf-8-sig")
        mlflow.log_artifact(path_chances)
        
        # ── Artilheiros: gols na fase de grupos + média mata-mata ─────
        dados_art = []
        for chave, total in artilheiros_acum.items():
            nome = chave.rsplit(" (", 1)[0]
            media_mm = total / SIMULACOES
            base = artilheiros_base.get(nome, 0)
            dados_art.append({
                "Jogador": chave,
                "Gols_Fase_Grupos": base,
                "Média_Gols_Mata_Mata": round(media_mm, 2),
                "Média_Gols_Copa_Total": round(base + media_mm, 2),
            })
        
        df_art = pd.DataFrame(dados_art).sort_values("Média_Gols_Copa_Total", ascending=False)
        path_art = os.path.join(SCRIPT_DIR, "outputs", "mata_mata_real_artilheiros.csv")
        df_art.head(40).to_csv(path_art, index=False, encoding="utf-8-sig")
        mlflow.log_artifact(path_art)
        
        # ── Assistentes ───────────────────────────────────────────────
        dados_ass = []
        for chave, total in assistentes_acum.items():
            nome = chave.rsplit(" (", 1)[0]
            media_mm = total / SIMULACOES
            base = assistentes_base.get(nome, 0)
            dados_ass.append({
                "Jogador": chave,
                "Assists_Fase_Grupos": base,
                "Média_Assists_Mata_Mata": round(media_mm, 2),
                "Média_Assists_Copa_Total": round(base + media_mm, 2),
            })
        
        df_ass = pd.DataFrame(dados_ass).sort_values("Média_Assists_Copa_Total", ascending=False)
        path_ass = os.path.join(SCRIPT_DIR, "outputs", "mata_mata_real_assistentes.csv")
        df_ass.head(40).to_csv(path_ass, index=False, encoding="utf-8-sig")
        mlflow.log_artifact(path_ass)
        
        # ── Placares mais prováveis dos R1 ────────────────────────────
        dados_placares = []
        for confronto, placares in placares_r1.items():
            top3 = sorted(placares.items(), key=lambda x: x[1], reverse=True)[:3]
            for placar, cnt in top3:
                dados_placares.append({
                    "Confronto": confronto,
                    "Placar": placar,
                    "Probabilidade (%)": round((cnt / SIMULACOES) * 100, 2),
                })
        
        df_placares = pd.DataFrame(dados_placares).sort_values(
            ["Confronto", "Probabilidade (%)"], ascending=[True, False]
        )
        path_placares = os.path.join(SCRIPT_DIR, "outputs", "mata_mata_real_placares.csv")
        df_placares.to_csv(path_placares, index=False, encoding="utf-8-sig")
        mlflow.log_artifact(path_placares)
        
        # =========================================================
        # CONSOLE - RESULTADOS FINAIS
        # =========================================================
        print(f"{'='*68}")
        print(f"  [CAMPEAO]  CAMPEAO MAIS PROVAVEL - TOP 10")
        print(f"{'='*68}")
        print(f"  {'Seleção':<24} {'1ª Fase':>8} {'Oitavas':>8} {'Quartas':>8} {'Semi':>8} {'Final':>8} {'Campeão':>8}")
        print(f"  {'-'*68}")
        for _, row in df_chances.head(10).iterrows():
            print(
                f"  {row['Seleção']:<24}"
                f" {row['Passa 1ª Fase (%)']:>7.1f}%"
                f" {row['Oitavas (%)']:>7.1f}%"
                f" {row['Quartas (%)']:>7.1f}%"
                f" {row['Semifinal (%)']:>7.1f}%"
                f" {row['Final (%)']:>7.1f}%"
                f" {row['Campeão (%)']:>7.1f}%"
            )
        
        print(f"\n{'='*68}")
        print(f"  [GOLS]  ARTILHARIA PROJETADA DA COPA (Fase de Grupos + Mata-Mata)")
        print(f"{'='*68}")
        print(f"  {'Jogador':<38} {'Grupos':>7} {'+MM':>7} {'= TOTAL':>8}")
        print(f"  {'-'*65}")
        for _, row in df_art.head(15).iterrows():
            print(
                f"  {row['Jogador']:<38}"
                f" {row['Gols_Fase_Grupos']:>7}"
                f" {row['Média_Gols_Mata_Mata']:>+7.2f}"
                f" = {row['Média_Gols_Copa_Total']:>5.2f}"
            )
        
        print(f"\n{'='*68}")
        print(f"  [ASSISTS]  ASSISTENCIAS PROJETADAS DA COPA (Fase de Grupos + Mata-Mata)")
        print(f"{'='*68}")
        print(f"  {'Jogador':<38} {'Grupos':>7} {'+MM':>7} {'= TOTAL':>8}")
        print(f"  {'-'*65}")
        for _, row in df_ass.head(15).iterrows():
            print(
                f"  {row['Jogador']:<38}"
                f" {row['Assists_Fase_Grupos']:>7}"
                f" {row['Média_Assists_Mata_Mata']:>+7.2f}"
                f" = {row['Média_Assists_Copa_Total']:>5.2f}"
            )
        
        print(f"\n{'='*68}")
        print(f"  Outputs gerados em copa/outputs/:")
        print(f"    - mata_mata_real_chances.csv")
        print(f"    - mata_mata_real_artilheiros.csv")
        print(f"    - mata_mata_real_assistentes.csv")
        print(f"    - mata_mata_real_placares.csv")
        print(f"{'='*68}\n")
