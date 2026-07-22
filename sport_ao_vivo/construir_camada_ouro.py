import csv
import json
import os
from collections import defaultdict

import config
import contexto
import espn_api
import parsers

BUCKET_ORDER = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "90+"]
HALF_ORDER = ["1T", "2T", "OT"]


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _to_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _to_float(value, default=None):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _round(value, digits=2):
    return round(value, digits) if value is not None else None


def write_table(subfolder, filename, fieldnames, rows):
    directory = os.path.join(config.FINAL_OUTPUT_DIR, subfolder)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    return path, len(rows)


def team_side(record, team_id):
    if record["casa"]["team_id"] == team_id:
        return record["casa"], record["fora"], "casa"
    return record["fora"], record["casa"], "fora"


def build_indexes(structured):
    all_games = {}
    team_games = defaultdict(list)
    id_to_name = {}
    roster_by_team = defaultdict(set)
    for team_name, records in structured.items():
        team_id = config.TEAMS[team_name]
        for record in records:
            all_games[record["event_id"]] = record
            team_games[team_id].append(record)
            for side in ("casa", "fora"):
                id_to_name[record[side]["team_id"]] = record[side]["nome"]
            ref, _, _ = team_side(record, team_id)
            for player in ref["titulares"] + ref["reservas"]:
                roster_by_team[team_id].add(player)
    return all_games, team_games, id_to_name, roster_by_team


def _tokens(name):
    return set(name.lower().replace("-", " ").split())


def build_canonical_maps(team_games):
    canonical_maps = {}
    for team_id, records in team_games.items():
        names = set()
        for record in records:
            ref, _, mando = team_side(record, team_id)
            names.update(ref["titulares"])
            names.update(ref["reservas"])
            for goal in record["gols"]:
                if goal.get("side") == mando:
                    names.add(goal["scorer"])
                    if goal.get("assist"):
                        names.add(goal["assist"])
            for card in record["cartoes"]:
                if card.get("side") == mando and card.get("player"):
                    names.add(card["player"])
            for sub in record["substituicoes"]:
                if sub.get("side") == mando:
                    names.add(sub.get("player_in"))
                    names.add(sub.get("player_out"))
        names = {n for n in names if n}
        token_map = {n: _tokens(n) for n in names}
        canonical = {}
        for name in names:
            supersets = [
                other
                for other in names
                if other != name and token_map[name] and token_map[name].issubset(token_map[other])
            ]
            if supersets:
                max_len = max(len(token_map[other]) for other in supersets)
                top = [other for other in supersets if len(token_map[other]) == max_len]
                canonical[name] = top[0] if len(top) == 1 else name
            else:
                canonical[name] = name
        canonical_maps[team_id] = canonical
    return canonical_maps


def resolve_name(name, canonical):
    if not name:
        return name
    return canonical.get(name, name)


