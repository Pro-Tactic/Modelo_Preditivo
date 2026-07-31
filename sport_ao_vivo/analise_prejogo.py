import os
from datetime import datetime, timezone

import config
import contexto_dados
import llm_client

SYSTEM = (
    f"Voce e o analista de dados da comissao tecnica do {config.TIME_ANALISE}, "
    f"assessorando o tecnico {config.TECNICO_ANALISE}. Escreva em portugues do Brasil, "
    "de forma objetiva e acionavel, sempre baseado nos dados fornecidos."
)

PROMPT_INSTRUCAO = (
    "Com base EXCLUSIVAMENTE nos dados abaixo, escreva um relatorio pre-jogo de 1 a 2 paginas "
    "em Markdown para a comissao tecnica, com as secoes:\n"
    "1. Panorama do confronto e momento das equipes\n"
    "2. Analise tatica das formacoes (nossas x adversario)\n"
    "3. Jogadores decisivos (artilheiros e assistentes) e risco disciplinar\n"
    "4. Padrao de gols (faixas de minuto e 1o/2o tempo) e implicacoes\n"
    "5. Historico de confrontos diretos\n"
    "6. Impacto dos desfalques na provavel escalacao\n"
    "7. Prognostico e 3 recomendacoes taticas objetivas\n"
    "Nao invente numeros que nao estejam nos dados."
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build_prompt(context_text):
    return f"{PROMPT_INSTRUCAO}\n\n===== DADOS =====\n{context_text}"


def build_offline_report(tables, context_text):
    time = config.TIME_ANALISE
    opponent = "Goias" if "sport" in time.lower() else "Sport"

    def team_row(rows, team):
        found = contexto_dados.filter_team(rows, team)
        return found[0] if found else {}

    resumo_time = team_row(tables["resumo"], time)
    resumo_opp = team_row(tables["resumo"], opponent)
    forma_time = team_row(tables["forma"], time)
    forma_opp = team_row(tables["forma"], opponent)
    formacoes_time = contexto_dados.filter_team(tables["formacoes"], time)
    formacoes_opp = contexto_dados.filter_team(tables["formacoes"], opponent)
    artilheiros_time = contexto_dados.filter_team(tables["artilheiros"], time)[:5]
    disciplina_time = contexto_dados.filter_team(tables["disciplina"], time)[:5]
    subs_time = team_row(tables["subs_padrao"], time)

    def formacao_principal(rows):
        return rows[0].get("formacao") if rows else "n/d"

    linhas = []
    linhas.append("> Gerado em modo OFFLINE (heuristico, sem IA). Configure GEMINI_API_KEY para o relatorio narrativo completo.\n")

    linhas.append("## 1. Panorama do confronto")
    if resumo_opp and resumo_time:
        linhas.append(
            f"- **{resumo_opp.get('time')}**: {resumo_opp.get('pontos')} pts, "
            f"{resumo_opp.get('vitorias')}V-{resumo_opp.get('empates')}E-{resumo_opp.get('derrotas')}D, "
            f"saldo {resumo_opp.get('saldo')}."
        )
        linhas.append(
            f"- **{resumo_time.get('time')}**: {resumo_time.get('pontos')} pts, "
            f"{resumo_time.get('vitorias')}V-{resumo_time.get('empates')}E-{resumo_time.get('derrotas')}D, "
            f"saldo {resumo_time.get('saldo')}."
        )
    linhas.append(
        f"- Forma recente (ult. 5): {resumo_opp.get('time','Adversario')} `{forma_opp.get('sequencia','')}` "
        f"({forma_opp.get('pontos','?')} pts) x {resumo_time.get('time', time)} `{forma_time.get('sequencia','')}` "
        f"({forma_time.get('pontos','?')} pts)."
    )

    linhas.append("\n## 2. Analise tatica das formacoes")
    linhas.append(f"- Formacao mais usada por {resumo_opp.get('time', opponent)}: **{formacao_principal(formacoes_opp)}**.")
    linhas.append(f"- Formacao mais usada por {resumo_time.get('time', time)}: **{formacao_principal(formacoes_time)}**.")

    linhas.append("\n## 3. Jogadores decisivos e disciplina")
    if artilheiros_time:
        artil = ", ".join(f"{r['jogador']} ({r['gols']}g)" for r in artilheiros_time)
        linhas.append(f"- Principais finalizadores do {time}: {artil}.")
    if disciplina_time:
        disc = ", ".join(f"{r['jogador']} ({r['cartoes_amarelos']}A)" for r in disciplina_time)
        linhas.append(f"- Atencao disciplinar: {disc}.")

    linhas.append("\n## 4. Padrao de gols")
    faixa_time = [r for r in tables["gols_faixa"] if contexto_dados._matches_team(r, time)]
    if faixa_time:
        pico = max(faixa_time, key=lambda r: int(r.get("gols") or 0))
        linhas.append(f"- {time} concentra gols na faixa **{pico.get('faixa_minuto')}** ({pico.get('gols')} gols, {pico.get('pct')}%).")
    tempo_time = [r for r in tables["gols_tempo"] if contexto_dados._matches_team(r, time)]
    for r in tempo_time:
        linhas.append(f"- {time} no {r.get('tempo')}: {r.get('gols')} gols ({r.get('pct')}%).")

    linhas.append("\n## 5. Confrontos diretos")
    for r in tables["h2h_resumo"]:
        linhas.append(
            f"- Fonte {r.get('fonte')}: {r.get('total_jogos')} jogos, "
            f"Goias {r.get('vitorias_goias')} x {r.get('vitorias_sport')} Sport ({r.get('empates')} empates)."
        )

    linhas.append("\n## 6. Impacto dos desfalques")
    for r in tables["desfalques"]:
        linhas.append(f"- {r.get('jogador')} ({r.get('time')}): {r.get('motivo')} — {r.get('status')}.")

    linhas.append("\n## 7. Prognostico e recomendacoes")
    if subs_time:
        linhas.append(
            f"- Janela de substituicoes do {time}: 1a ~{subs_time.get('minuto_medio_1a_sub')}', "
            f"2a ~{subs_time.get('minuto_medio_2a_sub')}', 3a ~{subs_time.get('minuto_medio_3a_sub')}'."
        )
    linhas.append("- Recomendacao 1: explorar as faixas de minuto de maior produtividade ofensiva.")
    linhas.append("- Recomendacao 2: reforcar a marcacao nas faixas em que a equipe mais sofre gols.")
    linhas.append("- Recomendacao 3: monitorar cartoes dos jogadores listados para evitar suspensoes/expulsoes.")

    return "\n".join(linhas)


def gerar_relatorio():
    tables = contexto_dados.load_all()
    context_text = contexto_dados.pregame_context_text(tables)

    header = (
        f"# Relatorio Pre-Jogo — {tables['contexto'][0].get('partida') if tables['contexto'] else 'Partida'}\n"
        f"_Gerado em {_now()} | IA: {llm_client.status()}_\n"
    )

    if llm_client.is_available():
        try:
            narrativa = llm_client.generate(build_prompt(context_text), system=SYSTEM, temperature=0.6)
            origem = "gemini"
        except Exception as error:
            narrativa = build_offline_report(tables, context_text) + f"\n\n> Falha ao chamar Gemini: {error}"
            origem = "offline_fallback"
    else:
        narrativa = build_offline_report(tables, context_text)
        origem = "offline"

    conteudo = (
        f"{header}\n{narrativa}\n\n---\n\n"
        f"## Anexo — Dados utilizados\n\n```\n{context_text}\n```\n"
    )

    os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
    with open(config.PREJOGO_REPORT_PATH, "w", encoding="utf-8") as handle:
        handle.write(conteudo)

    print(f"Relatorio gerado ({origem}) em {config.PREJOGO_REPORT_PATH}")
    return config.PREJOGO_REPORT_PATH


if __name__ == "__main__":
    gerar_relatorio()
