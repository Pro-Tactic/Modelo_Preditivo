import json
import os
import config
import llm_client

def main():
    print("Iniciando geração do Relatório Pós-Jogo...")
    
    # 1. Carregar dados do jogo
    with open(os.path.join(config.DATA_DIR, "partida_ao_vivo.json"), "r", encoding="utf-8") as f:
        partida = json.load(f)
        
    with open(os.path.join(config.DATA_DIR, "estatisticas_finais.json"), "r", encoding="utf-8") as f:
        stats = json.load(f)
        
    placar = partida.get("placar", {})
    eventos = partida.get("eventos", {})
    
    # 2. Construir o Prompt
    system_prompt = (
        f"Você é o analista tático Chefe do {config.TIME_ANALISE}, trabalhando para a comissão técnica de {config.TECNICO_ANALISE}. "
        "REGRA 1: Escreva EXCLUSIVAMENTE em Português do Brasil. "
        f"REGRA 2: A análise deve focar apenas no {config.TIME_ANALISE} e como ele performou. "
        "REGRA 3: Faça uma análise crítica e profissional de pós-jogo, sem limites severos de tamanho, estruturando em seções com marcação markdown (Pontos Fortes, Pontos Fracos, Evolução 1T vs 2T, Ajustes para o Próximo Jogo)."
    )
    
    prompt = (
        f"RESUMO DA PARTIDA:\n"
        f"Placar Final: {placar.get('casa', {}).get('time')} {placar.get('casa', {}).get('gols')} x {placar.get('fora', {}).get('gols')} {placar.get('fora', {}).get('time')}\n\n"
        f"ESTATÍSTICAS DO INTERVALO:\n"
        f"{json.dumps(stats.get('intervalo'), ensure_ascii=False, indent=2)}\n\n"
        f"ESTATÍSTICAS FINAIS:\n"
        f"{json.dumps(stats.get('final'), ensure_ascii=False, indent=2)}\n\n"
        f"EVENTOS IMPORTANTES (Gols, Cartões, Subs):\n"
        f"{json.dumps(eventos, ensure_ascii=False, indent=2)}\n\n"
        "Com base nos dados acima, crie o 'Relatório Tático Pós-Jogo'. "
        "Compare a performance do primeiro tempo com a do segundo (usando a subtração das estatísticas finais pelas do intervalo). "
        "Destaque o que funcionou (Pontos Fortes), o que falhou (Pontos Fracos/Vulnerabilidades) e o que o Pepa precisa focar nos treinamentos da semana para a próxima rodada da Série B."
    )
    
    print("Enviando dados para a Nvidia (Nemotron 120B)... aguarde...")
    try:
        relatorio = llm_client.generate(prompt, system=system_prompt, temperature=0.7)
        
        # Salvar o relatório
        out_path = os.path.join(config.OUTPUTS_DIR, "relatorio_posjogo.md")
        os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(relatorio)
            
        print("\n" + "="*50)
        print("RELATÓRIO GERADO COM SUCESSO!")
        print("="*50 + "\n")
        print(relatorio)
        print("\n" + "="*50)
        print(f"Salvo em: {out_path}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erro ao gerar relatório: {e}")

if __name__ == "__main__":
    main()
