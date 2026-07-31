import argparse
import time

import analise_prejogo
import coleta_temporada
import construir_camada_ouro
import llm_client
import monitor_ao_vivo


def _step(numero, titulo):
    print(f"\n{'=' * 60}\n[{numero}] {titulo}\n{'=' * 60}")


def executar(limit=None, skip_coleta=False, skip_ouro=False, skip_prejogo=False, live_once=False):
    inicio = time.time()

    if skip_coleta:
        print("[1] Coleta da temporada: PULADA (reutilizando data/ existente)")
    else:
        _step(1, "Coleta da temporada (ESPN)")
        coleta_temporada.run(limit=limit)

    if skip_ouro:
        print("[2] Camada ouro: PULADA")
    else:
        _step(2, "Construcao da camada ouro (final-output/)")
        construir_camada_ouro.run()

    if skip_prejogo:
        print("[3] Relatorio pre-jogo: PULADO")
    else:
        _step(3, f"Relatorio pre-jogo (IA: {llm_client.status()})")
        analise_prejogo.gerar_relatorio()

    if live_once:
        _step(4, "Ciclo unico do monitor ao vivo")
        monitor_ao_vivo.process_once()

    print(f"\nPipeline concluido em {time.time() - inicio:.1f}s.")


def parse_args():
    parser = argparse.ArgumentParser(description="Pipeline: coleta -> camada ouro -> relatorio pre-jogo")
    parser.add_argument("--limit", type=int, default=None, help="Limita jogos por time na coleta (amostragem)")
    parser.add_argument("--skip-coleta", action="store_true", help="Nao recoleta a temporada")
    parser.add_argument("--skip-ouro", action="store_true", help="Nao reconstroi a camada ouro")
    parser.add_argument("--skip-prejogo", action="store_true", help="Nao gera o relatorio pre-jogo")
    parser.add_argument("--live-once", action="store_true", help="Roda um ciclo do monitor ao vivo ao final")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    executar(
        limit=args.limit,
        skip_coleta=args.skip_coleta,
        skip_ouro=args.skip_ouro,
        skip_prejogo=args.skip_prejogo,
        live_once=args.live_once,
    )
