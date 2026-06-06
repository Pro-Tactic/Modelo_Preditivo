import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime
import json
import os
import sys
import mlflow

# Adiciona o diretório atual ao path para importar motor_simulacao e formacoes
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import motor_simulacao
from formacoes import MAPA_FORMACAO

# =========================================================
# CONFIGURAÇÕES
# =========================================================
ARQUIVO_JOGOS = "copa/jogos.csv"
ARQUIVO_CONVOCACAO = "copa/convocacao.csv"
SIMULACOES = 100000

TIME_A = "Brazil"
TIME_B = "Egypt"

# =========================================================
# LESÕES / DESFALQUES
# =========================================================
print("="*50)
print(f"PREVISÃO: {TIME_A} x {TIME_B}")
print("="*50)

usar_lesoes = input("Existe algum jogador machucado/suspenso? (s/n): ").strip().lower()

jogadores_fora = []
if usar_lesoes == "s":
    print("\nDigite os nomes separados por vírgula.")
    print("Exemplo: Alisson, Mohamed Salah")
    entrada = input("Jogadores fora: ")
    jogadores_fora = [x.strip() for x in entrada.split(",") if x.strip()]

print("\nJogadores indisponíveis:")
if jogadores_fora:
    for j in jogadores_fora:
        print("-", j)
else:
    print("Nenhum")
print()

# =========================================================
# LOAD & FILTER
# =========================================================
# O motor_simulacao já leu jogos.csv e calculou as forças globais.
# Vamos filtrar os jogos na memória apenas para extração da escalação.
jogos = pd.read_csv(ARQUIVO_JOGOS)
jogos["data_jogo"] = pd.to_datetime(jogos["data_jogo"])

jogos_filtrados = jogos[
    (jogos["time_casa"].isin([TIME_A, TIME_B])) |
    (jogos["time_fora"].isin([TIME_A, TIME_B]))
].copy()

# =========================================================
# UTILIDADES LOCAIS
# =========================================================
def separar_jogadores(texto):
    if pd.isna(texto): return []
    return [x.strip() for x in texto.split("|")]

def obter_posicao_time(time):
    return motor_simulacao.obter_pontos_fifa(time)

def peso_adversario(pts):
    # Base 1500 pontos. Time de 1800 pts -> 1.2x. Time de 1200 pts -> 0.8x.
    return max(0.5, pts / 1500.0)

# =========================================================
# MARKOV FORMAÇÃO & ESCALAÇÕES FIXAS
# =========================================================
def formacao_mais_comum(time):
    if time not in motor_simulacao.transicoes_formacao:
        return '4-3-3'
    estado_atual = motor_simulacao.ultima_formacao_time.get(time, "4-3-3")
    destinos = motor_simulacao.transicoes_formacao[time].get(estado_atual)
    if not destinos:
        return '4-3-3'
    contagem = Counter(destinos)
    return contagem.most_common(1)[0][0]

# Brasil: Formação fixada pelo Ancelotti
formacao_A = "4-4-2"
formacao_B = formacao_mais_comum(TIME_B)

escalacao_A = [
    ("GK", "Alisson"),
    ("RB", "Wesley"),
    ("RCB", "Marquinhos"),
    ("LCB", "Gabriel Magalhães"),
    ("LB", "Douglas Santos"),
    ("RM", "Luiz Henrique"),
    ("CM1", "Casemiro"),
    ("CM2", "Bruno Guimarães"),
    ("LM", "Raphinha"),
    ("ST1", "Vinícius Júnior"),
    ("ST2", "Igor Thiago")
]

# =========================================================
# ESCALAÇÃO POR SLOT TÁTICO
# =========================================================
def escalacao_tatica(df, time, formacao_prevista, adversario):
    slots = MAPA_FORMACAO.get(formacao_prevista, MAPA_FORMACAO["4-3-3"])
    pesos_slot = defaultdict(lambda: defaultdict(float))
    
    pts_adv = obter_posicao_time(adversario)
    peso_adv = peso_adversario(pts_adv)
    
    convocados = motor_simulacao.jogadores_convocados.get(time, set())
    df_time = df[(df["time_casa"] == time) | (df["time_fora"] == time)]
    
    for _, row in df_time.iterrows():
        peso = motor_simulacao.peso_recencia(row["data_jogo"], fator=0.015)
        peso *= motor_simulacao.obter_peso_competicao(row.get("competicao", ""))
        peso *= peso_adv
        
        if row["time_casa"] == time:
            titulares = separar_jogadores(row["titulares_casa"])
            formacao = row["formacao_casa"]
        else:
            titulares = separar_jogadores(row["titulares_fora"])
            formacao = row["formacao_fora"]
            
        if formacao != formacao_prevista:
            peso *= 0.5
            
        estrutura = MAPA_FORMACAO.get(formacao)
        if not estrutura or len(titulares) != len(estrutura):
            continue
            
        for slot, jogador in zip(estrutura, titulares):
            if jogador not in jogadores_fora and (not convocados or jogador in convocados):
                pesos_slot[slot][jogador] += peso
                
    escalacao = []
    usados = set()
    
    for slot in slots:
        candidatos = sorted(
            [(jogador, pontuacao) for jogador, pontuacao in pesos_slot[slot].items()],
            key=lambda x: x[1],
            reverse=True
        )
        escolhido = None
        for jogador, _ in candidatos:
            if jogador not in usados:
                escolhido = jogador
                usados.add(jogador)
                break
        if escolhido is None:
            disponiveis = [j for j in convocados if j not in usados and j not in jogadores_fora]
            escolhido = disponiveis[0] if disponiveis else "N/D"
            usados.add(escolhido)
            
        escalacao.append((slot, escolhido))
        
    return escalacao

