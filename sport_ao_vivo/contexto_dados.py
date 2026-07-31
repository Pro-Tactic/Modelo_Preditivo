import csv
import json
import os
import unicodedata

import config

TABELAS = {
    "resumo": "01_times/times_resumo_temporada.csv",
    "mando": "01_times/times_desempenho_mando.csv",
    "forma": "01_times/times_forma_recente.csv",
    "jogadores": "02_jogadores/jogadores_estatisticas.csv",
    "artilheiros": "02_jogadores/jogadores_artilheiros.csv",
    "assistentes": "02_jogadores/jogadores_assistentes.csv",
    "disciplina": "02_jogadores/jogadores_disciplina.csv",
    "gols_faixa": "03_gols/gols_marcados_por_faixa.csv",
    "gols_tempo": "03_gols/gols_marcados_por_tempo.csv",
    "gols_sofridos_faixa": "03_gols/gols_sofridos_por_faixa.csv",
    "formacoes": "04_taticas/formacoes_por_time.csv",
    "subs_padrao": "04_taticas/substituicoes_padrao_por_time.csv",
    "subs_jogadores": "04_taticas/substituicoes_jogadores.csv",
    "h2h_resumo": "05_confrontos/confrontos_resumo.csv",
    "h2h_detalhe": "05_confrontos/confrontos_diretos_h2h.csv",
    "contexto": "08_contexto/contexto_partida.csv",
    "desfalques": "08_contexto/desfalques.csv",
}


