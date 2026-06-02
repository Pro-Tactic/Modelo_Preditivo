import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime
import random
import math
from scipy.optimize import minimize


# =========================================================
# CONFIG
# =========================================================

ARQUIVO_JOGOS = "arsenal_psg_jogos.csv"
ARQUIVO_TABELAS = "tabelas_finais.csv"

SIMULACOES = 100000

TIME_A = "Paris Saint-Germain"
TIME_B = "Arsenal"

TITULARES_ABSOLUTOS = [
    "Nuno Mendes", "Marquinhos", "Willian Pacho", 
    "Vitinha", "Désiré Doué", "João Neves", "Ousmane Dembélé", "Khvicha Kvaratskhelia", 
    "David Raya", "Gabriel Magalhães", "William Saliba", 
    "Declan Rice", "Bukayo Saka", "Viktor Gyökeres"
]


# =========================================================
# LESÕES / DESFALQUES
# =========================================================

usar_lesoes = input(
    "Existe algum jogador machucado/suspenso? (s/n): "
).strip().lower()

jogadores_fora = []

if usar_lesoes == "s":

    print()
    print(
        "Digite os nomes separados por vírgula."
    )

    print(
        "Exemplo: Bukayo Saka, Ousmane Dembélé"
    )

    entrada = input("Jogadores fora: ")

    jogadores_fora = [
        x.strip()
        for x in entrada.split(",")
        if x.strip()
    ]

print()

print("Jogadores indisponíveis:")

if jogadores_fora:

    for j in jogadores_fora:
        print("-", j)

else:
    print("Nenhum")

print()


# =========================================================
# LOAD
# =========================================================

jogos = pd.read_csv(ARQUIVO_JOGOS)
tabela = pd.read_csv(ARQUIVO_TABELAS)

jogos["data_jogo"] = pd.to_datetime(
    jogos["data_jogo"]
)

jogos = jogos.sort_values(
    "data_jogo",
    ascending=False
)


# =========================================================
# MAPA TÁTICO
# =========================================================

MAPA_FORMACAO = {

    "4-3-3": [
        "GK",
        "RB",
        "RCB",
        "LCB",
        "LB",
        "CM1",
        "CM2",
        "CM3",
        "RW",
        "ST",
        "LW"
    ],

    "4-2-3-1": [
        "GK",
        "RB",
        "RCB",
        "LCB",
        "LB",
        "VOL1",
        "VOL2",
        "RAM",
        "CAM",
        "LAM",
        "ST"
    ],

    "4-4-2": [
        "GK",
        "RB",
        "RCB",
        "LCB",
        "LB",
        "RM",
        "CM1",
        "CM2",
        "LM",
        "ST1",
        "ST2"
    ]
}


# =========================================================
# UTILIDADES
# =========================================================

def peso_recencia(
    data_jogo,
    fator=0.015
):

    dias = (
        datetime.now() - data_jogo
    ).days

    return math.exp(
        -fator * dias
    )


def separar_jogadores(texto):

    if pd.isna(texto):
        return []

    return [
        x.strip()
        for x in texto.split("|")
    ]


def parse_resultado(resultado):

    try:

        g1, g2 = resultado.split("x")

        return (
            int(g1.strip()),
            int(g2.strip())
        )

    except:

        return 0, 0


def extrair_gols(texto):

    if pd.isna(texto):
        return []

    eventos = texto.split("|")

    jogadores = []

    for ev in eventos:

        try:

            jogador = (
                ev.split("'")[-1]
                .strip()
            )

            jogadores.append(jogador)

        except:
            pass

    return jogadores


def extrair_assistencias(texto):

    if pd.isna(texto):
        return []

    eventos = texto.split("|")

    jogadores = []

    for ev in eventos:

        try:

            jogador = ev.split("->")[0]

            jogador = (
                jogador.split("'")[-1]
                .strip()
            )

            jogadores.append(jogador)

        except:
            pass

    return jogadores


# =========================================================
# MÉDIAS POR COMPETIÇÃO
# =========================================================