# Egito (Escalação fixada pelo usuário)
formacao_B = "5-2-3"
escalacao_B = [
    ("GK", "Mohamed El Shenawy"),
    ("RWB", "Mohamed Hany"),
    ("RCB", "Hamdi Fathy"),
    ("CB", "Yasser Ibrahim"),
    ("LCB", "Rami Rabia"),
    ("LWB", "Ahmed Fatouh"),
    ("CM1", "Mohanad Lasheen"),
    ("CM2", "Marwan Attia"),
    ("RW", "Mohamed Salah"),
    ("ST", "Omar Marmoush"),
    ("LW", "Mahmoud Trézéguet")
]

# =========================================================
# FORÇA OFENSIVA E DEFENSIVA (PENALIZAÇÕES POR DESFALQUE)
# =========================================================
def impacto_desfalques(time, df):
    penalizacao_ataque = 0
    penalizacao_defesa = 0
    
    df_time = df[(df["time_casa"] == time) | (df["time_fora"] == time)]
    
    for jogador in jogadores_fora:
        score = 0
        soma_indices = 0
        qtd_titular = 0
        for _, row in df_time.iterrows():
            peso = motor_simulacao.peso_recencia(row["data_jogo"], fator=0.015)
            
            titulares_casa = separar_jogadores(row["titulares_casa"])
            titulares_fora = separar_jogadores(row["titulares_fora"])
            gols = motor_simulacao.extrair_jogadores(row["gols"])
            assists = motor_simulacao.extrair_jogadores(row["assistencias"])
            
            if jogador in titulares_casa:
                score += 1.5 * peso
                soma_indices += titulares_casa.index(jogador)
                qtd_titular += 1
            if jogador in titulares_fora:
                score += 1.5 * peso
                soma_indices += titulares_fora.index(jogador)
                qtd_titular += 1
            if jogador in gols: score += 3 * peso
            if jogador in assists: score += 2 * peso
                
        if qtd_titular > 0:
            idx_medio = soma_indices / qtd_titular
            if idx_medio <= 4.5: posicao = "DEF"
            elif idx_medio <= 8.5: posicao = "MID"
            else: posicao = "ATK"
            
            importancia = score
            penalidade = min(importancia * 0.015, 0.20)
            
            if posicao == "DEF":
                penalizacao_defesa += penalidade * 0.8
                penalizacao_ataque += penalidade * 0.2
            elif posicao == "ATK":
                penalizacao_ataque += penalidade * 0.9
                penalizacao_defesa += penalidade * 0.1
            else:
                penalizacao_ataque += penalidade * 0.6
                penalizacao_defesa += penalidade * 0.4
                
    return penalizacao_ataque, penalizacao_defesa

penalidade_atk_A, penalidade_def_A = impacto_desfalques(TIME_A, jogos_filtrados)
penalidade_atk_B, penalidade_def_B = impacto_desfalques(TIME_B, jogos_filtrados)

motor_simulacao.forca_ataque_global[TIME_A] *= max(0.45, 1 - penalidade_atk_A)
motor_simulacao.forca_defesa_global[TIME_A] *= (1 + penalidade_def_A)
motor_simulacao.forca_ataque_global[TIME_B] *= max(0.45, 1 - penalidade_atk_B)
motor_simulacao.forca_defesa_global[TIME_B] *= (1 + penalidade_def_B)

# =========================================================
# BATEDORES DE PÊNALTI
# =========================================================
motor_simulacao.PESO_COBRADOR_PENALTI[TIME_A] = {
    "Igor Thiago": 1.5,
}
motor_simulacao.PESO_COBRADOR_PENALTI[TIME_B] = {
    "Mohamed Salah": 1.5,
}

# =========================================================
# SIMULAÇÃO MONTE CARLO & MLFLOW
# =========================================================
print(f"\nSimulando {SIMULACOES} partidas entre {TIME_A} e {TIME_B}...")

mlflow.set_tracking_uri("sqlite:///mlruns_amistoso.db")
mlflow.set_experiment("Previsao_Amistoso_Brasil_Egito")

vitorias_A = 0
vitorias_B = 0
empates = 0
placares = defaultdict(int)
probs_gol = defaultdict(int)

