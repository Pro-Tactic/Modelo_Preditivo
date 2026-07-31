import json
import os
from datetime import datetime, timezone

import config
import contexto_dados
import llm_client

def get_system_prompt(is_manual=False):
    base = (
        f"Você é o analista tático EXCLUSIVO do {config.TIME_ANALISE}, trabalhando para o técnico {config.TECNICO_ANALISE}. "
        f"REGRA ZERO: Seu objetivo é ajudar apenas o {config.TIME_ANALISE}. NUNCA dê dicas, sugestões ou planos de ação para o time adversário. O adversário é o inimigo. "
        "Use RIGOROSAMENTE a escalação atual fornecida no contexto. "
        "ATENÇÃO: O bloco de 'Reservas Mais Acionados' é apenas um histórico. NUNCA sugira a entrada de um jogador que não esteja EXPLICITAMENTE listado no 'Banco' da escalação do jogo de hoje (ele pode estar suspenso)."
    )
    lang = "REGRA ABSOLUTA 2: RESPONDA EXCLUSIVAMENTE EM PORTUGUÊS DO BRASIL, NUNCA EM INGLÊS. "
    
    if is_manual:
        size = (
            "REGRA ABSOLUTA 1: Esta é uma análise sob demanda para o vestiário. "
            "Seja TELEGRÁFICO. Escreva EXATAMENTE 3 bullet points curtos e diretos (estilo SMS). "
            "PROIBIDO escrever introduções, conclusões ou parágrafos longos. Apenas os 3 tópicos de ação."
        )
    else:
        size = (
            f"REGRA ABSOLUTA 1: Gere um insight tático TELEGRÁFICO de NO MÁXIMO 3 FRASES CURTAS para o técnico {config.TECNICO_ANALISE}. "
            "PROIBIDO usar listas, bullet points, negrito, conclusões ou mais de um parágrafo. Seja seco e direto. "
            "O texto DEVE ter o tamanho de um SMS."
        )
        
    return base + size + lang + "PROIBIDO usar marcação de markdown complexa como tabelas."

_CACHE = {}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _tables():
    if "tables" not in _CACHE:
        _CACHE["tables"] = contexto_dados.load_all()
    return _CACHE["tables"]


def _pregame_text():
    if "pregame" not in _CACHE:
        _CACHE["pregame"] = contexto_dados.pregame_context_text(_tables())
    return _CACHE["pregame"]


def _is_our_team(team_id):
    return str(team_id) == str(config.TEAM_ID_SPORT)


def classify_trigger(event, state):
    tipo = event.get("tipo")
    minute = event.get("minute") or 0
    nossa = _is_our_team(event.get("team_id"))
    if tipo == "gols":
        return ("gol_marcado", "Reforce o padrao que gerou o gol e como sustentar a vantagem.") if nossa else (
            "gol_sofrido",
            "Analise a vulnerabilidade explorada e sugira ajuste defensivo imediato.",
        )
    if tipo == "cartoes":
        if nossa:
            return "cartao_nosso", "Avalie risco de expulsao e se o jogador deve ser preservado/substituido."
        return "cartao_adversario", "Avalie como explorar o jogador adversario pressionado por cartao."
    if tipo == "substituicoes":
        return ("sub_nossa", "Avalie se a substituicao ajusta corretamente o panorama do jogo.") if nossa else (
            "sub_adversario",
            "Alerta: a substituicao do adversario pode sinalizar mudanca de esquema. Antecipe o ajuste.",
        )
    if tipo == "intervalo":
        return "intervalo", "Compile o 1o tempo e proponha 3 ajustes para o 2o tempo."
    if tipo == "momentum":
        return "momentum", "Analise a tendencia do jogo e indique se e hora de acionar substituicoes."
    if tipo == "acrescimos":
        return "acrescimos", "Oriente os minutos finais conforme o placar atual."
    if tipo == "escalacao":
        return "escalacao", "Compare a formacao confirmada com as mais usadas na temporada."
    return "manual", "Gere uma leitura tatica objetiva do momento atual."


