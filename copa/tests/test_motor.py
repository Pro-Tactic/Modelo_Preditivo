import pytest
import sys
import os
from datetime import datetime, timedelta

# Adicionar pasta raiz 'copa' no path para importar motor_simulacao
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import motor_simulacao

def test_peso_recencia():
    # O jogo de hoje deve ter peso 1
    peso_hoje = motor_simulacao.peso_recencia(datetime.now())
    # O jogo de 100 dias atrás
    peso_100_dias = motor_simulacao.peso_recencia(datetime.now() - timedelta(days=100))
    
    assert peso_hoje == 1.0, "O peso de hoje deve ser 1.0"
    assert peso_100_dias < peso_hoje, "Jogo antigo deve ter peso menor"
    assert peso_100_dias > 0.0, "O peso não pode ser negativo"

def test_obter_pontos_fifa_fallback():
    pts_inexistente = motor_simulacao.obter_pontos_fifa("Narnia")
    assert pts_inexistente == 1300, "Time desconhecido deve cair no fallback de 1300 pts"

def test_sortear_jogador_evento():
    # Testar o cache/fallback de "Desconhecido" para time sem convocacao
    jogador = motor_simulacao.sortear_jogador_evento("Narnia", "gol")
    assert isinstance(jogador, str)
    assert jogador == "Desconhecido"

def test_simular_jogo():
    gols1, gols2 = motor_simulacao.simular_jogo("Brazil", "Argentina")
    assert isinstance(gols1, int)
    assert isinstance(gols2, int)
    assert gols1 >= 0
    assert gols2 >= 0
