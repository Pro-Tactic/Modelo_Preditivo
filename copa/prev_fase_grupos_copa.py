import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime
import math
import mlflow
import os

# =========================================================
# CONFIGURAÇÕES E CONSTANTES
# =========================================================
ARQUIVO_JOGOS = "copa/jogos.csv"
ARQUIVO_CLASSIFICACAO = "copa/classificacao.csv"
ARQUIVO_CONVOCACAO = "copa/convocacao.csv"

SIMULACOES = 2000

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

# =========================================================
# CARGA DE DADOS
# =========================================================
print("Carregando bases de dados...")
jogos = pd.read_csv(ARQUIVO_JOGOS)
tabela_completa = pd.read_csv(ARQUIVO_CLASSIFICACAO)
convocacao = pd.read_csv(ARQUIVO_CONVOCACAO)

jogos["data_jogo"] = pd.to_datetime(jogos["data_jogo"])

# Grupos da Copa
grupos_copa = tabela_completa[tabela_completa["liga"] == "Copa do Mundo FIFA 2026"].copy()
selecoes_copa = grupos_copa["time"].unique()

# Jogadores Convocados por Seleção
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
# FORÇA DOS TIMES E CICLO DA COPA
# =========================================================
print("Calculando forças das seleções...")

# Tier List explícita para forçar o "abismo" entre seleções de elite e zebras
PESOS_SELECOES = {
    # Tier S (Elite Mundial)
    "Argentina": 5.0, "France": 5.0, "Brazil": 5.0, "England": 5.0, "Spain": 5.0, "Germany": 5.0, "Portugal": 5.0,
    # Tier A (Muito Fortes)
    "Netherlands": 4.0, "Belgium": 4.0, "Italy": 4.0, "Uruguay": 4.0, "Colombia": 4.0, "Croatia": 4.0,
    # Tier B (Competitivos / Cascas Grossas)
    "Switzerland": 3.0, "Japan": 3.0, "Senegal": 3.0, "Morocco": 3.0, "USA": 3.0, "Mexico": 3.0, "Ecuador": 3.0, "South Korea": 3.0, "Austria": 3.0, "Türkiye": 3.0,
    # Tier C (Médios)
    "Côte d'Ivoire": 2.0, "Australia": 2.0, "Canada": 2.0, "Egypt": 2.0, "Algeria": 2.0, "Czechia": 2.0, "Ghana": 2.0, "Sweden": 2.0, "Norway": 2.0, "Scotland": 2.0, "Bosnia & Herzegovina": 2.0, "Paraguay": 2.0, "Iran": 2.0,
    # Tier D (Fracos)
    "Panama": 1.0, "DR Congo": 1.0, "South Africa": 1.0, "Tunisia": 1.0, "Qatar": 1.0, "Saudi Arabia": 1.0, "Iraq": 1.0, "Uzbekistan": 1.0,
    # Tier F (Zebras Totais)
    "Haiti": 0.3, "Cabo Verde": 0.3, "Curaçao": 0.3, "Jordan": 0.3, "New Zealand": 0.3
}

forca_ataque_global = defaultdict(float)
forca_defesa_global = defaultdict(float)

def obter_forca_time(time):
    gols_feitos = []
    gols_sofridos = []
    pesos = []
    
    # Pegar todos os jogos do time
    df_time = jogos[(jogos["time_casa"] == time) | (jogos["time_fora"] == time)]
    
    if df_time.empty:
        return 1.0, 1.0 # Default
        
    for _, row in df_time.iterrows():
        g1, g2 = parse_resultado(row["resultado"])
        peso = peso_recencia(row["data_jogo"])
        
        # Ajuste de peso do adversário baseado na Tier List
        adv = row["time_fora"] if row["time_casa"] == time else row["time_casa"]
        peso_adv = PESOS_SELECOES.get(adv, 1.0)
        
        peso_total = peso * peso_adv
        pesos.append(peso_total)
        
        if row["time_casa"] == time:
            gols_feitos.append(g1 * peso_total)
            gols_sofridos.append(g2 * peso_total / max(0.5, peso_adv)) # Sofrer gol de time ruim pesa muito
        else:
            gols_feitos.append(g2 * peso_total)
            gols_sofridos.append(g1 * peso_total / max(0.5, peso_adv))
            
    soma_pesos = sum(pesos)
    if soma_pesos > 0:
        ataque = sum(gols_feitos) / soma_pesos
        defesa = sum(gols_sofridos) / soma_pesos
        return max(0.2, ataque), max(0.2, defesa)
    return 1.0, 1.0

