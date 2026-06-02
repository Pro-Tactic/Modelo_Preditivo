import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import mlflow
import random

# Importar as estruturas base do motor da fase de grupos
from prev_fase_grupos_copa import (
    selecoes_copa, confrontos_por_grupo, 
    simular_jogo, sortear_jogador_evento, 
    PESOS_SELECOES, SIMULACOES
)

# =========================================================
# LÓGICA DE SIMULAÇÃO DE MATA-MATA
# =========================================================

def resolver_empate_mata_mata(t1, t2):
    # Lógica simples de pênaltis: leve favoritismo para times de maior Tier
    p1 = PESOS_SELECOES.get(t1, 1.0)
    p2 = PESOS_SELECOES.get(t2, 1.0)
    prob_t1 = p1 / (p1 + p2)
    
    # Suaviza a probabilidade porque pênalti tem muita sorte (ex: 70% vira 60%)
    prob_t1 = 0.5 + (prob_t1 - 0.5) * 0.5 
    
    if np.random.random() < prob_t1:
        return t1, t2 # vencedor, perdedor
    return t2, t1


def sortear_chaveamento_16avos(primeiros, segundos, terceiros):
    # Primeiros (12), Segundos (12), Terceiros (8)
    # Pote 1: 8 melhores primeiros
    pote1 = primeiros[:8]
    # Pote 2: 4 piores primeiros + 4 melhores segundos
    pote2 = primeiros[8:] + segundos[:4]
    # Pote 3: 8 piores segundos
    pote3 = segundos[4:]
    # Pote 4: 8 terceiros
    pote4 = terceiros
    
    # Embaralhar para o sorteio
    random.shuffle(pote1)
    random.shuffle(pote2)
    random.shuffle(pote3)
    random.shuffle(pote4)
    
    confrontos_16avos = []
    # Pote 1 x Pote 4
    for i in range(8):
        confrontos_16avos.append((pote1[i], pote4[i]))
    # Pote 2 x Pote 3
    for i in range(8):
        confrontos_16avos.append((pote2[i], pote3[i]))
        
    return confrontos_16avos