def build_times_resumo(team_games):
    rows = []
    for team_id, records in team_games.items():
        agg = {
            "jogos": 0,
            "V": 0,
            "E": 0,
            "D": 0,
            "gp": 0,
            "gc": 0,
            "gp_1t": 0,
            "gp_2t": 0,
            "gc_1t": 0,
            "gc_2t": 0,
            "amarelos": 0,
            "vermelhos": 0,
            "posse": [],
            "finalizacoes": [],
            "finalizacoes_alvo": [],
        }
        team_name = None
        for record in records:
            ref, opp, mando = team_side(record, team_id)
            team_name = ref["nome"]
            gp = _to_int(ref["gols"])
            gc = _to_int(opp["gols"])
            agg["jogos"] += 1
            agg["gp"] += gp
            agg["gc"] += gc
            if gp > gc:
                agg["V"] += 1
            elif gp == gc:
                agg["E"] += 1
            else:
                agg["D"] += 1
            for goal in record["gols"]:
                if goal.get("side") == mando:
                    agg["gp_1t" if goal["half"] == "1T" else "gp_2t"] += 1
                else:
                    agg["gc_1t" if goal["half"] == "1T" else "gc_2t"] += 1
            for card in record["cartoes"]:
                if card.get("side") == mando:
                    agg["amarelos" if card["color"] == "amarelo" else "vermelhos"] += 1
            posse = _to_float(ref["estatisticas"].get("possessionPct"))
            if posse is not None:
                agg["posse"].append(posse)
            shots = _to_float(ref["estatisticas"].get("totalShots"))
            if shots is not None:
                agg["finalizacoes"].append(shots)
            on_target = _to_float(ref["estatisticas"].get("shotsOnTarget"))
            if on_target is not None:
                agg["finalizacoes_alvo"].append(on_target)
        pontos = agg["V"] * 3 + agg["E"]
        jogos = agg["jogos"] or 1
        rows.append(
            {
                "team_id": team_id,
                "time": team_name,
                "jogos": agg["jogos"],
                "vitorias": agg["V"],
                "empates": agg["E"],
                "derrotas": agg["D"],
                "pontos": pontos,
                "aproveitamento_pct": _round(100 * pontos / (jogos * 3)),
                "gols_pro": agg["gp"],
                "gols_contra": agg["gc"],
                "saldo": agg["gp"] - agg["gc"],
                "gols_pro_1t": agg["gp_1t"],
                "gols_pro_2t": agg["gp_2t"],
                "gols_contra_1t": agg["gc_1t"],
                "gols_contra_2t": agg["gc_2t"],
                "cartoes_amarelos": agg["amarelos"],
                "cartoes_vermelhos": agg["vermelhos"],
                "posse_media": _round(sum(agg["posse"]) / len(agg["posse"])) if agg["posse"] else None,
                "finalizacoes_media": _round(sum(agg["finalizacoes"]) / len(agg["finalizacoes"]))
                if agg["finalizacoes"]
                else None,
                "finalizacoes_alvo_media": _round(
                    sum(agg["finalizacoes_alvo"]) / len(agg["finalizacoes_alvo"])
                )
                if agg["finalizacoes_alvo"]
                else None,
            }
        )
    fields = [
        "team_id", "time", "jogos", "vitorias", "empates", "derrotas", "pontos",
        "aproveitamento_pct", "gols_pro", "gols_contra", "saldo", "gols_pro_1t",
        "gols_pro_2t", "gols_contra_1t", "gols_contra_2t", "cartoes_amarelos",
        "cartoes_vermelhos", "posse_media", "finalizacoes_media", "finalizacoes_alvo_media",
    ]
    return fields, rows


def build_times_mando(team_games):
    rows = []
    for team_id, records in team_games.items():
        buckets = {"casa": defaultdict(int), "fora": defaultdict(int)}
        team_name = None
        for record in records:
            ref, opp, mando = team_side(record, team_id)
            team_name = ref["nome"]
            gp = _to_int(ref["gols"])
            gc = _to_int(opp["gols"])
            b = buckets[mando]
            b["jogos"] += 1
            b["gp"] += gp
            b["gc"] += gc
            if gp > gc:
                b["V"] += 1
            elif gp == gc:
                b["E"] += 1
            else:
                b["D"] += 1
        for mando in ("casa", "fora"):
            b = buckets[mando]
            rows.append(
                {
                    "team_id": team_id,
                    "time": team_name,
                    "mando": mando,
                    "jogos": b["jogos"],
                    "vitorias": b["V"],
                    "empates": b["E"],
                    "derrotas": b["D"],
                    "pontos": b["V"] * 3 + b["E"],
                    "gols_pro": b["gp"],
                    "gols_contra": b["gc"],
                }
            )
    fields = ["team_id", "time", "mando", "jogos", "vitorias", "empates", "derrotas", "pontos", "gols_pro", "gols_contra"]
    return fields, rows


def build_forma_recente(team_games, n=5):
    rows = []
    for team_id, records in team_games.items():
        ordered = sorted(records, key=lambda r: r["data_jogo"])
        recent = ordered[-n:]
        seq = []
        pontos = gp = gc = 0
        team_name = None
        for record in recent:
            ref, opp, _ = team_side(record, team_id)
            team_name = ref["nome"]
            g_for = _to_int(ref["gols"])
            g_against = _to_int(opp["gols"])
            gp += g_for
            gc += g_against
            if g_for > g_against:
                seq.append("V")
                pontos += 3
            elif g_for == g_against:
                seq.append("E")
                pontos += 1
            else:
                seq.append("D")
        rows.append(
            {
                "team_id": team_id,
                "time": team_name,
                "jogos_considerados": len(recent),
                "sequencia": "".join(seq),
                "pontos": pontos,
                "aproveitamento_pct": _round(100 * pontos / (len(recent) * 3)) if recent else None,
                "gols_pro": gp,
                "gols_contra": gc,
                "saldo": gp - gc,
            }
        )
    fields = ["team_id", "time", "jogos_considerados", "sequencia", "pontos", "aproveitamento_pct", "gols_pro", "gols_contra", "saldo"]
    return fields, rows


