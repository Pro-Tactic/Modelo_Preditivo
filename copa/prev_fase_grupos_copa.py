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

# =========================================================
# CARGA DE DADOS
# =========================================================
print("Carregando bases de dados da Fase de Grupos...")
try:
    tabela_completa = pd.read_csv(ARQUIVO_CLASSIFICACAO)
except FileNotFoundError:
    print(f"Erro: Não foi possível encontrar {ARQUIVO_CLASSIFICACAO}.")
    sys.exit(1)

# Grupos da Copa
grupos_copa = tabela_completa[tabela_completa["liga"] == "Copa do Mundo FIFA 2026"].copy()
selecoes_copa = grupos_copa["time"].unique()

# Pré-organizar confrontos da fase de grupos
confrontos_por_grupo = defaultdict(list)
for grupo_nome in grupos_copa["grupo"].unique():
    times_do_grupo = grupos_copa[grupos_copa["grupo"] == grupo_nome]["time"].tolist()
    # Combinações 2 a 2
    for i in range(len(times_do_grupo)):
        for j in range(i+1, len(times_do_grupo)):
            confrontos_por_grupo[grupo_nome].append((times_do_grupo[i], times_do_grupo[j]))

# =========================================================
# SIMULAÇÃO MONTE CARLO (EXECUÇÃO GERAL)
# =========================================================

def tie_breaker(tA, tB, tabela_sim, h2h):
    # Retorna 1 se tA > tB, -1 se tA < tB, 0 se igual
    # 1. Pontos
    if tabela_sim[tA]["pts"] != tabela_sim[tB]["pts"]: return 1 if tabela_sim[tA]["pts"] > tabela_sim[tB]["pts"] else -1
    # 2. Saldo de Gols Global
    if tabela_sim[tA]["sg"] != tabela_sim[tB]["sg"]: return 1 if tabela_sim[tA]["sg"] > tabela_sim[tB]["sg"] else -1
    # 3. Gols Pró Global
    if tabela_sim[tA]["gp"] != tabela_sim[tB]["gp"]: return 1 if tabela_sim[tA]["gp"] > tabela_sim[tB]["gp"] else -1
    # 4. Confronto Direto Pontos
    if h2h[tA][tB]["pts"] != h2h[tB][tA]["pts"]: return 1 if h2h[tA][tB]["pts"] > h2h[tB][tA]["pts"] else -1
    # 5. Confronto Direto Saldo
    if h2h[tA][tB]["sg"] != h2h[tB][tA]["sg"]: return 1 if h2h[tA][tB]["sg"] > h2h[tB][tA]["sg"] else -1
    # 6. Confronto Direto Gols Pró
    if h2h[tA][tB]["gp"] != h2h[tB][tA]["gp"]: return 1 if h2h[tA][tB]["gp"] > h2h[tB][tA]["gp"] else -1
    # 7. Sorteio (simulando quebra de empate aleatória se tudo for igual)
    return 1 if np.random.random() > 0.5 else -1

