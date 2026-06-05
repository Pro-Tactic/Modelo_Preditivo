import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import mlflow
import os
import sys
import json
from functools import cmp_to_key

# Adicionar raiz ao path para importar motor_simulacao
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import motor_simulacao

# =========================================================
# CONFIGURAÇÕES E CONSTANTES
# =========================================================
ARQUIVO_CLASSIFICACAO = "copa/classificacao.csv"

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    SIMULACOES = config_data.get("SIMULACOES", 50000)
except FileNotFoundError:
    print(f"Aviso: {CONFIG_PATH} não encontrado. Usando 50000 simulações padrão.")
    SIMULACOES = 50000

print("Carregando bases de dados do Global...")
try:
    tabela_completa = pd.read_csv(ARQUIVO_CLASSIFICACAO)
except FileNotFoundError:
    print(f"Erro: Não foi possível encontrar {ARQUIVO_CLASSIFICACAO}.")
    sys.exit(1)

grupos_copa = tabela_completa[tabela_completa["liga"] == "Copa do Mundo FIFA 2026"].copy()
selecoes_copa = grupos_copa["time"].unique()

confrontos_por_grupo = defaultdict(list)
for grupo_nome in grupos_copa["grupo"].unique():
    times_do_grupo = grupos_copa[grupos_copa["grupo"] == grupo_nome]["time"].tolist()
    for i in range(len(times_do_grupo)):
        for j in range(i+1, len(times_do_grupo)):
            confrontos_por_grupo[grupo_nome].append((times_do_grupo[i], times_do_grupo[j]))

# =========================================================
# LÓGICA DE SIMULAÇÃO DE MATA-MATA
# =========================================================

def tie_breaker(tA, tB, tabela_sim, h2h):
    if tabela_sim[tA]["pts"] != tabela_sim[tB]["pts"]: return 1 if tabela_sim[tA]["pts"] > tabela_sim[tB]["pts"] else -1
    if tabela_sim[tA]["sg"] != tabela_sim[tB]["sg"]: return 1 if tabela_sim[tA]["sg"] > tabela_sim[tB]["sg"] else -1
    if tabela_sim[tA]["gp"] != tabela_sim[tB]["gp"]: return 1 if tabela_sim[tA]["gp"] > tabela_sim[tB]["gp"] else -1
    if h2h[tA][tB]["pts"] != h2h[tB][tA]["pts"]: return 1 if h2h[tA][tB]["pts"] > h2h[tB][tA]["pts"] else -1
    if h2h[tA][tB]["sg"] != h2h[tB][tA]["sg"]: return 1 if h2h[tA][tB]["sg"] > h2h[tB][tA]["sg"] else -1
    if h2h[tA][tB]["gp"] != h2h[tB][tA]["gp"]: return 1 if h2h[tA][tB]["gp"] > h2h[tB][tA]["gp"] else -1
    return 1 if np.random.random() > 0.5 else -1

def sortear_chaveamento_16avos(primeiros, segundos, terceiros):
    # Abordagem estruturada de seeding para simular cruzamentos oficiais
    # primeiros: 12 times (ordenados do melhor pro pior)
    # segundos: 12 times (ordenados)
    # terceiros: 8 times (ordenados)
    
    confrontos = []
    
    # 8 melhores 1ºs cruzam com os 8 terceiros (cruzamento invertido 1º melhor x 8º melhor 3º)
    for i in range(8):
        confrontos.append((primeiros[i], terceiros[7-i]))
        
    # Os 4 piores 1ºs (pos 8 a 11) cruzam com os 4 piores 2ºs (pos 8 a 11)
    for i in range(4):
        confrontos.append((primeiros[8+i], segundos[11-i]))
        
    # Os 8 melhores 2ºs cruzam entre si (1º melhor 2º x 8º melhor 2º)
    for i in range(4):
        confrontos.append((segundos[i], segundos[7-i]))
        
    return confrontos