def build_formacoes(team_games):
    rows = []
    for team_id, records in team_games.items():
        by_formation = defaultdict(lambda: {"jogos": 0, "V": 0, "E": 0, "D": 0})
        team_name = None
        total = 0
        for record in records:
            ref, opp, _ = team_side(record, team_id)
            team_name = ref["nome"]
            formation = ref["formacao"] or "desconhecida"
            gp = _to_int(ref["gols"])
            gc = _to_int(opp["gols"])
            entry = by_formation[formation]
            entry["jogos"] += 1
            total += 1
            if gp > gc:
                entry["V"] += 1
            elif gp == gc:
                entry["E"] += 1
            else:
                entry["D"] += 1
        for formation, entry in sorted(by_formation.items(), key=lambda kv: kv[1]["jogos"], reverse=True):
            rows.append(
                {
                    "team_id": team_id,
                    "time": team_name,
                    "formacao": formation,
                    "jogos": entry["jogos"],
                    "uso_pct": _round(100 * entry["jogos"] / total) if total else None,
                    "vitorias": entry["V"],
                    "empates": entry["E"],
                    "derrotas": entry["D"],
                    "pontos": entry["V"] * 3 + entry["E"],
                }
            )
    fields = ["team_id", "time", "formacao", "jogos", "uso_pct", "vitorias", "empates", "derrotas", "pontos"]
    return fields, rows


def build_jogadores(team_games, canonical_maps):
    rows = []
    for team_id, records in team_games.items():
        roster = canonical_maps[team_id]
        team_name = None
        stats = defaultdict(lambda: {"gols": 0, "assist": 0, "amarelos": 0, "vermelhos": 0, "titular": 0, "entrou": 0, "saiu": 0})
        for record in records:
            ref, _, mando = team_side(record, team_id)
            team_name = ref["nome"]
            for player in ref["titulares"]:
                stats[resolve_name(player, roster)]["titular"] += 1
            for goal in record["gols"]:
                if goal.get("side") == mando:
                    stats[resolve_name(goal["scorer"], roster)]["gols"] += 1
                    if goal.get("assist"):
                        stats[resolve_name(goal["assist"], roster)]["assist"] += 1
            for card in record["cartoes"]:
                if card.get("side") == mando:
                    key = "amarelos" if card["color"] == "amarelo" else "vermelhos"
                    stats[resolve_name(card.get("player"), roster)][key] += 1
            for sub in record["substituicoes"]:
                if sub.get("side") == mando:
                    if sub.get("player_in"):
                        stats[resolve_name(sub["player_in"], roster)]["entrou"] += 1
                    if sub.get("player_out"):
                        stats[resolve_name(sub["player_out"], roster)]["saiu"] += 1
        for player, entry in stats.items():
            if not player:
                continue
            rows.append(
                {
                    "time": team_name,
                    "team_id": team_id,
                    "jogador": player,
                    "jogos_titular": entry["titular"],
                    "gols": entry["gols"],
                    "assistencias": entry["assist"],
                    "participacoes_gol": entry["gols"] + entry["assist"],
                    "entrou_como_reserva": entry["entrou"],
                    "foi_substituido": entry["saiu"],
                    "cartoes_amarelos": entry["amarelos"],
                    "cartoes_vermelhos": entry["vermelhos"],
                }
            )
    rows.sort(key=lambda r: (r["time"], -r["participacoes_gol"], -r["jogos_titular"]))
    fields = ["time", "team_id", "jogador", "jogos_titular", "gols", "assistencias", "participacoes_gol", "entrou_como_reserva", "foi_substituido", "cartoes_amarelos", "cartoes_vermelhos"]
    return fields, rows


def _ranked(rows, key, extra_fields):
    ranked = [r for r in rows if r[key] > 0]
    ranked.sort(key=lambda r: (r["time"], -r[key]))
    fields = ["time", "jogador", key] + extra_fields
    return fields, ranked