def simular_rodada_mata_mata(confrontos, artilheiros, assistentes, fase_nome):
    vencedores = []
    for t1, t2 in confrontos:
        g1, g2 = simular_jogo(t1, t2)
        
        # Atribuir artilheiros
        for _ in range(g1):
            art = sortear_jogador_evento(t1, "gol")
            ass = sortear_jogador_evento(t1, "assistencia")
            artilheiros[f"{art} ({t1})"] += 1
            if art != ass:
                assistentes[f"{ass} ({t1})"] += 1
                
        for _ in range(g2):
            art = sortear_jogador_evento(t2, "gol")
            ass = sortear_jogador_evento(t2, "assistencia")
            artilheiros[f"{art} ({t2})"] += 1
            if art != ass:
                assistentes[f"{ass} ({t2})"] += 1
                
        if g1 > g2:
            vencedores.append(t1)
        elif g2 > g1:
            vencedores.append(t2)
        else:
            venc, _ = resolver_empate_mata_mata(t1, t2)
            vencedores.append(venc)
            
    # Criar próximos confrontos (Vencedor 1 x Vencedor 2, Vencedor 3 x Vencedor 4...)
    proximos_confrontos = []
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
    
    # Rastreamento de conquistas de fase
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
            tabela_sim = {time: {"pts": 0, "sg": 0, "gp": 0} for time in selecoes_copa}
            
            # 1. FASE DE GRUPOS
            for grupo, confrontos in confrontos_por_grupo.items():
                for t1, t2 in confrontos:
                    gols1, gols2 = simular_jogo(t1, t2)
                    
                    tabela_sim[t1]["gp"] += gols1
                    tabela_sim[t2]["gp"] += gols2
                    tabela_sim[t1]["sg"] += (gols1 - gols2)
                    tabela_sim[t2]["sg"] += (gols2 - gols1)
                    
                    if gols1 > gols2:
                        tabela_sim[t1]["pts"] += 3
                    elif gols2 > gols1:
                        tabela_sim[t2]["pts"] += 3
                    else:
                        tabela_sim[t1]["pts"] += 1
                        tabela_sim[t2]["pts"] += 1
                        
                    for _ in range(gols1):
                        art = sortear_jogador_evento(t1, "gol")
                        ass = sortear_jogador_evento(t1, "assistencia")
                        artilheiros[f"{art} ({t1})"] += 1
                        if art != ass:
                            assistentes[f"{ass} ({t1})"] += 1
                            
                    for _ in range(gols2):
                        art = sortear_jogador_evento(t2, "gol")
                        ass = sortear_jogador_evento(t2, "assistencia")
                        artilheiros[f"{art} ({t2})"] += 1
                        if art != ass:
                            assistentes[f"{ass} ({t2})"] += 1
                            
            # Classificar os grupos
            primeiros = []
            segundos = []
            terceiros = []
            
            for grupo, confrontos in confrontos_por_grupo.items():
                times_do_grupo = list(set([c[0] for c in confrontos] + [c[1] for c in confrontos]))
                classificacao = sorted(times_do_grupo, key=lambda x: (tabela_sim[x]["pts"], tabela_sim[x]["sg"], tabela_sim[x]["gp"]), reverse=True)
                primeiros.append(classificacao[0])
                segundos.append(classificacao[1])
                terceiros.append(classificacao[2])
                
            # Ordenar primeiros, segundos e terceiros para formar potes
            primeiros = sorted(primeiros, key=lambda x: (tabela_sim[x]["pts"], tabela_sim[x]["sg"], tabela_sim[x]["gp"]), reverse=True)
            segundos = sorted(segundos, key=lambda x: (tabela_sim[x]["pts"], tabela_sim[x]["sg"], tabela_sim[x]["gp"]), reverse=True)
            terceiros = sorted(terceiros, key=lambda x: (tabela_sim[x]["pts"], tabela_sim[x]["sg"], tabela_sim[x]["gp"]), reverse=True)[:8]
            
            # 2. CHAVEAMENTO 16-AVOS
            confrontos_mata_mata = sortear_chaveamento_16avos(primeiros, segundos, terceiros)
            
            # 3. MATA MATA
            # 16-avos -> Oitavas
            venc_16avos, confrontos_oitavas = simular_rodada_mata_mata(confrontos_mata_mata, artilheiros, assistentes, "16-avos")
            for v in venc_16avos: resultados[v]["oitavas"] += 1
                
            # Oitavas -> Quartas
            venc_oitavas, confrontos_quartas = simular_rodada_mata_mata(confrontos_oitavas, artilheiros, assistentes, "Oitavas")
            for v in venc_oitavas: resultados[v]["quartas"] += 1
                
            # Quartas -> Semi
            venc_quartas, confrontos_semi = simular_rodada_mata_mata(confrontos_quartas, artilheiros, assistentes, "Quartas")
            for v in venc_quartas: resultados[v]["semi"] += 1
                
            # Semi -> Final
            venc_semi, confrontos_final = simular_rodada_mata_mata(confrontos_semi, artilheiros, assistentes, "Semi")
            for v in venc_semi: resultados[v]["final"] += 1
                
            # Final -> Campeão
            campeao, _ = simular_rodada_mata_mata(confrontos_final, artilheiros, assistentes, "Final")
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
        df_mm.to_csv("chances_mata_mata.csv", index=False)
        mlflow.log_artifact("chances_mata_mata.csv")
        
        # Artilheiros
        df_art = pd.DataFrame(list(artilheiros.items()), columns=["Jogador", "Gols_Simulados"])
        df_art["Gols_Medios_Torneio"] = round(df_art["Gols_Simulados"] / SIMULACOES, 2)
        df_art = df_art.sort_values("Gols_Medios_Torneio", ascending=False).head(30)
        df_art.to_csv("provaveis_artilheiros.csv", index=False)
        mlflow.log_artifact("provaveis_artilheiros.csv")
        
        # Assistentes
        df_ass = pd.DataFrame(list(assistentes.items()), columns=["Jogador", "Assists_Simuladas"])
        df_ass["Assists_Medias_Torneio"] = round(df_ass["Assists_Simuladas"] / SIMULACOES, 2)
        df_ass = df_ass.sort_values("Assists_Medias_Torneio", ascending=False).head(30)
        df_ass.to_csv("provaveis_assistentes.csv", index=False)
        mlflow.log_artifact("provaveis_assistentes.csv")
        
        print("Tabelas de Mata-Mata e Estatísticas de Jogadores geradas com sucesso!")