def simular_rodada_mata_mata(confrontos, artilheiros, assistentes):
    vencedores = []
    for t1, t2 in confrontos:
        g1, g2 = motor_simulacao.simular_jogo(t1, t2)
        
        for _ in range(g1):
            art = motor_simulacao.sortear_jogador_evento(t1, "gol")
            ass = motor_simulacao.sortear_jogador_evento(t1, "assistencia")
            artilheiros[f"{art} ({t1})"] += 1
            if art != ass: assistentes[f"{ass} ({t1})"] += 1
                
        for _ in range(g2):
            art = motor_simulacao.sortear_jogador_evento(t2, "gol")
            ass = motor_simulacao.sortear_jogador_evento(t2, "assistencia")
            artilheiros[f"{art} ({t2})"] += 1
            if art != ass: assistentes[f"{ass} ({t2})"] += 1
                
        if g1 > g2:
            vencedores.append(t1)
        elif g2 > g1:
            vencedores.append(t2)
        else:
            # Empate -> Prorrogação
            gp1, gp2 = motor_simulacao.simular_prorrogacao(t1, t2)
            
            # (Prorrogação também soma nas estatísticas de gols reais do jogador!)
            for _ in range(gp1):
                art = motor_simulacao.sortear_jogador_evento(t1, "gol")
                artilheiros[f"{art} ({t1})"] += 1
                if np.random.random() < 0.75:
                    ass = motor_simulacao.sortear_jogador_evento(t1, "assistencia")
                    if art != ass: assistentes[f"{ass} ({t1})"] += 1
            for _ in range(gp2):
                art = motor_simulacao.sortear_jogador_evento(t2, "gol")
                artilheiros[f"{art} ({t2})"] += 1
                if np.random.random() < 0.75:
                    ass = motor_simulacao.sortear_jogador_evento(t2, "assistencia")
                    if art != ass: assistentes[f"{ass} ({t2})"] += 1
            
            if gp1 > gp2:
                vencedores.append(t1)
            elif gp2 > gp1:
                vencedores.append(t2)
            else:
                # Pênaltis
                venc_penaltis = motor_simulacao.simular_penaltis(t1, t2)
                vencedores.append(venc_penaltis)
            
    proximos_confrontos = []
    # Cria os cruzamentos para a próxima fase (adjacentes)
    for i in range(0, len(vencedores), 2):
        if i+1 < len(vencedores):
            proximos_confrontos.append((vencedores[i], vencedores[i+1]))
            
    return vencedores, proximos_confrontos

# =========================================================
# MOTOR PRINCIPAL
# =========================================================

