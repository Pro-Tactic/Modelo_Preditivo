import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime
import math
import json
import os

# =========================================================
# CONFIGURAÇÕES E CONSTANTES
# =========================================================
# O arquivo JSON está na raiz, e os scripts rodam na raiz (já que os caminhos são 'copa/jogos.csv')
ARQUIVO_JOGOS = "copa/jogos.csv"
ARQUIVO_CONVOCACAO = "copa/convocacao.csv"
ARQUIVO_RANKING = "copa/fifa_ranking_men.json"

BATEDORES_PENALTI = {
    "Brazil": ["Neymar", "Vinícius Júnior", "Lucas Paquetá", "Rodrygo"],
    "Argentina": ["Lionel Messi", "Julián Alvarez", "Lautaro Martínez", "Alexis Mac Allister"],
    "France": ["Kylian Mbappé", "Antoine Griezmann"],
    "England": ["Harry Kane", "Bukayo Saka", "Cole Palmer"],
    "Portugal": ["Cristiano Ronaldo", "Bruno Fernandes", "João Félix"],
    "Germany": ["Kai Havertz", "İlkay Gündoğan", "Niclas Füllkrug"],
    "Spain": ["Rodri", "Álvaro Morata", "Dani Olmo"],
    "Belgium": ["Romelu Lukaku", "Kevin De Bruyne"],
    "Netherlands": ["Cody Gakpo", "Memphis Depay", "Virgil van Dijk"],
    "Italy": ["Jorginho", "Nicolò Barella", "Federico Chiesa"],
    "Croatia": ["Luka Modrić", "Andrej Kramarić"],
    "Uruguay": ["Federico Valverde", "Darwin Núñez", "Luis Suárez"],
    "Colombia": ["James Rodríguez", "Luis Díaz"]
}

HOST_TEAMS = ["USA", "Canada", "Mexico"]

# =========================================================
# CARGA DE DADOS
# =========================================================
print("Carregando bases de dados do Motor...")

try:
    jogos = pd.read_csv(ARQUIVO_JOGOS)
    convocacao = pd.read_csv(ARQUIVO_CONVOCACAO)
    jogos["data_jogo"] = pd.to_datetime(jogos["data_jogo"])
except FileNotFoundError as e:
    print(f"Aviso: Não encontrou o arquivo CSV. Verifique o caminho de execução. Erro: {e}")
    # Cria DF vazios para o linter/tipo funcionar caso seja rodado de um dir diferente
    jogos = pd.DataFrame(columns=["data_jogo", "time_casa", "time_fora", "resultado", "formacao_casa", "formacao_fora", "gols", "assistencias"])
    convocacao = pd.DataFrame(columns=["selecao", "jogador"])

TRADUCAO_FIFA = {
    "Mexico": "México", "South Africa": "África do Sul", "South Korea": "República da Coreia",
    "Czechia": "República Tcheca", "Canada": "Canadá", "Bosnia & Herzegovina": "Bósnia e Herzegovina",
    "Qatar": "Catar", "Switzerland": "Suíça", "Brazil": "Brasil", "Morocco": "Marrocos",
    "Haiti": "Haiti", "Scotland": "Escócia", "USA": "EUA", "Paraguay": "Paraguai",
    "Australia": "Austrália", "Türkiye": "Türkiye", "Germany": "Alemanha",
    "Curaçao": "Curaçau", "Côte d'Ivoire": "Costa do Marfim", "Ecuador": "Equador",
    "Netherlands": "Holanda", "Japan": "Japão", "Sweden": "Suécia", "Tunisia": "Tunísia",
    "Belgium": "Bélgica", "Egypt": "Egito", "Iran": "RI do Irã", "New Zealand": "Nova Zelândia",
    "Spain": "Espanha", "Cabo Verde": "Cabo Verde", "Saudi Arabia": "Arábia Saudita",
    "Uruguay": "Uruguai", "France": "França", "Senegal": "Senegal", "Iraq": "Iraque",
    "Norway": "Noruega", "Argentina": "Argentina", "Algeria": "Argélia", "Austria": "Áustria",
    "Jordan": "Jordânia", "Portugal": "Portugal", "DR Congo": "RD do Congo", 
    "Uzbekistan": "Uzbequistão", "Colombia": "Colômbia", "England": "Inglaterra",
    "Croatia": "Croácia", "Ghana": "Gana", "Panama": "Panamá"
}

fifa_points = {}
try:
    with open(ARQUIVO_RANKING, "r", encoding="utf-8") as f:
        ranking_data = json.load(f)
    for item in ranking_data:
        # Tratamento: remover acentos ou padronizar pode ser necessário se houver divergência entre JSON e CSV.
        fifa_points[item["country"]] = item["points"]
except FileNotFoundError as e:
    print(f"Aviso: Arquivo de ranking não encontrado em {ARQUIVO_RANKING}. Usando pesos padrão.")

def obter_pontos_fifa(time):
    # Se a string veio com erro de encoding, limpa
    t_clean = time.replace("", "") 
    nome_pt = TRADUCAO_FIFA.get(time, time)
    if nome_pt in fifa_points:
        return fifa_points[nome_pt]
    # Fallback para string zoada
    for en, pt in TRADUCAO_FIFA.items():
        if t_clean in en:
            return fifa_points.get(pt, 1300)
    return 1300