# Função para sortear gol restrito à escalação (evita reservas terem 30% de chance)
def sortear_gol_titular(time, escalacao):
    opcoes = []
    pesos = []
    for slot, jogador in escalacao:
        if jogador == "N/D": continue
        peso = motor_simulacao.distribuicao_gols[time].get(jogador, 0)
        if time in motor_simulacao.PESO_COBRADOR_PENALTI:
            peso *= motor_simulacao.PESO_COBRADOR_PENALTI[time].get(jogador, 1.0)
        opcoes.append(jogador)
        pesos.append(peso + 0.1) # peso mínimo para qualquer titular
    
    opcoes.append("Reservas/Outros")
    pesos.append(0.5) # peso fixo para o banco de reservas
    
    probabilidades = np.array(pesos) / sum(pesos)
    return np.random.choice(opcoes, p=probabilidades)

with mlflow.start_run():
    mlflow.log_param("time_a", TIME_A)
    mlflow.log_param("time_b", TIME_B)
    mlflow.log_param("simulacoes", SIMULACOES)
    mlflow.log_param("desfalques", ", ".join(jogadores_fora) if jogadores_fora else "Nenhum")

    for _ in range(SIMULACOES):
        golsA, golsB = motor_simulacao.simular_jogo(TIME_A, TIME_B)
        
        placares[f"{golsA}x{golsB}"] += 1
        
        if golsA > golsB: vitorias_A += 1
        elif golsB > golsA: vitorias_B += 1
        else: empates += 1
            
        for _ in range(golsA):
            art = sortear_gol_titular(TIME_A, escalacao_A)
            if art not in jogadores_fora:
                probs_gol[f"{art} ({TIME_A})"] += 1
                
        for _ in range(golsB):
            art = sortear_gol_titular(TIME_B, escalacao_B)
            if art not in jogadores_fora:
                probs_gol[f"{art} ({TIME_B})"] += 1

    prob_vit_A = vitorias_A / SIMULACOES
    prob_emp = empates / SIMULACOES
    prob_vit_B = vitorias_B / SIMULACOES

    mlflow.log_metric("prob_vitoria_time_a", prob_vit_A)
    mlflow.log_metric("prob_empate", prob_emp)
    mlflow.log_metric("prob_vitoria_time_b", prob_vit_B)

    # Salvando resultados detalhados como artefatos
    os.makedirs("copa/outputs", exist_ok=True)
    
    df_placares = pd.DataFrame(
        [{"Placar": p, "Probabilidade (%)": round((c / SIMULACOES) * 100, 2)} for p, c in placares.items()]
    ).sort_values("Probabilidade (%)", ascending=False)
    df_placares.to_csv("copa/outputs/brasil_egito_placares.csv", index=False)
    mlflow.log_artifact("copa/outputs/brasil_egito_placares.csv")

    df_gols = pd.DataFrame(
        [{"Jogador": j, "Probabilidade de Marcar (%)": round((c / SIMULACOES) * 100, 2)} for j, c in probs_gol.items()]
    ).sort_values("Probabilidade de Marcar (%)", ascending=False).head(30)
    df_gols.to_csv("copa/outputs/brasil_egito_goleadores.csv", index=False)
    mlflow.log_artifact("copa/outputs/brasil_egito_goleadores.csv")

# =========================================================
# RESULTADOS NO CONSOLE
# =========================================================
print("\n" + "="*50)
print(f"[{TIME_A}] PROVÁVEL ESCALAÇÃO ({formacao_A})")
print("="*50)
for slot, jogador in escalacao_A:
    print(f"{slot.ljust(5)} - {jogador}")

print("\n" + "="*50)
print(f"[{TIME_B}] PROVÁVEL ESCALAÇÃO ({formacao_B})")
print("="*50)
for slot, jogador in escalacao_B:
    print(f"{slot.ljust(5)} - {jogador}")

print("\n" + "="*50)
print("PROBABILIDADES DE RESULTADO")
print("="*50)
print(f"Vitória do {TIME_A}: {(prob_vit_A)*100:.2f}%")
print(f"Empate:             {(prob_emp)*100:.2f}%")
print(f"Vitória do {TIME_B}: {(prob_vit_B)*100:.2f}%")

print("\n" + "="*50)
print("PLACARES MAIS PROVÁVEIS")
print("="*50)
top_placares = sorted(placares.items(), key=lambda x: x[1], reverse=True)[:5]
for placar, count in top_placares:
    print(f"{placar}: {(count/SIMULACOES)*100:.2f}%")

print("\n" + "="*50)
print("PROBABILIDADE DE MARCAR GOL (QUALQUER MOMENTO)")
print("="*50)
top_gols = sorted(probs_gol.items(), key=lambda x: x[1], reverse=True)[:10]
for jogador, count in top_gols:
    prob_marcar = (count / SIMULACOES) * 100
    print(f"{jogador.ljust(30)} {prob_marcar:.2f}%")
print("==================================================\n")