def build_prompt(event, state, instrucao):
    live = contexto_dados.live_context_text(state)
    evento_txt = event.get("text") or event.get("descricao") or json.dumps(event, ensure_ascii=False)
    return (
        f"===== CONTEXTO DA TEMPORADA =====\n{_pregame_text()}\n\n"
        f"===== {live}\n\n"
        f"===== EVENTO GATILHO =====\n"
        f"Tipo: {event.get('tipo')} | Minuto: {event.get('minute_display') or event.get('minute')}\n"
        f"Descricao: {evento_txt}\n\n"
        f"===== INSTRUCAO =====\n{instrucao}"
    )


def _team_row(rows, team):
    found = contexto_dados.filter_team(rows, team)
    return found[0] if found else {}


def offline_insight(trigger, event, state):
    tables = _tables()
    time = config.TIME_ANALISE
    minute = event.get("minute_display") or event.get("minute")
    if trigger == "gol_sofrido":
        sofridos = [r for r in tables["gols_sofridos_faixa"] if contexto_dados._matches_team(r, time)]
        pior = max(sofridos, key=lambda r: int(r.get("gols") or 0)) if sofridos else {}
        return (
            f"Gol sofrido aos {minute}. Historicamente o {time} sofre mais na faixa "
            f"{pior.get('faixa_minuto', 'n/d')} ({pior.get('gols', '?')} gols na temporada). "
            "Reorganizar a linha defensiva e proteger a transicao imediata; evitar tomar o segundo em sequencia."
        )
    if trigger == "gol_marcado":
        return (
            f"Gol marcado aos {minute}. Manter o bloco e o plano que gerou a chance. "
            "Controlar o ritmo e usar a janela de substituicoes para segurar a vantagem."
        )
    if trigger == "sub_adversario":
        return (
            f"Substituicao do adversario aos {minute}: pode indicar mudanca de esquema. "
            "Confirmar a nova formacao e ajustar marcacao nos setores expostos."
        )
    if trigger == "cartao_nosso":
        return (
            f"Cartao do {time} aos {minute}. Risco de segundo amarelo em jogo faltoso. "
            "Avaliar preservar o atleta apos os 70' conforme o padrao da comissao."
        )
    subs = _team_row(tables["subs_padrao"], time)
    return (
        f"Leitura aos {minute}: acompanhar o momentum. Janela tipica de 1a substituicao do {time} "
        f"~{subs.get('minuto_medio_1a_sub', 'n/d')}'. Preparar ajustes conforme o placar."
    )


def log_insight(record):
    os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
    with open(config.INSIGHTS_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def generate_insight(state, event, persist=True, is_manual=False):
    trigger, instrucao = classify_trigger(event, state)
    if llm_client.is_available():
        try:
            texto = llm_client.generate(build_prompt(event, state, instrucao), system=get_system_prompt(is_manual), temperature=0.7)
            origem = "IA/Nvidia"
        except Exception as error:
            texto = offline_insight(trigger, event, state) + f" (fallback: {error})"
            origem = "offline_fallback"
    else:
        texto = offline_insight(trigger, event, state)
        origem = "offline"

    record = {
        "logged_at": _now_iso(),
        "event_id": state.get("event_id"),
        "trigger": trigger,
        "tipo": event.get("tipo"),
        "minute": event.get("minute_display") or event.get("minute"),
        "team_id": event.get("team_id"),
        "generated_by": origem,
        "insight": texto,
        "evento": event.get("text") or event.get("descricao"),
    }
    if persist:
        log_insight(record)
    return record


def generate_for_events(state, events, persist=True):
    return [generate_insight(state, event, persist=persist) for event in events]


def generate_manual(state, nota=None, persist=True):
    texto_evento = "Analise manual solicitada."
    if nota:
        texto_evento += f"\nEstatísticas e Contexto Adicional do Usuário:\n{nota}"
    event = {"tipo": "manual", "minute": state.get("clock"), "text": texto_evento}
    return generate_insight(state, event, persist=persist, is_manual=True)


if __name__ == "__main__":
    live = contexto_dados.load_live_state()
    exemplo = {"tipo": "gols", "minute": "52'", "team_id": config.TEAM_ID_GOIAS, "text": "Gol do Goias."}
    resultado = generate_insight(live or {"event_id": "teste"}, exemplo, persist=False)
    print(f"[{resultado['generated_by']}] trigger={resultado['trigger']}")
    print(resultado["insight"])