def calcular_medias_competicoes(tabela_df, jogos_df):
    medias = {}
    gols_total = 0
    jogos_total = 0

    # 1. Extrair das tabelas finais (Premier League, Ligue 1, Champions League)
    for comp in tabela_df['competicao'].unique():
        df_comp = tabela_df[tabela_df['competicao'] == comp]
        soma_gols_pro = df_comp['gols_pro'].sum()
        soma_jogos = df_comp['jogos'].sum()
        
        if soma_jogos > 0:
            media_comp = soma_gols_pro / (soma_jogos / 2)
            medias[comp] = media_comp
            gols_total += soma_gols_pro
            jogos_total += (soma_jogos / 2)

    # Media global considerando apenas as principais competições
    media_global = gols_total / jogos_total if jogos_total > 0 else 2.5
    
    return medias, media_global

MEDIAS_COMPETICAO, MEDIA_GLOBAL = calcular_medias_competicoes(tabela, jogos)


# =========================================================
# IMPORTÂNCIA DO JOGADOR
# =========================================================

def importancia_jogador(
    df,
    jogador
):

    score = 0
    soma_indices = 0
    qtd_titular = 0

    for _, row in df.iterrows():

        peso = peso_recencia(
            row["data_jogo"]
        )

        titulares_casa = (
            separar_jogadores(
                row["titulares_casa"]
            )
        )

        titulares_fora = (
            separar_jogadores(
                row["titulares_fora"]
            )
        )

        gols = extrair_gols(
            row["gols"]
        )

        assists = (
            extrair_assistencias(
                row["assistencias"]
            )
        )

        if jogador in titulares_casa:
            score += 1.5 * peso
            soma_indices += titulares_casa.index(jogador)
            qtd_titular += 1

        if jogador in titulares_fora:
            score += 1.5 * peso
            soma_indices += titulares_fora.index(jogador)
            qtd_titular += 1

        if jogador in gols:
            score += 3 * peso

        if jogador in assists:
            score += 2 * peso

    posicao_inferida = "MID"
    if qtd_titular > 0:
        idx_medio = soma_indices / qtd_titular
        if idx_medio <= 4.5:
            posicao_inferida = "DEF"
        elif idx_medio <= 8.5:
            posicao_inferida = "MID"
        else:
            posicao_inferida = "ATK"

    return score, posicao_inferida


# =========================================================
# TABELA / FORÇA ADVERSÁRIO
# =========================================================

def obter_posicao_time(time):

    nome_col = None
    pos_col = None

    for c in tabela.columns:

        cl = c.lower()

        if (
            "time" in cl or
            "team" in cl or
            "clube" in cl
        ):
            nome_col = c

        if (
            "pos" in cl or
            "rank" in cl
        ):
            pos_col = c

    if (
        nome_col is None or
        pos_col is None
    ):
        return 10

    linha = tabela[
        tabela[nome_col] == time
    ]

    if linha.empty:
        return 10

    return int(
        linha.iloc[0][pos_col]
    )


def peso_adversario(posicao):

    if posicao <= 3:
        return 1.5

    elif posicao <= 6:
        return 1.3

    elif posicao <= 10:
        return 1.1

    elif posicao <= 15:
        return 0.9

    return 0.7


# =========================================================
# JOGOS DO TIME
# =========================================================

def jogos_do_time(df, time):

    return df[
        (
            df["time_casa"] == time
        ) |
        (
            df["time_fora"] == time
        )
    ].copy()


arsenal = jogos_do_time(
    jogos,
    TIME_A
)

psg = jogos_do_time(
    jogos,
    TIME_B
)


# =========================================================
# MARKOV FORMAÇÃO
# =========================================================

def markov_formacao(
    df,
    time
):

    transicoes = defaultdict(
        Counter
    )

    historico = []

    for _, row in (
        df.sort_values("data_jogo")
        .iterrows()
    ):

        if row["time_casa"] == time:

            formacao = (
                row["formacao_casa"]
            )

        else:

            formacao = (
                row["formacao_fora"]
            )

        historico.append(
            formacao
        )

    for i in range(
        len(historico) - 1
    ):

        atual = historico[i]

        prox = historico[i + 1]

        transicoes[atual][prox] += 1

    ultima = historico[-1]

    if ultima not in transicoes:
        return ultima

    return (
        transicoes[ultima]
        .most_common(1)[0][0]
    )


formacao_arsenal = (
    markov_formacao(
        arsenal,
        TIME_A
    )
)

formacao_psg = (
    markov_formacao(
        psg,
        TIME_B
    )
)


