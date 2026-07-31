import json
import os
import time

import pandas as pd
import streamlit as st

import config
import contexto_dados
import llm_client
import insight_engine

TABLET_CSS = """
<style>
.block-container { max-width: 820px; padding-top: 1.2rem; padding-bottom: 3rem; }
html, body, [class*="css"] { font-size: 18px; }
h1 { font-size: 1.8rem !important; }
h2, h3 { font-size: 1.3rem !important; }
div[data-testid="stMetricValue"] { font-size: 2.6rem; }
div.stButton > button { height: 3.2rem; font-size: 1.15rem; border-radius: 0.8rem; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 0.9rem; }
</style>
"""


def _read_jsonl(path):
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def _safe_int(valor):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return 0


def _minuto_int(valor):
    if valor is None:
        return 0
    texto = str(valor).replace("'", "")
    if "+" in texto:
        base, extra = texto.split("+", 1)
        return _safe_int(base) + _safe_int(extra)
    return _safe_int(texto)


def painel_estado(state):
    st.subheader("Placar")
    if not state:
        st.info("Aguardando dados do monitor ao vivo.")
        return
    placar = state.get("placar", {})
    casa = placar.get("casa", {})
    fora = placar.get("fora", {})
    col1, col2 = st.columns(2)
    casa_time = casa.get("time") or "Casa"
    fora_time = fora.get("time") or "Fora"
    casa_gols = str(casa.get("gols") or "0")
    fora_gols = str(fora.get("gols") or "0")
    col1.metric(casa_time, casa_gols)
    col2.metric(fora_time, fora_gols)
    st.caption(f"Status: {state.get('status')} · Relogio: {state.get('clock')} · Periodo: {state.get('period')}")
    formacoes = state.get("formacoes", {})
    st.write(
        f"**Formacoes:** {casa.get('time','casa')} `{formacoes.get('casa') or 'n/d'}` "
        f"x `{formacoes.get('fora') or 'n/d'}` {fora.get('time','fora')}"
    )
    escalacao = state.get("escalacao", {})
    if escalacao:
        with st.expander("Escalações Confirmadas", expanded=False):
            ec1, ec2 = st.columns(2)
            if casa_time in escalacao:
                ec1.markdown(f"**{casa_time}**\n" + "\n".join(f"- {p}" for p in escalacao[casa_time].get("starters", [])))
            if fora_time in escalacao:
                ec2.markdown(f"**{fora_time}**\n" + "\n".join(f"- {p}" for p in escalacao[fora_time].get("starters", [])))
    eventos = state.get("eventos", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Gols", len(eventos.get("gols", [])))
    c2.metric("Cartoes", len(eventos.get("cartoes", [])))
    c3.metric("Subs", len(eventos.get("substituicoes", [])))


def painel_insights(insights):
    st.subheader("Insights da IA")
    st.caption(f"Motor: {llm_client.status()}")
    if not insights:
        st.info("Nenhum insight gerado ainda. Toque em 'Gerar analise agora' ou aguarde um evento.")
        return
    for record in reversed(insights[-30:]):
        with st.container(border=True):
            st.markdown(
                f"**{record.get('minute','?')} · {record.get('trigger','')}** "
                f"`{record.get('generated_by','')}`"
            )
            st.write(record.get("insight", ""))
            if record.get("evento"):
                st.caption(record["evento"])


def painel_momentum(state):
    eventos = (state or {}).get("eventos", {})
    gols = eventos.get("gols", [])
    if gols:
        linhas = []
        casa = 0
        fora = 0
        for gol in sorted(gols, key=lambda g: _minuto_int(g.get("minute"))):
            if gol.get("side") == "casa":
                casa += 1
            else:
                fora += 1
            linhas.append({"minuto": _minuto_int(gol.get("minute")), "saldo (casa - fora)": casa - fora})
        st.line_chart(pd.DataFrame(linhas).set_index("minuto"))
    else:
        st.caption("Sem gols para plotar momentum.")

    todos = eventos.get("gols", []) + eventos.get("cartoes", []) + eventos.get("substituicoes", [])
    if todos:
        tabela = [
            {"minuto": item.get("minute_display") or item.get("minute"), "descricao": item.get("text", "")}
            for item in sorted(todos, key=lambda i: _minuto_int(i.get("minute")))
        ]
        st.dataframe(pd.DataFrame(tabela), use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Analise Tatica ao Vivo", layout="centered", initial_sidebar_state="collapsed")
    st.markdown(TABLET_CSS, unsafe_allow_html=True)

    tables = contexto_dados.load_all()
    contexto = tables["contexto"][0] if tables["contexto"] else {}
    st.title(contexto.get("partida", "Analise Tatica ao Vivo"))
    st.caption(f"{contexto.get('competicao','')} · {contexto.get('data_hora','')} · {contexto.get('local','')}")

    with st.sidebar:
        st.header("Configuracoes")
        auto = st.toggle("Auto-atualizar", value=False)
        intervalo = st.slider("Intervalo (s)", 15, 120, config.POLL_INTERVAL_SECONDS, step=15)

    state = contexto_dados.load_live_state()
    insights = _read_jsonl(config.INSIGHTS_LOG_PATH)

    with st.expander("📝 Inserir Estatísticas do Sofascore/Footstats (Opcional)", expanded=False):
        nota_manual = st.text_area("Adicione dados extras para a IA analisar no intervalo", placeholder="Cole aqui: Posse de bola, xG, chutes no alvo, passes...")

    botoes = st.columns(2)
    with botoes[0]:
        if st.button("Atualizar", use_container_width=True):
            st.rerun()
    with botoes[1]:
        if st.button("Gerar analise agora", type="primary", use_container_width=True):
            registro = insight_engine.generate_manual(state or {"event_id": contexto.get("partida")}, nota=nota_manual)
            st.success(f"Insight gerado ({registro['generated_by']}).")
            insights = _read_jsonl(config.INSIGHTS_LOG_PATH)

    painel_estado(state)
    st.divider()
    painel_insights(insights)
    st.divider()
    with st.expander("Momentum e historico de eventos", expanded=False):
        painel_momentum(state)

    if auto:
        st.caption(f"Auto-atualizando a cada {intervalo}s...")
        time.sleep(intervalo)
        st.rerun()


if __name__ == "__main__":
    main()