def read_table(rel_path):
    full = os.path.join(config.FINAL_OUTPUT_DIR, rel_path)
    if not os.path.exists(full):
        return []
    with open(full, encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_all():
    return {name: read_table(rel) for name, rel in TABELAS.items()}


def _normalize(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def _matches_team(row, team):
    return _normalize(team) in _normalize(row.get("time"))


def filter_team(rows, team):
    return [row for row in rows if _matches_team(row, team)]


def _format(rows, columns, limit=None):
    if not rows:
        return "(sem dados)"
    selected = rows[:limit] if limit else rows
    header = " | ".join(columns)
    lines = [header, " | ".join("---" for _ in columns)]
    for row in selected:
        lines.append(" | ".join(str(row.get(col, "")) for col in columns))
    return "\n".join(lines)


def _team_display(tables, team):
    for row in tables["resumo"]:
        if _matches_team(row, team):
            return row.get("time")
    return team


def pregame_context_text(tables=None, team=None, opponent=None):
    tables = tables or load_all()
    team = team or config.TIME_ANALISE
    time_ref = _team_display(tables, team)
    opponent = opponent or ("Goias" if "sport" in team.lower() else "Sport")
    opp_ref = _team_display(tables, opponent)

    contexto = tables["contexto"][0] if tables["contexto"] else {}
    blocks = []

    blocks.append(
        "[CONTEXTO DA PARTIDA]\n"
        + "\n".join(f"- {key}: {value}" for key, value in contexto.items())
    )

    blocks.append(
        "[CLASSIFICACAO E RESUMO DA TEMPORADA]\n"
        + _format(
            tables["resumo"],
            ["time", "jogos", "vitorias", "empates", "derrotas", "pontos", "gols_pro", "gols_contra", "saldo", "posse_media", "finalizacoes_media"],
        )
    )

    blocks.append(
        "[FORMA RECENTE - ULTIMOS 5 JOGOS]\n"
        + _format(tables["forma"], ["time", "sequencia", "pontos", "gols_pro", "gols_contra", "saldo"])
    )

    blocks.append(
        "[DESEMPENHO MANDANTE/VISITANTE]\n"
        + _format(tables["mando"], ["time", "mando", "jogos", "vitorias", "empates", "derrotas", "gols_pro", "gols_contra"])
    )

    for label, key in (("FORMACOES", "formacoes"),):
        blocks.append(
            f"[{label} - {time_ref}]\n"
            + _format(filter_team(tables[key], team), ["formacao", "jogos", "uso_pct", "vitorias", "empates", "derrotas"])
        )
        blocks.append(
            f"[{label} - {opp_ref}]\n"
            + _format(filter_team(tables[key], opponent), ["formacao", "jogos", "uso_pct", "vitorias", "empates", "derrotas"])
        )

    blocks.append(
        f"[ARTILHEIROS - {time_ref}]\n"
        + _format(filter_team(tables["artilheiros"], team), ["jogador", "gols", "assistencias", "jogos_titular"], limit=8)
    )
    blocks.append(
        f"[ARTILHEIROS - {opp_ref}]\n"
        + _format(filter_team(tables["artilheiros"], opponent), ["jogador", "gols", "assistencias", "jogos_titular"], limit=8)
    )
    blocks.append(
        f"[ASSISTENTES - {time_ref}]\n"
        + _format(filter_team(tables["assistentes"], team), ["jogador", "assistencias", "gols"], limit=6)
    )
    blocks.append(
        f"[DISCIPLINA (cartoes) - {time_ref}]\n"
        + _format(filter_team(tables["disciplina"], team), ["jogador", "cartoes_amarelos", "cartoes_vermelhos"], limit=8)
    )

    blocks.append(
        "[PADRAO DE GOLS MARCADOS POR FAIXA DE MINUTO]\n"
        + _format(tables["gols_faixa"], ["time", "faixa_minuto", "gols", "pct"])
    )
    blocks.append(
        "[PADRAO DE GOLS SOFRIDOS POR FAIXA DE MINUTO]\n"
        + _format(tables["gols_sofridos_faixa"], ["time", "faixa_minuto", "gols", "pct"])
    )
    blocks.append(
        "[GOLS POR TEMPO (1T/2T)]\n"
        + _format(tables["gols_tempo"], ["time", "tempo", "gols", "pct"])
    )

    blocks.append(
        "[PADRAO DE SUBSTITUICOES POR TIME]\n"
        + _format(tables["subs_padrao"], ["time", "media_substituicoes_por_jogo", "minuto_medio_1a_sub", "minuto_medio_2a_sub", "minuto_medio_3a_sub"])
    )
    blocks.append(
        f"[RESERVAS MAIS ACIONADOS - {time_ref}]\n"
        + _format(filter_team(tables["subs_jogadores"], team), ["jogador", "vezes_entrou", "minuto_medio_entrada"], limit=8)
    )

    blocks.append(
        "[CONFRONTOS DIRETOS - RESUMO]\n"
        + _format(tables["h2h_resumo"], ["fonte", "total_jogos", "vitorias_goias", "vitorias_sport", "empates"])
    )
    blocks.append(
        "[CONFRONTOS DIRETOS - ULTIMOS JOGOS]\n"
        + _format(tables["h2h_detalhe"], ["data_jogo", "time_casa", "time_fora", "placar"], limit=6)
    )

    blocks.append(
        "[DESFALQUES E RETORNOS]\n"
        + _format(tables["desfalques"], ["time", "jogador", "motivo", "status"])
    )

    live_state = load_live_state()
    if live_state and live_state.get("escalacao"):
        blocks.append("[ESCALACAO CONFIRMADA]")
        for team_name, players in live_state.get("escalacao", {}).items():
            blocks.append(f"Time: {team_name}")
            blocks.append(f"Titulares: {', '.join(players.get('starters', []))}")
            blocks.append(f"Reservas: {', '.join(players.get('bench', []))}")

    return "\n\n".join(blocks)


def load_live_state():
    if not os.path.exists(config.STATE_PATH):
        return {}
    with open(config.STATE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def live_context_text(state):
    if not state:
        return "(sem estado ao vivo disponivel)"
    placar = state.get("placar", {})
    casa = placar.get("casa", {})
    fora = placar.get("fora", {})
    eventos = state.get("eventos", {})

    def resumo_eventos(kind):
        items = eventos.get(kind, [])
        if not items:
            return "nenhum"
        return "; ".join(
            f"{item.get('minute_display') or item.get('minute')} {item.get('text', '')}".strip()
            for item in items
        )

    return (
        "[ESTADO ATUAL DA PARTIDA]\n"
        f"- Status: {state.get('status')} ({state.get('status_detail')})\n"
        f"- Relogio: {state.get('clock')} | Periodo: {state.get('period')}\n"
        f"- Placar: {casa.get('time')} {casa.get('gols')} x {fora.get('gols')} {fora.get('time')}\n"
        f"- Formacoes: casa {state.get('formacoes', {}).get('casa')} | fora {state.get('formacoes', {}).get('fora')}\n"
        f"- Gols: {resumo_eventos('gols')}\n"
        f"- Cartoes: {resumo_eventos('cartoes')}\n"
        f"- Substituicoes: {resumo_eventos('substituicoes')}"
    )