def build_gols_detalhado(all_games):
    rows = []
    for record in all_games.values():
        for goal in record["gols"]:
            side = goal.get("side")
            if side == "casa":
                scoring, opponent = record["casa"], record["fora"]
            elif side == "fora":
                scoring, opponent = record["fora"], record["casa"]
            else:
                continue
            rows.append(
                {
                    "event_id": record["event_id"],
                    "data_jogo": record["data_jogo"],
                    "time_marcou": scoring["nome"],
                    "adversario": opponent["nome"],
                    "mando": side,
                    "minuto": goal["minute"],
                    "minuto_display": goal["minute_display"],
                    "tempo": goal["half"],
                    "faixa_minuto": goal["bucket"],
                    "marcador": goal["scorer"],
                    "assistente": goal.get("assist"),
                    "penalti": goal.get("penalty"),
                    "gol_contra": goal.get("own_goal"),
                }
            )
    rows.sort(key=lambda r: (r["data_jogo"], r["minuto"]))
    fields = ["event_id", "data_jogo", "time_marcou", "adversario", "mando", "minuto", "minuto_display", "tempo", "faixa_minuto", "marcador", "assistente", "penalti", "gol_contra"]
    return fields, rows


def build_gols_por_faixa(team_games, sofridos=False):
    rows = []
    for team_id, records in team_games.items():
        counts = defaultdict(int)
        team_name = None
        total = 0
        for record in records:
            ref, _, mando = team_side(record, team_id)
            team_name = ref["nome"]
            for goal in record["gols"]:
                is_for = goal.get("side") == mando
                if sofridos == (not is_for):
                    counts[goal["bucket"]] += 1
                    total += 1
        for bucket in BUCKET_ORDER:
            rows.append(
                {
                    "team_id": team_id,
                    "time": team_name,
                    "faixa_minuto": bucket,
                    "gols": counts.get(bucket, 0),
                    "pct": _round(100 * counts.get(bucket, 0) / total) if total else 0,
                }
            )
    fields = ["team_id", "time", "faixa_minuto", "gols", "pct"]
    return fields, rows


def build_gols_por_tempo(team_games, sofridos=False):
    rows = []
    for team_id, records in team_games.items():
        counts = defaultdict(int)
        team_name = None
        total = 0
        for record in records:
            ref, _, mando = team_side(record, team_id)
            team_name = ref["nome"]
            for goal in record["gols"]:
                is_for = goal.get("side") == mando
                if sofridos == (not is_for):
                    counts[goal["half"]] += 1
                    total += 1
        for half in HALF_ORDER:
            if half == "OT" and counts.get(half, 0) == 0:
                continue
            rows.append(
                {
                    "team_id": team_id,
                    "time": team_name,
                    "tempo": half,
                    "gols": counts.get(half, 0),
                    "pct": _round(100 * counts.get(half, 0) / total) if total else 0,
                }
            )
    fields = ["team_id", "time", "tempo", "gols", "pct"]
    return fields, rows


def build_subs_detalhado(all_games, id_to_name):
    rows = []
    for record in all_games.values():
        for sub in record["substituicoes"]:
            side = sub.get("side")
            team_name = record.get(side, {}).get("nome") if side else id_to_name.get(sub.get("team_id"))
            rows.append(
                {
                    "event_id": record["event_id"],
                    "data_jogo": record["data_jogo"],
                    "time": team_name,
                    "mando": side,
                    "minuto": sub["minute"],
                    "minuto_display": sub["minute_display"],
                    "jogador_entrou": sub.get("player_in"),
                    "jogador_saiu": sub.get("player_out"),
                    "motivo": sub.get("reason"),
                }
            )
    rows.sort(key=lambda r: (r["data_jogo"], r["minuto"]))
    fields = ["event_id", "data_jogo", "time", "mando", "minuto", "minuto_display", "jogador_entrou", "jogador_saiu", "motivo"]
    return fields, rows