for time in selecoes_copa:
    atk, df = obter_forca_time(time)
    forca_ataque_global[time] = atk
    forca_defesa_global[time] = df

# =========================================================
# MARKOV FORMAÇÃO PROBABILÍSTICA
# =========================================================
print("Gerando Matrizes de Transição de Formações...")
transicoes_formacao = defaultdict(lambda: defaultdict(list))

for time in selecoes_copa:
    df_time = jogos[(jogos["time_casa"] == time) | (jogos["time_fora"] == time)].sort_values("data_jogo")
    historico = []
    for _, row in df_time.iterrows():
        form = row["formacao_casa"] if row["time_casa"] == time else row["formacao_fora"]
        historico.append(form)
        
    for i in range(len(historico) - 1):
        transicoes_formacao[time][historico[i]].append(historico[i+1])

def prever_formacao(time):
    # Se não temos histórico suficiente, chutar o clássico
    if time not in transicoes_formacao or not transicoes_formacao[time]:
        return "4-3-3"
    
    # Pega o histórico, se a matriz do estado atual (última formação) existir, sorteia dela
    # Como simplificação, fazemos um Counter de todas as transições e sorteamos com pesos
    todas_formacoes = []
    for f_orig, f_dest_list in transicoes_formacao[time].items():
        todas_formacoes.extend(f_dest_list)
        
    if not todas_formacoes:
        return "4-3-3"
        
    contagem = Counter(todas_formacoes)
    opcoes = list(contagem.keys())
    pesos = list(contagem.values())
    probabilidades = np.array(pesos) / sum(pesos)
    
    return np.random.choice(opcoes, p=probabilidades)

# =========================================================
# DISTRIBUIÇÃO DE GOLS / ASSISTÊNCIAS E JOGADORES
# =========================================================
print("Processando perfis ofensivos dos jogadores...")
distribuicao_gols = defaultdict(lambda: defaultdict(float))
distribuicao_assists = defaultdict(lambda: defaultdict(float))

for _, row in jogos.iterrows():
    peso = peso_recencia(row["data_jogo"])
    gols = extrair_jogadores(row["gols"])
    assists = extrair_jogadores(row["assistencias"])
    
    # Atribuir para casa
    time_c = row["time_casa"]
    for j in gols:
        if j in jogadores_convocados.get(time_c, []):
            distribuicao_gols[time_c][j] += peso
    for j in assists:
        if j in jogadores_convocados.get(time_c, []):
            distribuicao_assists[time_c][j] += peso
            
    # Atribuir para fora
    time_f = row["time_fora"]
    for j in gols:
        if j in jogadores_convocados.get(time_f, []):
            distribuicao_gols[time_f][j] += peso
    for j in assists:
        if j in jogadores_convocados.get(time_f, []):
            distribuicao_assists[time_f][j] += peso

def sortear_jogador_evento(time, evento="gol"):
    dic_time = distribuicao_gols[time] if evento == "gol" else distribuicao_assists[time]
    
    # Se o time não tiver histórico de gols mapeado com esses jogadores, escolhe um jogador convocado aleatório de ataque
    if not dic_time or sum(dic_time.values()) == 0:
        convs = list(jogadores_convocados.get(time, ["Desconhecido"]))
        return np.random.choice(convs)
        
    opcoes = list(dic_time.keys())
    pesos = list(dic_time.values())
    
    # Bônus para batedores de pênalti (se for gol)
    if evento == "gol" and time in BATEDORES_PENALTI:
        is_penalti = np.random.random() < 0.15 # 15% dos gols são de pênalti
        if is_penalti:
            batedores = BATEDORES_PENALTI[time]
            batedores_validos = [b for b in batedores if b in jogadores_convocados.get(time, [])]
            if batedores_validos:
                return np.random.choice(batedores_validos)
    
    probabilidades = np.array(pesos) / sum(pesos)
    return np.random.choice(opcoes, p=probabilidades)

# =========================================================
# SIMULAÇÃO MONTE CARLO (EXECUÇÃO GERAL)
# =========================================================

def simular_jogo(t1, t2):
    # Fator Tático Aleatório (Markov)
    form1 = prever_formacao(t1)
    form2 = prever_formacao(t2)
    
    # Ajuste agressivo de disparidade de força usando a Tier List
    rk1 = PESOS_SELECOES.get(t1, 1.0)
    rk2 = PESOS_SELECOES.get(t2, 1.0)
    # Multiplicador que favorece muito o time mais forte e enfraquece o mais fraco
    mult_t1 = (rk1 / rk2) ** 0.6
    mult_t2 = (rk2 / rk1) ** 0.6
    
    # Expectativa de Gols baseada no Histórico + Multiplicador de Confederação
    xg1 = (forca_ataque_global[t1] * forca_defesa_global[t2]) * mult_t1
    xg2 = (forca_ataque_global[t2] * forca_defesa_global[t1]) * mult_t2
    
    # Sorteio Poisson
    gols1 = np.random.poisson(xg1)
    gols2 = np.random.poisson(xg2)
    
    return gols1, gols2

