"""
Servidor Flask para a interface Brasil x Egito.
Apenas lê os CSVs já gerados pelo script prev_brasil_egito.py
e os disponibiliza como JSON para o frontend.

Para rodar: python copa/app_brasil_egito.py
"""

import os
import re
import sys
import json
import pandas as pd
from flask import Flask, jsonify, send_from_directory

base_dir  = os.path.dirname(os.path.abspath(__file__))          # .../copa
root_dir  = os.path.dirname(base_dir)                            # .../Modelo_Preditivo
out_dir   = os.path.join(base_dir, "outputs")
iface_dir = os.path.join(base_dir, "interface")

app = Flask(__name__, static_folder=iface_dir, static_url_path="")

# ─── helpers ────────────────────────────────────────────────────────────────

def player_info(name: str, team: str, df_conv: pd.DataFrame) -> dict:
    row = df_conv[(df_conv["selecao"] == team) & (df_conv["jogador"] == name)]
    if not row.empty:
        pid = row.iloc[0]["player_id"]
        pid = int(pid) if not pd.isna(pid) else None
        return {
            "name": name,
            "id": pid,
            "photo_url": f"https://api.sofascore.app/api/v1/player/{pid}/image" if pid else None
        }
    return {"name": name, "id": None, "photo_url": None}


# Escalações fixas definidas em prev_brasil_egito.py
ESCALACAO_BRASIL = [
    ("GK",  "Alisson"),
    ("RB",  "Wesley"),
    ("RCB", "Marquinhos"),
    ("LCB", "Léo Pereira"),
    ("LB",  "Douglas Santos"),
    ("RM",  "Lucas Paquetá"),
    ("CM1", "Casemiro"),
    ("CM2", "Bruno Guimarães"),
    ("LM",  "Raphinha"),
    ("ST1", "Igor Thiago"),
    ("ST2", "Vinícius Júnior"),
]

ESCALACAO_EGITO = [
    ("GK",  "Mohamed El Shenawy"),
    ("RWB", "Mohamed Hany"),
    ("RCB", "Hamdi Fathy"),
    ("CB",  "Yasser Ibrahim"),
    ("LCB", "Rami Rabia"),
    ("LWB", "Ahmed Fatouh"),
    ("CM1", "Mohanad Lasheen"),
    ("CM2", "Marwan Attia"),
    ("RW",  "Mohamed Salah"),
    ("ST",  "Omar Marmoush"),
    ("LW",  "Mahmoud Trézéguet"),
]

# ─── rotas ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(iface_dir, "brasil_egito.html")

@app.route("/api/results")
def results():
    """
    Lê os CSVs já gerados pela última execução de prev_brasil_egito.py
    e devolve um JSON completo para o frontend.
    """
    # 1) CSVs de saída
    try:
        df_placares    = pd.read_csv(os.path.join(out_dir, "brasil_egito_placares.csv"))
        df_goleadores  = pd.read_csv(os.path.join(out_dir, "brasil_egito_goleadores.csv"))
        df_assistentes = pd.read_csv(os.path.join(out_dir, "brasil_egito_assistentes.csv"))
    except FileNotFoundError as e:
        return jsonify({
            "erro": (
                "Arquivos de saída não encontrados. "
                "Execute primeiro: python copa/prev_brasil_egito.py"
            ),
            "detalhe": str(e)
        }), 404

    # 2) Convocação para fotos
    df_conv = pd.read_csv(os.path.join(base_dir, "convocacao.csv"))

    # 3) Placares mais prováveis
    placares = [
        {"placar": r["Placar"], "prob": float(r["Probabilidade (%)"])}
        for _, r in df_placares.head(10).iterrows()
    ]

    # 4) Goleadores
    def parse_jogador(jogador_str, prob_col):
        m = re.match(r"(.*?)\s*\((.*?)\)", jogador_str)
        nome  = m.group(1).strip() if m else jogador_str
        equipe = m.group(2).strip() if m else "Brazil"
        return {"jogador": nome, "equipe": equipe, "prob": float(prob_col),
                "info": player_info(nome, equipe, df_conv)}

    goleadores = [
        parse_jogador(r["Jogador"], r["Probabilidade de Marcar (%)"])
        for _, r in df_goleadores.head(10).iterrows()
    ]

    assistentes = [
        parse_jogador(r["Jogador"], r["Probabilidade de Dar Assistência (%)"])
        for _, r in df_assistentes.head(10).iterrows()
    ]

    # 5) Escalações com fotos
    esc_brasil = [
        {"slot": s, "name": n, "info": player_info(n, "Brazil", df_conv)}
        for s, n in ESCALACAO_BRASIL
    ]
    esc_egito = [
        {"slot": s, "name": n, "info": player_info(n, "Egypt", df_conv)}
        for s, n in ESCALACAO_EGITO
    ]

    # 6) Estatísticas da última simulação
    #    (geradas pelo script e salvas nos CSVs; valores extraídos do stdout
    #     da última execução — estáveis até a próxima rodada manual do script)
    stats = {
        "simulacoes": 100_000,
        "probabilidades": {
            "brasil": 58.83,
            "empate": 23.50,
            "egito":  17.68
        },
        "primeiro_gol": {
            "brasil":  62.73,
            "egito":   29.33,
            "sem_gol":  7.94
        },
        "lideranca": {
            "brasil": 70.41,
            "egito":  33.11
        },
        "halves": {
            "apenas_1t": 20.02,
            "apenas_2t": 19.86,
            "ambos":     52.18
        }
    }

    return jsonify({
        "formacao_brasil": "4-4-2",
        "formacao_egito":  "5-2-3",
        "escalacao_brasil": esc_brasil,
        "escalacao_egito":  esc_egito,
        "placares":         placares,
        "goleadores":       goleadores,
        "assistentes":      assistentes,
        "stats":            stats
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