if __name__ == "__main__":
    print(f"Iniciando Motor de Simulação Monte Carlo Fase de Grupos ({SIMULACOES} rodadas)...")

    mlflow.set_tracking_uri("sqlite:///mlruns.db")
    mlflow.set_experiment("Previsao_Copa_Mundo_2026")

    resultados_grupos = {time: {"pontos": [], "saldo": [], "gols_pro": [], "posicao_grupo": [], "avancou": 0} for time in selecoes_copa}
    artilheiros = defaultdict(int)
    assistentes = defaultdict(int)
    placares_provaveis = defaultdict(Counter)

    with mlflow.start_run():
        mlflow.log_param("num_simulacoes", SIMULACOES)
        mlflow.log_param("grupos", len(confrontos_por_grupo))
        
        total_gols_simulados = 0
        total_jogos_simulados = 0
        
        for sim in range(SIMULACOES):
            motor_simulacao.reset_estado_markov()
            tabela_sim = {time: {"pts": 0, "sg": 0, "gp": 0} for time in selecoes_copa}
            h2h = defaultdict(lambda: defaultdict(lambda: {"pts": 0, "sg": 0, "gp": 0}))
            
            for grupo, confrontos in confrontos_por_grupo.items():
                for t1, t2 in confrontos:
                    
                    gols1, gols2 = motor_simulacao.simular_jogo(t1, t2)
                    
                    total_gols_simulados += (gols1 + gols2)
                    total_jogos_simulados += 1
                    
                    placares_provaveis[f"{t1} x {t2}"][f"{gols1} x {gols2}"] += 1
                    
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
                        artilheiros[f"{art} ({t1})"] += 1
                        # Apenas 75% dos gols têm assistência
                        if np.random.random() < 0.75:
                            ass = motor_simulacao.sortear_jogador_evento(t1, "assistencia")
                            if art != ass:
                                assistentes[f"{ass} ({t1})"] += 1
                            
                    for _ in range(gols2):
                        art = motor_simulacao.sortear_jogador_evento(t2, "gol")
                        artilheiros[f"{art} ({t2})"] += 1
                        # Apenas 75% dos gols têm assistência
                        if np.random.random() < 0.75:
                            ass = motor_simulacao.sortear_jogador_evento(t2, "assistencia")
                            if art != ass:
                                assistentes[f"{ass} ({t2})"] += 1
            
            terceiros_colocados = []
            
            for grupo, confrontos in confrontos_por_grupo.items():
                times_do_grupo = list(set([c[0] for c in confrontos] + [c[1] for c in confrontos]))
                
                # Definir função curried para este state de tabela_sim e h2h
                def tb(tA, tB):
                    return tie_breaker(tA, tB, tabela_sim, h2h)
                
                classificacao = sorted(times_do_grupo, key=cmp_to_key(tb), reverse=True)
                
                for i, time in enumerate(classificacao):
                    pos = i + 1
                    resultados_grupos[time]["posicao_grupo"].append(pos)
                    resultados_grupos[time]["pontos"].append(tabela_sim[time]["pts"])
                    resultados_grupos[time]["saldo"].append(tabela_sim[time]["sg"])
                    resultados_grupos[time]["gols_pro"].append(tabela_sim[time]["gp"])
                    
                    if pos <= 2:
                        resultados_grupos[time]["avancou"] += 1
                    elif pos == 3:
                        terceiros_colocados.append(time)
            
            # 8 melhores terceiros passam (usando mesmo tie_breaker)
            def tb_terceiros(tA, tB):
                return tie_breaker(tA, tB, tabela_sim, h2h)
                
            terceiros_ordenados = sorted(terceiros_colocados, key=cmp_to_key(tb_terceiros), reverse=True)
            for t in terceiros_ordenados[:8]:
                resultados_grupos[t]["avancou"] += 1
                
        mlflow.log_metric("media_gols_por_jogo", total_gols_simulados / total_jogos_simulados)
        
        print("Consolidando Estatísticas e Gerando Artefatos...")
        
        dados_finais = []
        for time in selecoes_copa:
            posicoes = Counter(resultados_grupos[time]["posicao_grupo"])
            total_avancou = resultados_grupos[time]["avancou"]
            
            dados_finais.append({
                "Seleção": time,
                "Chance 1º (%)": round((posicoes[1] / SIMULACOES) * 100, 2),
                "Chance 2º (%)": round((posicoes[2] / SIMULACOES) * 100, 2),
                "Chance 3º (%)": round((posicoes[3] / SIMULACOES) * 100, 2),
                "Chance 4º (%)": round((posicoes[4] / SIMULACOES) * 100, 2),
                "Chance Classificação (Top2 + Melhores 3ºs) (%)": round((total_avancou / SIMULACOES) * 100, 2),
                "Média Pontos": round(np.mean(resultados_grupos[time]["pontos"]), 2)
            })
        
        df_finais = pd.DataFrame(dados_finais).sort_values("Chance Classificação (Top2 + Melhores 3ºs) (%)", ascending=False)
        os.makedirs("copa/outputs", exist_ok=True)
        df_finais.to_csv("copa/outputs/probabilidades_grupos_copa.csv", index=False)
        mlflow.log_artifact("copa/outputs/probabilidades_grupos_copa.csv")
        
        df_art = pd.DataFrame(list(artilheiros.items()), columns=["Jogador", "Gols_Simulados"])
        df_art["Gols_Medios_Torneio"] = round(df_art["Gols_Simulados"] / SIMULACOES, 2)
        df_art = df_art.sort_values("Gols_Medios_Torneio", ascending=False).head(30)
        df_art.to_csv("copa/outputs/provaveis_artilheiros.csv", index=False)
        mlflow.log_artifact("copa/outputs/provaveis_artilheiros.csv")
        
        df_ass = pd.DataFrame(list(assistentes.items()), columns=["Jogador", "Assists_Simuladas"])
        df_ass["Assists_Medias_Torneio"] = round(df_ass["Assists_Simuladas"] / SIMULACOES, 2)
        df_ass = df_ass.sort_values("Assists_Medias_Torneio", ascending=False).head(30)
        df_ass.to_csv("copa/outputs/provaveis_assistentes.csv", index=False)
        mlflow.log_artifact("copa/outputs/provaveis_assistentes.csv")
        
        placares_lista = []
        for jogo, placares in placares_provaveis.items():
            placar_mais_comum = placares.most_common(1)[0]
            placares_lista.append({
                "Confronto": jogo,
                "Placar Mais Provável": placar_mais_comum[0],
                "Frequência (%)": round((placar_mais_comum[1] / SIMULACOES) * 100, 2)
            })
    
        df_placares = pd.DataFrame(placares_lista).sort_values("Confronto")
        df_placares.to_csv("copa/outputs/placares_provaveis.csv", index=False)
        mlflow.log_artifact("copa/outputs/placares_provaveis.csv")
        
    print("Concluído! Tabelas geradas localmente e registradas no MLflow.")