# Pré-organizar confrontos da fase de grupos
confrontos_por_grupo = defaultdict(list)
for grupo_nome in grupos_copa["grupo"].unique():
    times_do_grupo = grupos_copa[grupos_copa["grupo"] == grupo_nome]["time"].tolist()
    # Combinações 2 a 2
    for i in range(len(times_do_grupo)):
        for j in range(i+1, len(times_do_grupo)):
            confrontos_por_grupo[grupo_nome].append((times_do_grupo[i], times_do_grupo[j]))

if __name__ == "__main__":
    print(f"Iniciando Motor de Simulação Monte Carlo ({SIMULACOES} rodadas)...")

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
            # Tabela interna da simulação atual
            tabela_sim = {time: {"pts": 0, "sg": 0, "gp": 0} for time in selecoes_copa}
            
            for grupo, confrontos in confrontos_por_grupo.items():
                for t1, t2 in confrontos:
                    
                    gols1, gols2 = simular_jogo(t1, t2)
                    
                    total_gols_simulados += (gols1 + gols2)
                    total_jogos_simulados += 1
                    
                    # Salvar placar para achar o mais provável
                    placares_provaveis[f"{t1} x {t2}"][f"{gols1} x {gols2}"] += 1
                    
                    # Atualizar pontos e saldo
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
                        
                    # Atribuir artilheiros e assistentes
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
            
            # Terminou a fase de grupos desta simulação. Calcular quem passou.
            terceiros_colocados = []
            for grupo, confrontos in confrontos_por_grupo.items():
                times_do_grupo = list(set([c[0] for c in confrontos] + [c[1] for c in confrontos]))
                # Ordenar por: pts (desc), sg (desc), gp (desc)
                classificacao = sorted(times_do_grupo, key=lambda x: (tabela_sim[x]["pts"], tabela_sim[x]["sg"], tabela_sim[x]["gp"]), reverse=True)
                
                # Registrar Posições
                for i, time in enumerate(classificacao):
                    pos = i + 1
                    resultados_grupos[time]["posicao_grupo"].append(pos)
                    resultados_grupos[time]["pontos"].append(tabela_sim[time]["pts"])
                    resultados_grupos[time]["saldo"].append(tabela_sim[time]["sg"])
                    resultados_grupos[time]["gols_pro"].append(tabela_sim[time]["gp"])
                    
                    # Top 2 passam direto
                    if pos <= 2:
                        resultados_grupos[time]["avancou"] += 1
                    # 3º vai para a repescagem
                    elif pos == 3:
                        terceiros_colocados.append(time)
            
            # 8 melhores terceiros passam
            terceiros_ordenados = sorted(terceiros_colocados, key=lambda x: (tabela_sim[x]["pts"], tabela_sim[x]["sg"], tabela_sim[x]["gp"]), reverse=True)
            for t in terceiros_ordenados[:8]:
                resultados_grupos[t]["avancou"] += 1
                
        mlflow.log_metric("media_gols_por_jogo", total_gols_simulados / total_jogos_simulados)
        
        # =========================================================
        # COMPILAÇÃO DOS RESULTADOS
        # =========================================================
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
        df_finais.to_csv("probabilidades_grupos_copa.csv", index=False)
        mlflow.log_artifact("probabilidades_grupos_copa.csv")
        
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
        
        # Placares Mais Prováveis
        placares_lista = []
        for jogo, placares in placares_provaveis.items():
            placar_mais_comum = placares.most_common(1)[0]
            placares_lista.append({
                "Confronto": jogo,
                "Placar Mais Provável": placar_mais_comum[0],
                "Frequência (%)": round((placar_mais_comum[1] / SIMULACOES) * 100, 2)
            })
    
        df_placares = pd.DataFrame(placares_lista).sort_values("Confronto")
        df_placares.to_csv("placares_provaveis.csv", index=False)
        mlflow.log_artifact("placares_provaveis.csv")
        print("Concluído! Tabelas geradas localmente e registradas no MLflow.").artifact("placares_provaveis.csv")

print("Concluído! Tabelas geradas localmente e registradas no MLflow.")