jogadores_convocados = defaultdict(set)
for _, row in convocacao.iterrows():
    jogadores_convocados[row["selecao"]].add(row["jogador"])

# =========================================================
# UTILIDADES
# =========================================================
def peso_recencia(data_jogo, fator=0.001):
    dias = (datetime.now() - data_jogo).days
    return math.exp(-fator * max(0, dias))

def parse_resultado(resultado):
    try:
        g1, g2 = resultado.split("x")
        return int(g1.strip()), int(g2.strip())
    except:
        return 0, 0

def extrair_jogadores(texto):
    if pd.isna(texto):
        return []
    eventos = texto.split("|")
    jogadores = []
    for ev in eventos:
        try:
            jogador = ev.split("->")[0].split("'")[-1].strip()
            jogadores.append(jogador)
        except:
            pass
    return jogadores

# =========================================================
# FORÇA DOS TIMES E CICLO DA COPA (DIXON-COLES SIMPLIFICADO)
# =========================================================
print("Calculando forças das seleções (Dixon-Coles simplificado)...")

forca_ataque_global = defaultdict(lambda: 1.0)
forca_defesa_global = defaultdict(lambda: 1.0)

total_gols = 0
total_jogos = 0
for _, row in jogos.iterrows():
    g1, g2 = parse_resultado(row["resultado"])
    total_gols += (g1 + g2)
    total_jogos += 1

MEDIA_GOLS_LIGA = (total_gols / total_jogos) / 2 if total_jogos > 0 else 1.5

def calcular_forcas():
    forcas_ataque = defaultdict(float)
    forcas_defesa = defaultdict(float)
    pesos_ataque = defaultdict(float)
    pesos_defesa = defaultdict(float)
    
    for _, row in jogos.iterrows():
        g1, g2 = parse_resultado(row["resultado"])
        peso = peso_recencia(row["data_jogo"])
        t_casa = row["time_casa"]
        t_fora = row["time_fora"]
        
        pts_casa = obter_pontos_fifa(t_casa)
        pts_fora = obter_pontos_fifa(t_fora)
        
        # O gol marcado ganha um multiplicador baseado na força de quem sofreu
        gol_ajustado_casa = g1 * (pts_fora / 1500.0)
        gol_ajustado_fora = g2 * (pts_casa / 1500.0)
        
        # O gol sofrido dói mais se vier de um time fraco (inverso)
        def_ajustada_casa = g2 * (1500.0 / max(500, pts_fora))
        def_ajustada_fora = g1 * (1500.0 / max(500, pts_casa))
        
        forcas_ataque[t_casa] += (gol_ajustado_casa * peso)
        pesos_ataque[t_casa] += peso
        
        forcas_defesa[t_casa] += (def_ajustada_casa * peso)
        pesos_defesa[t_casa] += peso
        
        forcas_ataque[t_fora] += (gol_ajustado_fora * peso)
        pesos_ataque[t_fora] += peso
        
        forcas_defesa[t_fora] += (def_ajustada_fora * peso)
        pesos_defesa[t_fora] += peso

    for time in set(list(forcas_ataque.keys()) + list(forcas_defesa.keys())):
        if pesos_ataque[time] > 0:
            atk = forcas_ataque[time] / pesos_ataque[time]
            df = forcas_defesa[time] / pesos_defesa[time]
            # Normalizar pela média de gols para calibrar xG
            forca_ataque_global[time] = atk / MEDIA_GOLS_LIGA
            forca_defesa_global[time] = df / MEDIA_GOLS_LIGA

if not jogos.empty:
    calcular_forcas()

# =========================================================
# MARKOV FORMAÇÃO PROBABILÍSTICA (COM ESTADO)
# =========================================================
transicoes_formacao = defaultdict(lambda: defaultdict(list))
ultima_formacao_time = {}

times_unicos = pd.concat([jogos["time_casa"], jogos["time_fora"]]).unique() if not jogos.empty else []
for time in times_unicos:
    df_time = jogos[(jogos["time_casa"] == time) | (jogos["time_fora"] == time)].sort_values("data_jogo")
    historico = []
    for _, row in df_time.iterrows():
        form = row["formacao_casa"] if row["time_casa"] == time else row["formacao_fora"]
        historico.append(form)
        
    for i in range(len(historico) - 1):
        transicoes_formacao[time][historico[i]].append(historico[i+1])
        
    if historico:
        ultima_formacao_time[time] = historico[-1]
    else:
        ultima_formacao_time[time] = "4-3-3"

def prever_formacao(time, estado_atual=None):
    if not estado_atual:
        estado_atual = ultima_formacao_time.get(time, "4-3-3")
        
    if time not in transicoes_formacao:
        return '4-3-3'
        
    if estado_atual in transicoes_formacao[time]:
        destinos = transicoes_formacao[time][estado_atual]
    else:
        # fallback: juntar todas as transições se o estado não tiver caminho
        destinos = []
        for d_list in transicoes_formacao[time].values():
            destinos.extend(d_list)
            
    if not destinos:
        return '4-3-3'
        
    contagem = Counter(destinos)
    opcoes, pesos = zip(*contagem.items())
    return np.random.choice(opcoes, p=np.array(pesos)/sum(pesos))

