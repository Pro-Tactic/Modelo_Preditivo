import builtins
import importlib
import sys
import os
import io
import json
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".")

# Ensure the project directory is in the sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load the player ID database
PLAYER_IDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_ids.json")
try:
    with open(PLAYER_IDS_PATH, "r", encoding="utf-8") as f:
        player_ids = json.load(f)
except Exception as e:
    print(f"Error loading player_ids.json: {e}")
    player_ids = {}

# Mock input generator for prev.py prompts
class MockInput:
    def __init__(self, injured_players):
        self.injured_players = injured_players
        self.call_count = 0
        
    def __call__(self, prompt=""):
        self.call_count += 1
        if self.call_count == 1:
            # First prompt: "Existe algum jogador machucado/suspenso? (s/n): "
            return "s" if self.injured_players else "n"
        elif self.call_count == 2:
            # Second prompt: "Jogadores fora: "
            return ",".join(self.injured_players)
        return ""

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/style.css")
def css():
    return send_from_directory(".", "style.css")

@app.route("/script.js")
def js():
    return send_from_directory(".", "script.js")

@app.route("/logo.png")
def logo():
    return send_from_directory(".", "logo.png")

@app.route("/logo_preta.svg")
def logo_preta():
    return send_from_directory(".", "logo_preta.svg")

@app.route("/api/players", methods=["GET"])
def get_players():
    # Load raw lists from our players file
    players_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_ids.json")
    try:
        with open(players_json_path, "r", encoding="utf-8") as f:
            ids_db = json.load(f)
    except:
        ids_db = {}
        
    # We will classify them by looking at the CSV or predefined squads.
    # In prev.py, there are two lists of players:
    # We can extract them from the csv or from the JSON we saved in the scratch directory.
    # To keep it simple, we can load them from our local players.json
    local_players_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "players.json")
    try:
        with open(local_players_path, "r", encoding="utf-8") as f:
            squads = json.load(f)
    except:
        # Fallback to lists
        squads = {
            "Arsenal": [k for k in ids_db.keys() if k in ["Bukayo Saka", "Martin Ødegaard", "Declan Rice", "William Saliba", "Gabriel Magalhães"]],
            "PSG": [k for k in ids_db.keys() if k not in ["Bukayo Saka", "Martin Ødegaard", "Declan Rice", "William Saliba", "Gabriel Magalhães"]]
        }
    
    # Map them to list of dicts with name, id, and image
    result = {
        "Arsenal": [{"name": p, "id": ids_db.get(p), "photo_url": f"https://api.sofascore.app/api/v1/player/{ids_db.get(p)}/image" if ids_db.get(p) else None} for p in squads.get("Arsenal", [])],
        "PSG": [{"name": p, "id": ids_db.get(p), "photo_url": f"https://api.sofascore.app/api/v1/player/{ids_db.get(p)}/image" if ids_db.get(p) else None} for p in squads.get("PSG", [])]
    }
    return jsonify(result)

@app.route("/api/simulate", methods=["POST"])
def simulate():
    data = request.json or {}
    desfalques = data.get("desfalques", [])
    simulations_count = data.get("simulacoes", 100000)
    
    # Clamp simulation size for safety (keep it between 5,000 and 100,000)
    simulations_count = max(5000, min(simulations_count, 100000))
    
    # Configure dynamic mock input for the reload
    builtins.input = MockInput(desfalques)
    
    # We must suppress stdout to prevent console flooding
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        if 'prev' in sys.modules:
            # Update the configuration in prev before reload
            sys.modules['prev'].SIMULACOES = simulations_count
            importlib.reload(sys.modules['prev'])
            copa.prev = sys.modules['prev']
        else:
            import copa.prev as prev
            prev.SIMULACOES = simulations_count
            # Force reload to apply mock input the first time too
            importlib.reload(prev)
    except Exception as e:
        sys.stdout = old_stdout
        return jsonify({"error": str(e)}), 500
        
    sys.stdout = old_stdout
    
    # Construct player info helper
    def get_player_info(name):
        pid = player_ids.get(name)
        return {
            "name": name,
            "id": pid,
            "photo_url": f"https://api.sofascore.app/api/v1/player/{pid}/image" if pid else None
        }

    # Format the simulation outputs
    try:
        sum_gols = sum(prev.gols_jogadores.values())
        sum_assists = sum(prev.assist_jogadores.values())
        
        res = {
            "time_a": prev.TIME_A,
            "time_b": prev.TIME_B,
            "formacao_a": prev.formacao_arsenal,
            "formacao_b": prev.formacao_psg,
            "forcas": {
                "a": {"atk": prev.atk_a, "def": prev.def_a},
                "b": {"atk": prev.atk_b, "def": prev.def_b}
            },
            "medias_gols": {
                "a": prev.media_arsenal,
                "b": prev.media_psg
            },
            "probabilidades": {
                "a": prev.prob_v_a,
                "empate": prev.prob_emp,
                "b": prev.prob_v_b
            },
            "lideranca": {
                "psg": prev.prob_psg_liderou,
                "arsenal": prev.prob_arsenal_liderou,
                "nenhum": prev.prob_nenhum_liderou
            },
            "primeiro_gol": {
                "psg": prev.prob_psg_primeiro,
                "arsenal": prev.prob_arsenal_primeiro,
                "sem_gol": prev.prob_sem_gol
            },
            "placar_mais_comum": prev.placar_mais_comum,
            "artilheiro_principal": prev.artilheiro,
            "assistente_principal": prev.assistencia,
            "favorito": prev.favorito,
            "favorito_chance": prev.chance,
            "mata_mata": {
                "prorrogacao": prev.resultado_prorrogacao,
                "penaltis": prev.penaltis
            },
            "placares_provaveis": [
                {"placar": p, "prob": (qtd / simulations_count) * 100}
                for p, qtd in prev.resultados.most_common(10)
            ],
            "artilheiros": [
                {"jogador": j, "prob": (qtd / sum_gols) * 100 if sum_gols > 0 else 0, "info": get_player_info(j)}
                for j, qtd in prev.gols_jogadores.most_common(10)
            ],
            "assistentes": [
                {"jogador": j, "prob": (qtd / sum_assists) * 100 if sum_assists > 0 else 0, "info": get_player_info(j)}
                for j, qtd in prev.assist_jogadores.most_common(10)
            ],
            "escalacao_a": [
                {"slot": slot, "name": name, "info": get_player_info(name)}
                for slot, name in prev.escalacao_arsenal
            ],
            "escalacao_b": [
                {"slot": slot, "name": name, "info": get_player_info(name)}
                for slot, name in prev.escalacao_psg
            ],
            "desfalques_considerados": [get_player_info(d) for d in desfalques]
        }
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Error formatting simulation results: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