def build_subs_padrao(team_games):
    rows = []
    for team_id, records in team_games.items():
        first, second, third, totals = [], [], [], []
        team_name = None
        for record in records:
            ref, _, mando = team_side(record, team_id)
            team_name = ref["nome"]
            minutes = sorted(s["minute"] for s in record["substituicoes"] if s.get("side") == mando)
            totals.append(len(minutes))
            if len(minutes) >= 1:
                first.append(minutes[0])
            if len(minutes) >= 2:
                second.append(minutes[1])
            if len(minutes) >= 3:
                third.append(minutes[2])

        def avg(values):
            return _round(sum(values) / len(values)) if values else None

        rows.append(
            {
                "team_id": team_id,
                "time": team_name,
                "media_substituicoes_por_jogo": avg(totals),
                "minuto_medio_1a_sub": avg(first),
                "minuto_medio_2a_sub": avg(second),
                "minuto_medio_3a_sub": avg(third),
            }
        )
    fields = ["team_id", "time", "media_substituicoes_por_jogo", "minuto_medio_1a_sub", "minuto_medio_2a_sub", "minuto_medio_3a_sub"]
    return fields, rows


def build_subs_jogadores(team_games, canonical_maps):
    rows = []
    for team_id, records in team_games.items():
        roster = canonical_maps[team_id]
        team_name = None
        stats = defaultdict(lambda: {"entrou": 0, "saiu": 0, "minutos_entrada": []})
        for record in records:
            ref, _, mando = team_side(record, team_id)
            team_name = ref["nome"]
            for sub in record["substituicoes"]:
                if sub.get("side") != mando:
                    continue
                if sub.get("player_in"):
                    name = resolve_name(sub["player_in"], roster)
                    stats[name]["entrou"] += 1
                    stats[name]["minutos_entrada"].append(sub["minute"])
                if sub.get("player_out"):
                    stats[resolve_name(sub["player_out"], roster)]["saiu"] += 1
        for player, entry in stats.items():
            if not player:
                continue
            minutos = entry["minutos_entrada"]
            rows.append(
                {
                    "time": team_name,
                    "team_id": team_id,
                    "jogador": player,
                    "vezes_entrou": entry["entrou"],
                    "vezes_saiu": entry["saiu"],
                    "minuto_medio_entrada": _round(sum(minutos) / len(minutos)) if minutos else None,
                }
            )
    rows.sort(key=lambda r: (r["time"], -r["vezes_entrou"]))
    fields = ["time", "team_id", "jogador", "vezes_entrou", "vezes_saiu", "minuto_medio_entrada"]
    return fields, rows


def build_partidas(all_games):
    rows = []
    for record in all_games.values():
        home, away = record["casa"], record["fora"]
        rows.append(
            {
                "event_id": record["event_id"],
                "data_jogo": record["data_jogo"],
                "status": record["status"],
                "time_casa": home["nome"],
                "time_fora": away["nome"],
                "gols_casa": _to_int(home["gols"]),
                "gols_fora": _to_int(away["gols"]),
                "formacao_casa": home["formacao"],
                "formacao_fora": away["formacao"],
                "posse_casa": home["estatisticas"].get("possessionPct"),
                "posse_fora": away["estatisticas"].get("possessionPct"),
                "finalizacoes_casa": home["estatisticas"].get("totalShots"),
                "finalizacoes_fora": away["estatisticas"].get("totalShots"),
                "total_gols": _to_int(home["gols"]) + _to_int(away["gols"]),
            }
        )
    rows.sort(key=lambda r: r["data_jogo"])
    fields = ["event_id", "data_jogo", "status", "time_casa", "time_fora", "gols_casa", "gols_fora", "formacao_casa", "formacao_fora", "posse_casa", "posse_fora", "finalizacoes_casa", "finalizacoes_fora", "total_gols"]
    return fields, rows