def atualizar_estado_formacao(time, nova_formacao):
    ultima_formacao_time[time] = nova_formacao

# =========================================================
# DISTRIBUIÇÃO DE GOLS / ASSISTÊNCIAS E JOGADORES
# =========================================================
distribuicao_gols = defaultdict(lambda: defaultdict(float))
distribuicao_assists = defaultdict(lambda: defaultdict(float))

for _, row in jogos.iterrows():
    peso = peso_recencia(row["data_jogo"])
    gols = extrair_jogadores(row["gols"])
    assists = extrair_jogadores(row["assistencias"])
    
    time_c = row["time_casa"]
    time_f = row["time_fora"]
    
    for j in gols:
        if j in jogadores_convocados.get(time_c, []): distribuicao_gols[time_c][j] += peso
        if j in jogadores_convocados.get(time_f, []): distribuicao_gols[time_f][j] += peso
            
    for j in assists:
        if j in jogadores_convocados.get(time_c, []): distribuicao_assists[time_c][j] += peso
        if j in jogadores_convocados.get(time_f, []): distribuicao_assists[time_f][j] += peso

def sortear_jogador_evento(time, evento="gol"):
    dic_time = distribuicao_gols[time] if evento == "gol" else distribuicao_assists[time]
    
    if not dic_time or sum(dic_time.values()) == 0:
        convs = list(jogadores_convocados.get(time, ["Desconhecido"]))
        return np.random.choice(convs)
        
    opcoes = list(dic_time.keys())
    pesos = list(dic_time.values())
    
    if evento == "gol" and time in BATEDORES_PENALTI:
        if np.random.random() < 0.15:
            batedores_validos = [b for b in BATEDORES_PENALTI[time] if b in jogadores_convocados.get(time, [])]
            if batedores_validos:
                return np.random.choice(batedores_validos)
    
    probabilidades = np.array(pesos) / sum(pesos)
    return np.random.choice(opcoes, p=probabilidades)

# =========================================================
# SIMULAÇÃO MONTE CARLO (EXECUÇÃO GERAL)
# =========================================================

def simular_jogo(t1, t2):
    # Atualizar formações baseadas no estado da Cadeia de Markov
    form1 = prever_formacao(t1)
    form2 = prever_formacao(t2)
    atualizar_estado_formacao(t1, form1)
    atualizar_estado_formacao(t2, form2)
    
    # Dixon-Coles com média da liga (a força já embutiu o peso do ranking no treinamento)
    xg1 = (forca_ataque_global[t1] * forca_defesa_global[t2]) * MEDIA_GOLS_LIGA
    xg2 = (forca_ataque_global[t2] * forca_defesa_global[t1]) * MEDIA_GOLS_LIGA
    
    # Vantagem de mandante (Hosts) - aumenta xG em 8% e diminui do adversário
    if t1 in HOST_TEAMS:
        xg1 *= 1.08
        xg2 *= 0.92
    if t2 in HOST_TEAMS:
        xg2 *= 1.08
        xg1 *= 0.92
        
    gols1 = np.random.poisson(max(0.1, xg1))
    gols2 = np.random.poisson(max(0.1, xg2))
    
    return gols1, gols2

def simular_prorrogacao(t1, t2):
    # Prorrogação é aprox 30% do tempo de um jogo (30 mins vs 90 mins)
    xg1 = (forca_ataque_global[t1] * forca_defesa_global[t2]) * MEDIA_GOLS_LIGA * 0.33
    xg2 = (forca_ataque_global[t2] * forca_defesa_global[t1]) * MEDIA_GOLS_LIGA * 0.33
    
    if t1 in HOST_TEAMS:
        xg1 *= 1.08
        xg2 *= 0.92
    if t2 in HOST_TEAMS:
        xg2 *= 1.08
        xg1 *= 0.92
        
    return np.random.poisson(max(0.05, xg1)), np.random.poisson(max(0.05, xg2))

def simular_penaltis(t1, t2):
    # Simula 5 cobranças com base em % de acerto derivadas do ranking
    pts1 = obter_pontos_fifa(t1)
    pts2 = obter_pontos_fifa(t2)
    
    # Base de acerto de pênalti = 75%. Varia de acordo com o ranking (max 85%, min 65%)
    prob1 = min(0.85, max(0.65, 0.75 + (pts1 - 1500) / 4000.0))
    prob2 = min(0.85, max(0.65, 0.75 + (pts2 - 1500) / 4000.0))
    
    gols_p1 = sum(np.random.random() < prob1 for _ in range(5))
    gols_p2 = sum(np.random.random() < prob2 for _ in range(5))
    
    # Morte súbita se empatar
    while gols_p1 == gols_p2:
        gols_p1 += 1 if np.random.random() < prob1 else 0
        gols_p2 += 1 if np.random.random() < prob2 else 0
        
    return t1 if gols_p1 > gols_p2 else t2