if __name__ == "__main__":
    print(f"Iniciando Motor Global (Grupos + Mata-Mata) com {SIMULACOES} rodadas...")
    
    mlflow.set_tracking_uri("sqlite:///mlruns.db")
    mlflow.set_experiment("Previsao_Copa_Mundo_2026_Global")
    
    resultados = {
        time: {
            "oitavas": 0,
            "quartas": 0,
            "semi": 0,
            "final": 0,
            "campeao": 0
        } for time in selecoes_copa
    }
    
    artilheiros = defaultdict(int)
    assistentes = defaultdict(int)
    
    with mlflow.start_run():
        mlflow.log_param("num_simulacoes", SIMULACOES)
        
        for sim in range(SIMULACOES):
            motor_simulacao.reset_estado_markov()
            tabela_sim = {time: {"pts": 0, "sg": 0, "gp": 0} for time in selecoes_copa}
            h2h = defaultdict(lambda: defaultdict(lambda: {"pts": 0, "sg": 0, "gp": 0}))
            
            # 1. FASE DE GRUPOS
            for grupo, confrontos in confrontos_por_grupo.items():
                for t1, t2 in confrontos:
                    gols1, gols2 = motor_simulacao.simular_jogo(t1, t2)
                    
                    tabela_sim[t1]["gp"] += gols1
                    tabela_sim[t2]["gp"] += gols2
                    tabela_sim[t1]["sg"] += (gols1 - gols2)
                    tabela_sim[t2]["sg"] += (gols2 - gols1)
                    
                    h2h[t1][t2]["gp"] += gols1
                    h2h[t2][t1]["gp"] += gols2
                    h2h[t1][t2]["sg"] += (gols1 - gols2)
                    h2h[t2][t1]["sg"] += (gols2 - gols1)
                    
                    if gols1 > gols2:
                        tabela_sim[t1]["pts"] += 3
                        h2h[t1][t2]["pts"] += 3
                    elif gols2 > gols1:
                        tabela_sim[t2]["pts"] += 3
                        h2h[t2][t1]["pts"] += 3
                    else:
                        tabela_sim[t1]["pts"] += 1
                        tabela_sim[t2]["pts"] += 1
                        h2h[t1][t2]["pts"] += 1
                        h2h[t2][t1]["pts"] += 1
                        
                    for _ in range(gols1):
                        art = motor_simulacao.sortear_jogador_evento(t1, "gol")
                        ass = motor_simulacao.sortear_jogador_evento(t1, "assistencia")
                        artilheiros[f"{art} ({t1})"] += 1
                        if art != ass: assistentes[f"{ass} ({t1})"] += 1
                            
                    for _ in range(gols2):
                        art = motor_simulacao.sortear_jogador_evento(t2, "gol")
                        ass = motor_simulacao.sortear_jogador_evento(t2, "assistencia")
                        artilheiros[f"{art} ({t2})"] += 1
                        if art != ass: assistentes[f"{ass} ({t2})"] += 1
                            
            def tb_global(tA, tB):
                return tie_breaker(tA, tB, tabela_sim, h2h)
                
            primeiros = []
            segundos = []
            terceiros = []
            
            for grupo, confrontos in confrontos_por_grupo.items():
                times_do_grupo = list(set([c[0] for c in confrontos] + [c[1] for c in confrontos]))
                classificacao = sorted(times_do_grupo, key=cmp_to_key(tb_global), reverse=True)
                primeiros.append(classificacao[0])
                segundos.append(classificacao[1])
                terceiros.append(classificacao[2])
                
            # Ordenar para formar potes (ranking global da 1a fase)
            primeiros = sorted(primeiros, key=cmp_to_key(tb_global), reverse=True)
            segundos = sorted(segundos, key=cmp_to_key(tb_global), reverse=True)
            terceiros = sorted(terceiros, key=cmp_to_key(tb_global), reverse=True)[:8]
            
            # 2. CHAVEAMENTO 16-AVOS
            confrontos_mata_mata = sortear_chaveamento_16avos(primeiros, segundos, terceiros)
            
            # 3. MATA MATA
            # 16-avos -> Oitavas
            venc_16avos, confrontos_oitavas = simular_rodada_mata_mata(confrontos_mata_mata, artilheiros, assistentes)
            for v in venc_16avos: resultados[v]["oitavas"] += 1
                
            # Oitavas -> Quartas
            venc_oitavas, confrontos_quartas = simular_rodada_mata_mata(confrontos_oitavas, artilheiros, assistentes)
            for v in venc_oitavas: resultados[v]["quartas"] += 1
                
            # Quartas -> Semi
            venc_quartas, confrontos_semi = simular_rodada_mata_mata(confrontos_quartas, artilheiros, assistentes)
            for v in venc_quartas: resultados[v]["semi"] += 1
                
            # Semi -> Final
            venc_semi, confrontos_final = simular_rodada_mata_mata(confrontos_semi, artilheiros, assistentes)
            for v in venc_semi: resultados[v]["final"] += 1
                
            # Final -> Campeão
            campeao, _ = simular_rodada_mata_mata(confrontos_final, artilheiros, assistentes)
            resultados[campeao[0]]["campeao"] += 1

        print("Consolidando Estatísticas Finais...")
        
        dados_mata_mata = []
        for time in selecoes_copa:
            dados_mata_mata.append({
                "Seleção": time,
                "Oitavas (%)": round((resultados[time]["oitavas"] / SIMULACOES) * 100, 2),
                "Quartas (%)": round((resultados[time]["quartas"] / SIMULACOES) * 100, 2),
                "Semifinal (%)": round((resultados[time]["semi"] / SIMULACOES) * 100, 2),
                "Final (%)": round((resultados[time]["final"] / SIMULACOES) * 100, 2),
                "Campeão (%)": round((resultados[time]["campeao"] / SIMULACOES) * 100, 2)
            })
            
        df_mm = pd.DataFrame(dados_mata_mata).sort_values("Campeão (%)", ascending=False)
        os.makedirs("copa/outputs", exist_ok=True)
        df_mm.to_csv("copa/outputs/chances_mata_mata.csv", index=False)
        mlflow.log_artifact("copa/outputs/chances_mata_mata.csv")
        
        # Artilheiros
        df_art = pd.DataFrame(list(artilheiros.items()), columns=["Jogador", "Gols_Simulados"])
        df_art["Gols_Medios_Torneio"] = round(df_art["Gols_Simulados"] / SIMULACOES, 2)
        df_art = df_art.sort_values("Gols_Medios_Torneio", ascending=False).head(30)
        df_art.to_csv("copa/outputs/provaveis_artilheiros.csv", index=False)
        mlflow.log_artifact("copa/outputs/provaveis_artilheiros.csv")
        
        # Assistentes
        df_ass = pd.DataFrame(list(assistentes.items()), columns=["Jogador", "Assists_Simuladas"])
        df_ass["Assists_Medias_Torneio"] = round(df_ass["Assists_Simuladas"] / SIMULACOES, 2)
        df_ass = df_ass.sort_values("Assists_Medias_Torneio", ascending=False).head(30)
        df_ass.to_csv("copa/outputs/provaveis_assistentes.csv", index=False)
        mlflow.log_artifact("copa/outputs/provaveis_assistentes.csv")
        
        print("Tabelas de Mata-Mata e Estatísticas de Jogadores geradas com sucesso!")
