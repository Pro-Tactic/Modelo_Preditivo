# formacoes.py — Mapa tático e perfis derivados para uso no motor de simulação

MAPA_FORMACAO = {
    "3-1-4-2": ["GK","RCB","CB","LCB","VOL1","RM","CM1","CM2","LM","ST1","ST2"],
    "3-2-4-1": ["GK","RCB","CB","LCB","VOL1","VOL2","RAM","CAM1","CAM2","LAM","ST"],
    "3-3-1-3": ["GK","RCB","CB","LCB","VOL1","VOL2","VOL3","CAM","RW","ST","LW"],
    "3-4-1-2": ["GK","RCB","CB","LCB","RM","CM1","CM2","LM","CAM","ST1","ST2"],
    "3-4-2-1": ["GK","RCB","CB","LCB","RM","CM1","CM2","LM","RAM","LAM","ST"],
    "3-4-3":   ["GK","RCB","CB","LCB","RM","CM1","CM2","LM","RW","ST","LW"],
    "3-5-1-1": ["GK","RCB","CB","LCB","RM","CM1","CM2","CM3","LM","CAM","ST"],
    "3-5-2":   ["GK","RCB","CB","LCB","RM","CM1","CM2","CM3","LM","ST1","ST2"],
    "4-1-2-3": ["GK","RB","RCB","LCB","LB","VOL1","CM1","CM2","RW","ST","LW"],
    "4-1-3-2": ["GK","RB","RCB","LCB","LB","VOL1","CM1","CAM","CM2","ST1","ST2"],
    "4-1-4-1": ["GK","RB","RCB","LCB","LB","VOL1","RM","CM1","CM2","LM","ST"],
    "4-2-1-3": ["GK","RB","RCB","LCB","LB","VOL1","VOL2","CAM","RW","ST","LW"],
    "4-2-2-2": ["GK","RB","RCB","LCB","LB","VOL1","VOL2","RAM","LAM","ST1","ST2"],
    "4-2-3-1": ["GK","RB","RCB","LCB","LB","VOL1","VOL2","RAM","CAM","LAM","ST"],
    "4-3-1-2": ["GK","RB","RCB","LCB","LB","CM1","CM2","CM3","CAM","ST1","ST2"],
    "4-3-2-1": ["GK","RB","RCB","LCB","LB","CM1","CM2","CM3","RAM","LAM","ST"],
    "4-3-3":   ["GK","RB","RCB","LCB","LB","CM1","CM2","CM3","RW","ST","LW"],
    "4-4-1-1": ["GK","RB","RCB","LCB","LB","RM","CM1","CM2","LM","CAM","ST"],
    "4-4-2":   ["GK","RB","RCB","LCB","LB","RM","CM1","CM2","LM","ST1","ST2"],
    "4-5-1":   ["GK","RB","RCB","LCB","LB","RM","CM1","CM2","CM3","LM","ST"],
    "5-2-3":   ["GK","RWB","RCB","CB","LCB","LWB","CM1","CM2","RW","ST","LW"],
    "5-3-2":   ["GK","RWB","RCB","CB","LCB","LWB","CM1","CM2","CM3","ST1","ST2"],
    "5-4-1":   ["GK","RWB","RCB","CB","LCB","LWB","RM","CM1","CM2","LM","ST"],
}

# Posições classificadas por papel tático
POSICOES_OFENSIVAS  = {"ST","ST1","ST2","RW","LW","CAM","RAM","LAM","CAM1","CAM2"}
POSICOES_DEFENSIVAS = {"GK","RB","LB","RCB","LCB","CB","RWB","LWB","VOL1","VOL2","VOL3"}

def calcular_perfis(mapa):
    """Retorna dict {formacao: {idx_ataque, idx_defesa}} normalizado entre 0 e 1."""
    perfis = {}
    for form, posicoes in mapa.items():
        sem_gk = [p for p in posicoes if p != "GK"]
        n = len(sem_gk) or 1
        perfis[form] = {
            "idx_ataque": sum(1 for p in sem_gk if p in POSICOES_OFENSIVAS) / n,
            "idx_defesa": sum(1 for p in sem_gk if p in POSICOES_DEFENSIVAS) / n,
        }
    return perfis

PERFIL_FORMACAO = calcular_perfis(MAPA_FORMACAO)

# Médias globais (usadas como baseline na normalização do efeito)
_vals_atk = [p["idx_ataque"] for p in PERFIL_FORMACAO.values()]
_vals_def = [p["idx_defesa"] for p in PERFIL_FORMACAO.values()]
MEDIA_IDX_ATAQUE = sum(_vals_atk) / len(_vals_atk)
MEDIA_IDX_DEFESA = sum(_vals_def) / len(_vals_def)