def build_h2h(h2h_games, id_to_name):
    rows = []
    resumo = {"total": 0, "vitorias_goias": 0, "vitorias_sport": 0, "empates": 0, "gols_goias": 0, "gols_sport": 0}
    goias_id = config.TEAM_ID_GOIAS
    sport_id = config.TEAM_ID_SPORT
    for game in h2h_games:
        home_id = game["home_team_id"]
        away_id = game["away_team_id"]
        home_score = _to_int(game["home_score"])
        away_score = _to_int(game["away_score"])
        scores = {home_id: home_score, away_id: away_score}
        if goias_id in scores and sport_id in scores:
            resumo["total"] += 1
            resumo["gols_goias"] += scores[goias_id]
            resumo["gols_sport"] += scores[sport_id]
            if scores[goias_id] > scores[sport_id]:
                resumo["vitorias_goias"] += 1
            elif scores[goias_id] < scores[sport_id]:
                resumo["vitorias_sport"] += 1
            else:
                resumo["empates"] += 1
        rows.append(
            {
                "game_id": game["game_id"],
                "data_jogo": game["date"],
                "competicao": game["competition"],
                "time_casa": id_to_name.get(home_id, home_id),
                "time_fora": id_to_name.get(away_id, away_id),
                "placar": game["score"],
                "gols_casa": home_score,
                "gols_fora": away_score,
            }
        )
    rows.sort(key=lambda r: r["data_jogo"] or "", reverse=True)
    detail_fields = ["game_id", "data_jogo", "competicao", "time_casa", "time_fora", "placar", "gols_casa", "gols_fora"]

    resumo_rows = [
        {
            "fonte": "espn_ultimos_confrontos",
            "total_jogos": resumo["total"],
            "vitorias_goias": resumo["vitorias_goias"],
            "vitorias_sport": resumo["vitorias_sport"],
            "empates": resumo["empates"],
            "gols_goias": resumo["gols_goias"],
            "gols_sport": resumo["gols_sport"],
        },
        {
            "fonte": contexto.H2H_HISTORICO_PLANEJAMENTO["fonte"],
            "total_jogos": contexto.H2H_HISTORICO_PLANEJAMENTO["total_jogos"],
            "vitorias_goias": contexto.H2H_HISTORICO_PLANEJAMENTO["vitorias_goias"],
            "vitorias_sport": contexto.H2H_HISTORICO_PLANEJAMENTO["vitorias_sport"],
            "empates": contexto.H2H_HISTORICO_PLANEJAMENTO["empates"],
            "gols_goias": None,
            "gols_sport": None,
        },
    ]
    resumo_fields = ["fonte", "total_jogos", "vitorias_goias", "vitorias_sport", "empates", "gols_goias", "gols_sport"]
    return (detail_fields, rows), (resumo_fields, resumo_rows)


def build_ao_vivo_estado(live_state):
    if not live_state:
        return ["campo", "valor"], []
    placar = live_state.get("placar", {})
    eventos = live_state.get("eventos", {})
    row = {
        "event_id": live_state.get("event_id"),
        "updated_at": live_state.get("updated_at"),
        "status": live_state.get("status"),
        "status_detail": live_state.get("status_detail"),
        "clock": live_state.get("clock"),
        "periodo": live_state.get("period"),
        "time_casa": placar.get("casa", {}).get("time"),
        "gols_casa": placar.get("casa", {}).get("gols"),
        "time_fora": placar.get("fora", {}).get("time"),
        "gols_fora": placar.get("fora", {}).get("gols"),
        "formacao_casa": live_state.get("formacoes", {}).get("casa"),
        "formacao_fora": live_state.get("formacoes", {}).get("fora"),
        "total_gols": len(eventos.get("gols", [])),
        "total_cartoes": len(eventos.get("cartoes", [])),
        "total_substituicoes": len(eventos.get("substituicoes", [])),
    }
    fields = ["event_id", "updated_at", "status", "status_detail", "clock", "periodo", "time_casa", "gols_casa", "time_fora", "gols_fora", "formacao_casa", "formacao_fora", "total_gols", "total_cartoes", "total_substituicoes"]
    return fields, [row]


def build_ao_vivo_eventos(log_rows, id_to_name):
    rows = []
    for entry in log_rows:
        rows.append(
            {
                "logged_at": entry.get("logged_at"),
                "tipo": entry.get("tipo"),
                "minuto": entry.get("minute"),
                "team_id": entry.get("team_id"),
                "time": id_to_name.get(entry.get("team_id"), entry.get("team_id")),
                "marcador": entry.get("scorer"),
                "assistente": entry.get("assist"),
                "cartao": entry.get("color"),
                "descricao": entry.get("text"),
            }
        )
    fields = ["logged_at", "tipo", "minuto", "team_id", "time", "marcador", "assistente", "cartao", "descricao"]
    return fields, rows