# =========================================================
# ESCALAÇÃO POR SLOT TÁTICO
# =========================================================

def escalacao_tatica(
    df,
    time,
    formacao_prevista,
    adversario
):

    slots = MAPA_FORMACAO.get(
        formacao_prevista,
        MAPA_FORMACAO["4-3-3"]
    )

    pesos_slot = defaultdict(
        lambda: defaultdict(float)
    )

    pos_adv = obter_posicao_time(
        adversario
    )

    peso_adv = peso_adversario(
        pos_adv
    )

    for _, row in df.iterrows():

        peso = peso_recencia(
            row["data_jogo"]
        )

        peso *= peso_adv

        if row["time_casa"] == time:

            titulares = (
                separar_jogadores(
                    row["titulares_casa"]
                )
            )

            formacao = (
                row["formacao_casa"]
            )

        else:

            titulares = (
                separar_jogadores(
                    row["titulares_fora"]
                )
            )

            formacao = (
                row["formacao_fora"]
            )

        if (
            formacao !=
            formacao_prevista
        ):
            peso *= 0.5

        estrutura = (
            MAPA_FORMACAO.get(
                formacao
            )
        )

        if not estrutura:
            continue

        if (
            len(titulares) !=
            len(estrutura)
        ):
            continue

        for slot, jogador in zip(
            estrutura,
            titulares
        ):

            if (
                jogador not in
                jogadores_fora
            ):
                pesos_slot[slot][
                    jogador
                ] += peso

    escalacao = []

    usados = set()

    for slot in slots:

        candidatos_com_bonus = []
        for jogador, pontuacao in pesos_slot[slot].items():
            # Hierarquia: multiplica a pontuação final na posição por 5
            # Isso garante que ele vença os reservas, mas não roube posições (ex: Rice na LD) onde sua base é 0.1
            multiplicador = 5.0 if jogador in TITULARES_ABSOLUTOS else 1.0
            candidatos_com_bonus.append((jogador, pontuacao * multiplicador))

        candidatos = sorted(
            candidatos_com_bonus,
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
            escolhido = "N/D"

        escalacao.append(
            (
                slot,
                escolhido
            )
        )

    return escalacao


escalacao_arsenal = (
    escalacao_tatica(
        arsenal,
        TIME_A,
        formacao_arsenal,
        TIME_B
    )
)

escalacao_psg = (
    escalacao_tatica(
        psg,
        TIME_B,
        formacao_psg,
        TIME_A
    )
)


# =========================================================
# FORÇA OFENSIVA / DEFENSIVA
# =========================================================

def forca_time(
    df,
    time,
    jogadores_fora=None
):

    if jogadores_fora is None:
        jogadores_fora = []

    pesos = []

    gols_feitos = []

    gols_sofridos = []

    for _, row in df.iterrows():

        g1, g2 = parse_resultado(
            row["resultado"]
        )

        peso_rec = peso_recencia(
            row["data_jogo"]
        )
        
        comp = row["competicao"]
        if comp in MEDIAS_COMPETICAO:
            media_comp = MEDIAS_COMPETICAO[comp]
            fator_correcao = MEDIA_GLOBAL / media_comp if media_comp > 0 else 1.0
        else:
            if "Friendly" in comp or "Amistoso" in comp or "Emirates Cup" in comp:
                fator_correcao = 0.5
            else:
                fator_correcao = 1.0

        pesos.append(peso_rec)

        if row["time_casa"] == time:

            gols_feitos.append(
                g1 * fator_correcao * peso_rec
            )

            gols_sofridos.append(
                g2 * fator_correcao * peso_rec
            )

        else:

            gols_feitos.append(
                g2 * fator_correcao * peso_rec
            )

            gols_sofridos.append(
                g1 * fator_correcao * peso_rec
            )

    soma_pesos = sum(pesos)

    ataque = (
        sum(gols_feitos) / soma_pesos
    )

    defesa = (
        sum(gols_sofridos) / soma_pesos
    )

    penalizacao_ataque = 0
    penalizacao_defesa = 0

    for jogador in jogadores_fora:

        importancia, posicao = (
            importancia_jogador(
                df,
                jogador
            )
        )

        penalidade = importancia * 0.015

        if posicao == "DEF":
            penalizacao_defesa += penalidade * 0.8
            penalizacao_ataque += penalidade * 0.2
        elif posicao == "ATK":
            penalizacao_ataque += penalidade * 0.9
            penalizacao_defesa += penalidade * 0.1
        else:
            penalizacao_ataque += penalidade * 0.6
            penalizacao_defesa += penalidade * 0.4

    ataque *= max(
        0.45,
        1 - penalizacao_ataque
    )
    
    defesa *= (
        1 + penalizacao_defesa
    )

    return ataque, defesa


atk_a, def_a = forca_time(
    arsenal,
    TIME_A,
    jogadores_fora
)

atk_b, def_b = forca_time(
    psg,
    TIME_B,
    jogadores_fora
)


# =========================================================
# PROBABILIDADE GOL
# =========================================================

def probabilidades_gol(df):

    gols = defaultdict(float)

    for _, row in df.iterrows():

        peso = peso_recencia(
            row["data_jogo"]
        )

        eventos = extrair_gols(
            row["gols"]
        )

        for jogador in eventos:

            if (
                jogador not in
                jogadores_fora
            ):
                gols[jogador] += peso

    total = sum(gols.values())

    return {
        k: v / total
        for k, v in gols.items()
    }


# =========================================================
# PROBABILIDADE ASSISTÊNCIA
# =========================================================

def probabilidades_assistencia(df):

    assists = defaultdict(float)

    for _, row in df.iterrows():

        peso = peso_recencia(
            row["data_jogo"]
        )

        eventos = (
            extrair_assistencias(
                row["assistencias"]
            )
        )

        for jogador in eventos:

            if (
                jogador not in
                jogadores_fora
            ):
                assists[jogador] += peso

    total = sum(
        assists.values()
    )

    return {
        k: v / total
        for k, v in assists.items()
    }


prob_gol_arsenal = (
    probabilidades_gol(
        arsenal
    )
)

prob_gol_psg = (
    probabilidades_gol(
        psg
    )
)

prob_ast_arsenal = (
    probabilidades_assistencia(
        arsenal
    )
)

prob_ast_psg = (
    probabilidades_assistencia(
        psg
    )
)


# =========================================================
# MONTE CARLO
# =========================================================

def poisson_gols(media):

    return np.random.poisson(
        media
    )


media_arsenal = (
    atk_a + def_b
) / 2

media_psg = (
    atk_b + def_a
) / 2


resultados = Counter()

gols_jogadores = Counter()

assist_jogadores = Counter()

cnt_psg_liderou = 0
cnt_arsenal_liderou = 0
cnt_nenhum_liderou = 0

cnt_psg_primeiro = 0
cnt_arsenal_primeiro = 0
cnt_sem_gol = 0


for _ in range(SIMULACOES):

    gols_a = poisson_gols(
        media_arsenal
    )

    gols_b = poisson_gols(
        media_psg
    )

    placar = (
        f"{gols_a}x{gols_b}"
    )

    resultados[placar] += 1

    for _ in range(gols_a):

        jogador = random.choices(
            list(
                prob_gol_arsenal.keys()
            ),
            weights=list(
                prob_gol_arsenal.values()
            )
        )[0]

        assist = random.choices(
            list(
                prob_ast_arsenal.keys()
            ),
            weights=list(
                prob_ast_arsenal.values()
            )
        )[0]

        gols_jogadores[
            jogador
        ] += 1

        assist_jogadores[
            assist
        ] += 1

    for _ in range(gols_b):

        jogador = random.choices(
            list(
                prob_gol_psg.keys()
            ),
            weights=list(
                prob_gol_psg.values()
            )
        )[0]

        assist = random.choices(
            list(
                prob_ast_psg.keys()
            ),
            weights=list(
                prob_ast_psg.values()
            )
        )[0]

        gols_jogadores[
            jogador
        ] += 1

        assist_jogadores[
            assist
        ] += 1

    if gols_a == 0 and gols_b == 0:
        cnt_nenhum_liderou += 1
        cnt_sem_gol += 1
    else:
        gols_seq = ['P'] * gols_a + ['A'] * gols_b
        random.shuffle(gols_seq)

        # Primeiro gol da partida
        if gols_seq[0] == 'P':
            cnt_psg_primeiro += 1
        else:
            cnt_arsenal_primeiro += 1

        score_psg = 0
        score_ars = 0
        psg_lid = False
        ars_lid = False

        for gol in gols_seq:
            if gol == 'P':
                score_psg += 1
            else:
                score_ars += 1

            if score_psg > score_ars:
                psg_lid = True
            elif score_ars > score_psg:
                ars_lid = True

        if psg_lid:
            cnt_psg_liderou += 1
        if ars_lid:
            cnt_arsenal_liderou += 1

# =========================================================
# PRORROGAÇÃO E PÊNALTIS
# =========================================================

resultado_mais_comum = (
    resultados.most_common(1)[0][0]
)

g_a, g_b = (
    resultado_mais_comum
    .split("x")
)

g_a = int(g_a)
g_b = int(g_b)

resultado_prorrogacao = None

penaltis = None

if g_a == g_b:

    media_prorro_arsenal = (
        media_arsenal * 0.33
    )

    media_prorro_psg = (
        media_psg * 0.33
    )

    resultados_prorro = Counter()

    for _ in range(SIMULACOES):

        ga = poisson_gols(
            media_prorro_arsenal
        )

        gb = poisson_gols(
            media_prorro_psg
        )

        placar = f"{ga}x{gb}"

        resultados_prorro[
            placar
        ] += 1

    resultado_prorrogacao = (
        resultados_prorro
        .most_common(1)[0][0]
    )

    ga_p, gb_p = (
        resultado_prorrogacao
        .split("x")
    )

    ga_p = int(ga_p)
    gb_p = int(gb_p)

    if ga_p == gb_p:

        força_penalti_arsenal = (
            atk_a * 0.6 +
            (
                1 / max(def_a, 0.1)
            ) * 0.4
        )

        força_penalti_psg = (
            atk_b * 0.6 +
            (
                1 / max(def_b, 0.1)
            ) * 0.4
        )

        penalti_arsenal = 0
        penalti_psg = 0

        for _ in range(SIMULACOES):

            score_a = 0
            score_b = 0

            for i in range(5):

                prob_a = min(
                    0.92,
                    0.55 + (
                        força_penalti_arsenal
                        * 0.08
                    )
                )

                prob_b = min(
                    0.92,
                    0.55 + (
                        força_penalti_psg
                        * 0.08
                    )
                )

                if (
                    random.random()
                    < prob_a
                ):
                    score_a += 1

                if (
                    random.random()
                    < prob_b
                ):
                    score_b += 1

            while (
                score_a ==
                score_b
            ):

                if (
                    random.random()
                    < prob_a
                ):
                    score_a += 1

                if (
                    random.random()
                    < prob_b
                ):
                    score_b += 1

            if score_a > score_b:
                penalti_arsenal += 1

            else:
                penalti_psg += 1

        prob_penalti_arsenal = (
            penalti_arsenal /
            SIMULACOES
        ) * 100

        prob_penalti_psg = (
            penalti_psg /
            SIMULACOES
        ) * 100

        if (
            penalti_arsenal >
            penalti_psg
        ):
            penaltis = TIME_A

        else:
            penaltis = TIME_B


# =========================================================
# VITÓRIA
# =========================================================

v_a = 0
v_b = 0
emp = 0

for placar, qtd in (
    resultados.items()
):

    g1, g2 = placar.split("x")

    g1 = int(g1)
    g2 = int(g2)

    if g1 > g2:
        v_a += qtd

    elif g2 > g1:
        v_b += qtd

    else:
        emp += qtd


# =========================================================
# REGRESSÃO POISSON LOG-LINEAR COMPARATIVA
# =========================================================

def calcular_poisson_loglinear(df_jogos):
    
    # Extrair os gols ajustados das duas equipes em seus históricos
    gols_A = []
    gols_B = []
    
    for _, row in df_jogos.iterrows():
        g1, g2 = parse_resultado(row["resultado"])
        comp = row["competicao"]
        if comp in MEDIAS_COMPETICAO:
            media_comp = MEDIAS_COMPETICAO[comp]
            fator = MEDIA_GLOBAL / media_comp if media_comp > 0 else 1.0
        else:
            if "Friendly" in comp or "Amistoso" in comp or "Emirates Cup" in comp:
                fator = 0.5
            else:
                fator = 1.0
        
        if row["time_casa"] == TIME_A:
            gols_A.append(g1 * fator)
        elif row["time_fora"] == TIME_A:
            gols_A.append(g2 * fator)
            
        if row["time_casa"] == TIME_B:
            gols_B.append(g1 * fator)
        elif row["time_fora"] == TIME_B:
            gols_B.append(g2 * fator)
            
    lambda_a_inicial = np.mean(gols_A) if gols_A else 1.0
    lambda_b_inicial = np.mean(gols_B) if gols_B else 1.0
    
    # Função objetivo (Negative Log-Likelihood para Poisson)
    def nll_poisson(params, observacoes):
        L = params[0]
        if L <= 0: return np.inf
        # sum( L - y * log(L) ) ignorando log(y!)
        return np.sum(L - observacoes * np.log(L))
        
    res_a = minimize(nll_poisson, [lambda_a_inicial], args=(np.array(gols_A),), method='Nelder-Mead')
    res_b = minimize(nll_poisson, [lambda_b_inicial], args=(np.array(gols_B),), method='Nelder-Mead')
    
    l_a = res_a.x[0] if res_a.success else lambda_a_inicial
    l_b = res_b.x[0] if res_b.success else lambda_b_inicial
    
    return l_a, l_b

poisson_a, poisson_b = calcular_poisson_loglinear(jogos)

# =========================================================
# RELATÓRIO
# =========================================================

print("\n" + "=" * 80)
print(" " * 24 + "PREVISÃO DA PARTIDA")
print("=" * 80)

print(
    f"\nJOGO: "
    f"{TIME_A} x {TIME_B}"
)

print("\n" + "-" * 80)
print("DESFALQUES CONSIDERADOS")
print("-" * 80)

if jogadores_fora:

    for j in jogadores_fora:
        print(f"• {j}")

else:
    print(
        "Nenhum desfalque informado."
    )

print("\n" + "-" * 80)
print("FORMAÇÕES MAIS PROVÁVEIS")
print("-" * 80)

print(
    f"{TIME_A}: "
    f"{formacao_arsenal}"
)

print(
    f"{TIME_B}: "
    f"{formacao_psg}"
)

print("\n" + "-" * 80)
print("ESCALAÇÕES TÁTICAS PROVÁVEIS")
print("-" * 80)

print(f"\n{TIME_A}")

for slot, jogador in (
    escalacao_arsenal
):

    print(
        f"{slot:<6} | "
        f"{jogador}"
    )

print(f"\n{TIME_B}")

for slot, jogador in (
    escalacao_psg
):

    print(
        f"{slot:<6} | "
        f"{jogador}"
    )

print("\n" + "-" * 80)
print("FORÇA OFENSIVA / DEFENSIVA")
print("-" * 80)

print(
    f"{TIME_A:<22} "
    f"Ataque: {atk_a:.2f} | "
    f"Defesa: {def_a:.2f}"
)

print(
    f"{TIME_B:<22} "
    f"Ataque: {atk_b:.2f} | "
    f"Defesa: {def_b:.2f}"
)

print()

print(
    f"Média esperada de gols "
    f"{TIME_A}: "
    f"{media_arsenal:.2f}"
)

print(
    f"Média esperada de gols "
    f"{TIME_B}: "
    f"{media_psg:.2f}"
)

print("\n" + "-" * 80)
print("PLACARES MAIS PROVÁVEIS")
print("-" * 80)

for i, (
    placar,
    qtd
) in enumerate(
    resultados.most_common(10),
    start=1
):

    prob = (
        qtd / SIMULACOES
    ) * 100

    print(
        f"{i:>2}. "
        f"{placar:<8} "
        f"-> "
        f"{prob:>6.2f}%"
    )

print("\n" + "-" * 80)
print("ARTILHEIROS MAIS PROVÁVEIS")
print("-" * 80)

for i, (
    jogador,
    qtd
) in enumerate(
    gols_jogadores
    .most_common(10),
    start=1
):

    prob = (
        qtd /
        sum(
            gols_jogadores.values()
        )
    ) * 100

    print(
        f"{i:>2}. "
        f"{jogador:<30} "
        f"{prob:>6.2f}%"
    )

print("\n" + "-" * 80)
print("ASSISTÊNCIAS MAIS PROVÁVEIS")
print("-" * 80)

for i, (
    jogador,
    qtd
) in enumerate(
    assist_jogadores
    .most_common(10),
    start=1
):

    prob = (
        qtd /
        sum(
            assist_jogadores.values()
        )
    ) * 100

    print(
        f"{i:>2}. "
        f"{jogador:<30} "
        f"{prob:>6.2f}%"
    )

print("\n" + "-" * 80)
print("PROBABILIDADES FINAIS")
print("-" * 80)

prob_v_a = (
    v_a / SIMULACOES
) * 100

prob_emp = (
    emp / SIMULACOES
) * 100

prob_v_b = (
    v_b / SIMULACOES
) * 100

prob_psg_liderou = (
    cnt_psg_liderou / SIMULACOES
) * 100

prob_arsenal_liderou = (
    cnt_arsenal_liderou / SIMULACOES
) * 100

prob_nenhum_liderou = (
    cnt_nenhum_liderou / SIMULACOES
) * 100

prob_psg_primeiro = (
    cnt_psg_primeiro / SIMULACOES
) * 100

prob_arsenal_primeiro = (
    cnt_arsenal_primeiro / SIMULACOES
) * 100

prob_sem_gol = (
    cnt_sem_gol / SIMULACOES
) * 100

print(
    f"Vitória {TIME_A:<20} "
    f"{prob_v_a:>6.2f}%"
)

print(
    f"Empate{'':<22} "
    f"{prob_emp:>6.2f}%"
)

print(
    f"Vitória {TIME_B:<20} "
    f"{prob_v_b:>6.2f}%"
)

if resultado_prorrogacao:

    print("\n" + "-" * 80)
    print("CENÁRIO DE MATA-MATA")
    print("-" * 80)

    print(
        f"Prorrogação mais provável: "
        f"{resultado_prorrogacao}"
    )

    if penaltis:

        print(
            f"Maior probabilidade "
            f"nos pênaltis: "
            f"{penaltis}"
        )

placar_mais_comum = (
    resultados
    .most_common(1)[0][0]
)

artilheiro = (
    gols_jogadores
    .most_common(1)[0][0]
)

assistencia = (
    assist_jogadores
    .most_common(1)[0][0]
)

print("\n" + "=" * 80)
print(" " * 30 + "ANÁLISE FINAL")
print("=" * 80)

print()

print(
    f"• Placar mais provável: "
    f"{placar_mais_comum}"
)

print(
    f"• Jogador com maior chance "
    f"de marcar: "
    f"{artilheiro}"
)

print(
    f"• Jogador com maior chance "
    f"de assistência: "
    f"{assistencia}"
)

print()

if prob_v_a > prob_v_b:

    favorito = TIME_A
    chance = prob_v_a

elif prob_v_b > prob_v_a:

    favorito = TIME_B
    chance = prob_v_b

else:

    favorito = "Nenhum"
    chance = prob_emp

print(
    f"• Favorito estatístico: "
    f"{favorito} "
    f"({chance:.2f}%)"
)

print()

print("MODELO UTILIZADO")

print(
    "• Peso temporal exponencial"
)

print(
    "• Cadeia de Markov"
)

print(
    "• Escalação por SLOT tático"
)

print(
    "• Peso por força do adversário"
)

print(
    "• Penalização por desfalques"
)

print(
    f"• {SIMULACOES} simulações "
    f"Monte Carlo"
)

print("\n" + "-" * 80)
print("COMPARAÇÃO DE MODELOS (MÉDIA DE GOLS)")
print("-" * 80)

print(f"Pesos dinâmicos calculados por Competição:")
for c, m in sorted(MEDIAS_COMPETICAO.items(), key=lambda x: x[1], reverse=True):
    # Fator é a média global / média da competição
    fator = MEDIA_GLOBAL / m if m > 0 else 1.0
    print(f"  {c:<35}: Média {m:.2f} gols/jogo (Fator Dificuldade: x{fator:.2f})")

print(f"\nExpectativa de Gols {TIME_A}:")
print(f"  - Monte Carlo Ponderado : {media_arsenal:.2f}")
print(f"  - Poisson Log-Linear    : {poisson_a:.2f}")

print(f"\nExpectativa de Gols {TIME_B}:")
print(f"  - Monte Carlo Ponderado : {media_psg:.2f}")
print(f"  - Poisson Log-Linear    : {poisson_b:.2f}")

print("=" * 80)