def build_ao_vivo_resumo(log_rows, id_to_name):
    counts = defaultdict(int)
    for entry in log_rows:
        counts[(entry.get("team_id"), entry.get("tipo"))] += 1
    rows = []
    for (team_id, tipo), total in sorted(counts.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        rows.append(
            {
                "team_id": team_id,
                "time": id_to_name.get(team_id, team_id),
                "tipo_evento": tipo,
                "total": total,
            }
        )
    fields = ["team_id", "time", "tipo_evento", "total"]
    return fields, rows


def build_contexto():
    row = dict(contexto.CONTEXTO_PARTIDA)
    fields = list(row.keys())
    return fields, [row]


def build_desfalques():
    fields = ["time", "jogador", "motivo", "status"]
    return fields, contexto.DESFALQUES


def run():
    structured = _load_json(os.path.join(config.DATA_DIR, "jogos_estruturado.json"), {})
    if not structured:
        raise SystemExit("data/jogos_estruturado.json nao encontrado. Rode coleta_temporada.py primeiro.")
    live_state = _load_json(os.path.join(config.DATA_DIR, "partida_ao_vivo.json"), {})
    log_rows = _load_jsonl(os.path.join(config.OUTPUTS_DIR, "insights_log.jsonl"))

    all_games, team_games, id_to_name, roster_by_team = build_indexes(structured)
    canonical_maps = build_canonical_maps(team_games)

    try:
        summary = espn_api.get_summary(config.MATCH_EVENT_ID)
        h2h_games = parsers.parse_h2h(summary)
    except Exception as error:
        print(f"  ! nao foi possivel obter H2H da ESPN: {error}")
        h2h_games = []

    jog_fields, jog_rows = build_jogadores(team_games, canonical_maps)
    (h2h_detail, h2h_resumo) = build_h2h(h2h_games, id_to_name)

    tables = [
        ("01_times", "times_resumo_temporada.csv", build_times_resumo(team_games)),
        ("01_times", "times_desempenho_mando.csv", build_times_mando(team_games)),
        ("01_times", "times_forma_recente.csv", build_forma_recente(team_games)),
        ("02_jogadores", "jogadores_estatisticas.csv", (jog_fields, jog_rows)),
        ("02_jogadores", "jogadores_artilheiros.csv", _ranked(jog_rows, "gols", ["jogos_titular", "assistencias"])),
        ("02_jogadores", "jogadores_assistentes.csv", _ranked(jog_rows, "assistencias", ["jogos_titular", "gols"])),
        ("02_jogadores", "jogadores_disciplina.csv", _ranked(jog_rows, "cartoes_amarelos", ["cartoes_vermelhos", "jogos_titular"])),
        ("03_gols", "gols_detalhado.csv", build_gols_detalhado(all_games)),
        ("03_gols", "gols_marcados_por_faixa.csv", build_gols_por_faixa(team_games, sofridos=False)),
        ("03_gols", "gols_marcados_por_tempo.csv", build_gols_por_tempo(team_games, sofridos=False)),
        ("03_gols", "gols_sofridos_por_faixa.csv", build_gols_por_faixa(team_games, sofridos=True)),
        ("03_gols", "gols_sofridos_por_tempo.csv", build_gols_por_tempo(team_games, sofridos=True)),
        ("04_taticas", "formacoes_por_time.csv", build_formacoes(team_games)),
        ("04_taticas", "substituicoes_detalhado.csv", build_subs_detalhado(all_games, id_to_name)),
        ("04_taticas", "substituicoes_padrao_por_time.csv", build_subs_padrao(team_games)),
        ("04_taticas", "substituicoes_jogadores.csv", build_subs_jogadores(team_games, canonical_maps)),
        ("05_confrontos", "confrontos_diretos_h2h.csv", h2h_detail),
        ("05_confrontos", "confrontos_resumo.csv", h2h_resumo),
        ("06_partidas", "partidas_resultados.csv", build_partidas(all_games)),
        ("07_ao_vivo", "ao_vivo_estado_atual.csv", build_ao_vivo_estado(live_state)),
        ("07_ao_vivo", "ao_vivo_eventos.csv", build_ao_vivo_eventos(log_rows, id_to_name)),
        ("07_ao_vivo", "ao_vivo_eventos_resumo.csv", build_ao_vivo_resumo(log_rows, id_to_name)),
        ("08_contexto", "contexto_partida.csv", build_contexto()),
        ("08_contexto", "desfalques.csv", build_desfalques()),
    ]

    print(f"Construindo camada ouro em {config.FINAL_OUTPUT_DIR}")
    total_files = 0
    for subfolder, filename, (fields, rows) in tables:
        path, count = write_table(subfolder, filename, fields, rows)
        total_files += 1
        print(f"  [{subfolder}] {filename}: {count} linhas")
    print(f"Concluido. {total_files} tabelas geradas.")


if __name__ == "__main__":
    run()
