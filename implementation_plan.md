# Sistema de Análise Tática ao Vivo — Goiás x Sport (22/07/2026)
## Comissão de Análise de Desempenho — Sport Club do Recife

> **Revisão 2** — Atualizado com base nos comentários: Gemini confirmado como IA, API-Football descartada (dados só até 2024), ESPN como fonte principal, TheSportsDB avaliado.

Este documento descreve o plano técnico completo para um sistema de coleta de dados + IA generativa em tempo real, inspirado no projeto da Copa do Mundo e adaptado para a Série B 2026.

---

## Contexto da Partida

| Campo | Detalhe |
|---|---|
| **Partida** | Goiás x Sport Recife |
| **Competição** | Campeonato Brasileiro Série B 2026 — 19ª Rodada |
| **Data/Hora** | 22/07/2026 às 20h30 |
| **Local** | Estádio Hailé Pinheiro (Serrinha), Goiânia |
| **Classificação** | Goiás 7º (28pts) vs Sport 9º (27pts) |
| **Desfalques Sport** | Marcelo Benevenuto (susp.), Chrystian Barletta (susp.), Marlon Douglas (susp.), Carlos de Pena (lesão), Zé Lucas |
| **Retorno Sport** | Clayson disponível |
| **Momento Sport** | 7 jogos sem vitória |

---

## Pergunta 1: A API da ESPN serve para este projeto?

### Diagnóstico Atualizado

A ESPN possui **dois níveis de endpoints** não-documentados, que formam a espinha dorsal deste projeto:

| Endpoint | Tipo de dados | Uso no projeto |
|---|---|---|
| `site.api.espn.com/apis/site/v2/...` | Scoreboard, resumo, escalações, eventos | Monitor ao vivo + coleta de temporada |
| `sports.core.api.espn.com/v2/...` | Histórico de jogadores, estatísticas de jogo, logs de temporada | Coleta mais rica da temporada 2026 |

**O que a ESPN consegue fazer (confirmado):**
- ✅ Placar ao vivo (atualização a cada ~30-60s)
- ✅ Escalações confirmadas da partida
- ✅ Eventos da partida ao vivo (gols, cartões, substituições)
- ✅ Resultados e calendário completo da Série B 2026 (`bra.2`)
- ✅ Todos os jogos da temporada de Goiás e Sport
- ✅ Posse de bola, finalizações, estatísticas básicas do box score histórico
- ✅ Dados de jogadores (estatísticas de temporada por atleta)

**O que a ESPN NÃO oferece:**
- ❌ xG (Expected Goals) — métrica avançada proprietária da Opta/StatsBomb
- ❌ Mapa de calor / posições em campo
- ❌ Passes progressivos, pressão alta (métricas Wyscout/StatsBomb)

> [!NOTE]
> **Sobre estatísticas avançadas históricas:** A ESPN oferece dados de box score histórico (posse, chutes, escanteios, faltas) via `sports.core.api.espn.com`, o que é **suficiente para alimentar o contexto da IA**. xG e dados de posicionamento não estão disponíveis gratuitamente em nenhuma API pública para a Série B.

### Avaliação do TheSportsDB

| Critério | TheSportsDB Free | TheSportsDB Premium ($9/mês) |
|---|---|---|
| Escalações ao vivo | ❌ | ✅ (delay ~2min) |
| Eventos da partida | ❌ | ✅ (limitado) |
| Histórico Série B 2026 | ⚠️ Incompleto (crowd-sourced) | ⚠️ Incompleto |
| Logos e imagens dos times | ✅ Excelente | ✅ Excelente |

> [!WARNING]
> **TheSportsDB não é recomendado como fonte primária** para este projeto. Por ser crowd-sourced, a cobertura da Série B pode ter dados incompletos ou desatualizados. Seu uso fica restrito a **metadados visuais** (logos dos times, foto do estádio) para enriquecer o dashboard.

### Stack de APIs Definitiva

| API | Papel | Custo |
|---|---|---|
| **ESPN `site.api.espn.com`** | 🥇 Fonte principal — ao vivo + temporada (eventos, escalações, resultados) | Gratuito |
| **ESPN `sports.core.api.espn.com`** | 🥈 Stats históricas mais ricas (posse, chutes, estatísticas de temporada por jogador) | Gratuito |
| **TheSportsDB (free)** | 🎨 Logos e metadados visuais para o dashboard | Gratuito |
| **API-Football** | ❌ **Descartada** (dados apenas até 2024, limite de chamadas insuficiente) | — |
| **Sofascore** | ❌ Bloqueada | — |

**Estratégia definitiva: ESPN como única fonte de dados (temporada + ao vivo) + TheSportsDB apenas para logos no dashboard.**

---

## Pergunta 2: Quais insights a IA irá gerar?

Os insights são divididos em dois momentos: **pré-jogo** (baseados no contexto da temporada) e **ao vivo** (baseados nos dados da partida em andamento).

### Insights Pré-Jogo (alimentados pelos dados da temporada)
1. Análise tática das formações mais usadas por cada time na temporada
2. Desempenho dos titulares prováveis (artilheiros, assistências)
3. Histórico de confrontos diretos (33 jogos, Goiás 15 x 12 Sport)
4. Padrão de gols (minutos, primeiros/segundos tempos)
5. Análise do momento dos times (forma recente, últimos 5 jogos)
6. Alerta sobre desfalques e impacto estimado na escalação

### Insights ao Vivo (gerados a cada atualização)
1. **Análise de escalação confirmada** — como a formação escolhida se compara às mais usadas na temporada
2. **Alerta de mudança tática** — quando uma substituição sinaliza mudança de esquema
3. **Análise de gol** — quem marcou, como foi o lance, padrão do jogador na temporada
4. **Análise de pressão** — contexto do resultado sobre a necessidade tática do Sport
5. **Sugestão de substituição** — baseada no padrão de uso de reservas do Gilmar Dal Pozzo
6. **Análise de cartões** — risco de expulsão, histórico do jogador
7. **Análise de momentum** — tendência da partida baseada nos eventos acumulados
8. **Previsão de resultado** — probabilidade dinâmica atualizada a cada evento

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────┐
│                FASE 1: PRÉ-JOGO                      │
│  coleta_temporada.py                                  │
│  └── ESPN site.api + sports.core.api                 │
│      ├── /teams/{id}/schedule (18 jogos Goiás)       │
│      ├── /teams/{id}/schedule (18 jogos Sport)       │
│      ├── /summary?event={id} → escalações + eventos  │
│      └── /statistics?event={id} → posse, chutes      │
│  → Gera: goias_temporada.csv + sport_temporada.csv   │
└─────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│              FASE 2: CONTEXTO PRÉ-JOGO               │
│  analise_prejogo.py                                   │
│  └── Google Gemini Flash 2.0 (API key do usuário)    │
│      Input: CSVs + desfalques + histórico H2H        │
│      → Gera: relatorio_prejogo.md (para a comissão)  │
└─────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│              FASE 3: MONITORAMENTO AO VIVO           │
│  monitor_ao_vivo.py (loop a cada 60s)                │
│  └── ESPN site.api.espn.com                          │
│      ├── /scoreboard?league=bra.2 → placar e minuto  │
│      └── /summary?event={id} → eventos novos         │
│      → Detecta: gols, substituições, cartões         │
└─────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│              FASE 4: ENGINE DE INSIGHTS IA           │
│  insight_engine.py                                    │
│  └── Google Gemini Flash 2.0                         │
│      Input: contexto_temporada + estado_atual        │
│      Output: insight formatado para a comissão       │
└─────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│              FASE 5: DASHBOARD                       │
│  dashboard.py (Streamlit)                            │
│  ├── Logos via TheSportsDB free API                  │
│  └── Exibe insights ao vivo para a comissão técnica  │
└─────────────────────────────────────────────────────┘
```

---

## Proposed Changes

### Estrutura de Diretórios do Projeto

```
Modelo_Preditivo/
└── sport_ao_vivo/
    ├── config.py                   # Chaves de API, IDs dos times
    ├── coleta_temporada.py         # [FASE 1] Coleta dados da Season 2026
    ├── analise_prejogo.py          # [FASE 2] Gera relatório pré-jogo com IA
    ├── monitor_ao_vivo.py          # [FASE 3] Loop de monitoramento ao vivo
    ├── insight_engine.py           # [FASE 4] Envia dados à IA e processa resposta
    ├── dashboard.py                # [FASE 5] Interface visual para a comissão
    ├── data/
    │   ├── goias_temporada.csv     # Gerado pela Fase 1
    │   ├── sport_temporada.csv     # Gerado pela Fase 1
    │   └── partida_ao_vivo.json    # Atualizado pelo monitor a cada ciclo
    └── outputs/
        ├── relatorio_prejogo.md    # Gerado pela Fase 2
        └── insights_log.jsonl      # Log de todos os insights gerados ao vivo
```

---

### Componente 1: Configuração (`config.py`)

#### [NEW] config.py
- `GEMINI_API_KEY` — chave do Google Gemini (fornecida pelo usuário)
- IDs dos times na ESPN: Goiás e Sport (descobertos via API de teams)
- `ESPN_LEAGUE = "bra.2"` (Série B)
- `ESPN_SEASON = 2026`
- `THESPORTSDB_TEAM_GOIAS` e `THESPORTSDB_TEAM_SPORT` — IDs para logos
- Intervalos do monitor: `POLL_INTERVAL_SECONDS = 60`

---

### Componente 2: Coleta da Temporada (`coleta_temporada.py`)

#### [NEW] coleta_temporada.py

Coleta todos os jogos de Goiás e Sport na temporada 2026, no mesmo formato estrutural do `jogos.csv` do projeto Copa:

| Campo | Equivalente no jogos.csv |
|---|---|
| `time_referencia` | Goiás / Sport |
| `competicao` | Série B 2026 |
| `data_jogo` | Timestamp do jogo |
| `time_casa / time_fora` | Mandante / Visitante |
| `resultado` | Placar final |
| `formacao_casa / formacao_fora` | Formação tática |
| `titulares_casa / titulares_fora` | 11 titulares |
| `substituicoes` | Trocas realizadas |
| `gols` | Marcadores e minutos |
| `assistencias` | Passadores |

**Endpoints ESPN utilizados:**
```
# Calendário e resultados da temporada
GET site.api.espn.com/apis/site/v2/sports/soccer/bra.2/teams/{team_id}/schedule?season=2026

# Box score completo (escalações, eventos, estatísticas) por jogo
GET site.api.espn.com/apis/site/v2/sports/soccer/bra.2/summary?event={event_id}

# Estatísticas de temporada por jogador
GET sports.core.api.espn.com/v2/sports/soccer/leagues/bra.2/seasons/2026/teams/{team_id}/statistics
```

---

### Componente 3: Análise Pré-Jogo (`analise_prejogo.py`)

#### [NEW] analise_prejogo.py

Lê os CSVs da temporada e envia ao modelo de IA um prompt estruturado que inclui:
- Histórico completo da temporada de ambos os times
- Desfalques confirmados
- Histórico de confrontos diretos
- Pedido de análise tática + prognóstico

**Output esperado:** `outputs/relatorio_prejogo.md` — documento de 1-2 páginas para a comissão técnica antes da partida.

---

### Componente 4: Monitor ao Vivo (`monitor_ao_vivo.py`)

#### [NEW] monitor_ao_vivo.py

Loop `while True` com intervalo de 60 segundos que:
1. Chama a ESPN API para o placar ao vivo da Série B
2. Detecta o jogo Goiás x Sport pelo horário/slug
3. Extrai eventos novos (gols, substituições, cartões amarelos/vermelhos)
4. Compara com o estado anterior para identificar **apenas eventos novos**
5. Salva o estado atual em `data/partida_ao_vivo.json`
6. Chama o `insight_engine.py` quando detectar evento novo

**Endpoints ESPN utilizados:**
```
# Scoreboard ao vivo da Série B
GET https://site.api.espn.com/apis/site/v2/sports/soccer/bra.2/scoreboard

# Detalhes ao vivo da partida (eventos, placar, escalação)
GET https://site.api.espn.com/apis/site/v2/sports/soccer/bra.2/summary?event={id}
```

> [!NOTE]
> Sem fallback externo. Em caso de falha da ESPN, o monitor registra a falha no log e tenta novamente no próximo ciclo (60s). O estado anterior é preservado para não gerar insights duplicados.

---

### Componente 5: Engine de Insights IA (`insight_engine.py`)

#### [NEW] insight_engine.py

Responsável por montar o prompt contextual e chamar o modelo de IA.

**Estrutura do prompt enviado:**

```
[CONTEXTO DA TEMPORADA]
- Dados completos de Goiás na Série B 2026 (CSV)
- Dados completos do Sport na Série B 2026 (CSV)
- Desfalques e situação dos times

[ESTADO ATUAL DA PARTIDA]
- Minuto: XX'
- Placar: Goiás X x Sport Y
- Eventos ocorridos até agora: [lista]
- Evento mais recente: [descrição]

[INSTRUÇÃO]
Você é o analista de dados da comissão técnica do Sport Club do Recife.
Com base nos dados da temporada e no estado atual da partida, gere um insight
tático de até 150 palavras focado em AÇÃO IMEDIATA para o técnico Gilmar Dal Pozzo.
```

**Tipos de insight por gatilho:**

| Gatilho | Tipo de Insight |
|---|---|
| Início da partida (escalação confirmada) | Análise tática da formação adversária |
| Gol sofrido | Análise da vulnerabilidade + sugestão de ajuste |
| Gol marcado | Reforço do padrão que gerou o gol |
| Substituição do adversário | Alerta sobre mudança tática do Goiás |
| Cartão amarelo de jogador do Sport | Risco disciplinar + análise |
| Intervalo (45') | Análise completa do 1º tempo + sugestões |
| 60'-70' sem gol | Análise de momentum + gatilho para substituições |
| Entrada nos acréscimos | Orientação para os minutos finais |

---

### Componente 6: Dashboard (`dashboard.py`)

#### [NEW] dashboard.py

Interface visual simples em **Streamlit** ou HTML puro para a comissão técnica:

- **Painel esquerdo:** Estado atual da partida (placar, minuto, escalações)
- **Painel central:** Feed de insights ao vivo (em tempo real, com timestamp)
- **Painel direito:** Gráfico de momentum + histórico de eventos
- **Botão manual:** "Gerar análise agora" (aciona insight sem evento novo)

---

## Catálogo Completo de Insights

### Grupo 1 — Análise Tática
- 🎯 **Formação adversária vs. histórico**: "O Goiás está usando 4-2-3-1, diferente da sua formação predominante (4-3-3) na temporada. Isso sugere postura mais defensiva..."
- 🔄 **Impacto de substituição**: "A entrada de X no lugar de Y pelo Goiás indica transição para 3-5-2, o que expõe os flancos do Sport..."

### Grupo 2 — Situação de Jogo
- ⚠️ **Alerta pós-gol sofrido**: "Após o gol aos X minutos, o Sport precisa adaptar [área específica]. Com base nos últimos 7 jogos, a equipe tem dificuldade em reagir em menos de 10 minutos..."
- 🏆 **Manutenção de vantagem**: "Com o Sport vencendo por X a Y e considerando o padrão dos últimos 5 jogos do Goiás como mandante..."

### Grupo 3 — Gestão de Elenco
- 🔁 **Janela de substituição ideal**: "Baseado no padrão de Dal Pozzo na temporada (média de 1ª substituição aos 58'), a janela ideal para entrada de Clayson é entre 55'-65'..."
- 🟨 **Alerta disciplinar**: "Jogador X está com 1 cartão amarelo e jogou com intensidade alta. Em situações semelhantes na temporada, Dal Pozzo costuma preservá-lo após os 70'..."

### Grupo 4 — Estatística Contextual
- 📊 **Comparativo de desempenho**: "Em confrontos fora de casa contra times do G-10, o Sport marcou apenas 23% dos seus gols no 1º tempo..."
- 📈 **Tendência de gols**: "O Goiás marcou 71% dos seus gols em casa nos primeiros 20 minutos ou após os 65'..."

### Grupo 5 — Análise de Momento Crítico
- ⏱️ **Análise de intervalo**: Compilação completa do 1º tempo com métricas e 3 sugestões táticas para o 2º tempo
- 🎯 **Prognóstico dinâmico**: "Com base no placar atual e no padrão histórico deste confronto, a probabilidade de vitória do Sport é de X%..."

---

## Stack Tecnológica

| Componente | Tecnologia |
|---|---|
| **Linguagem** | Python 3.11+ |
| **Coleta temporada (histórico)** | `requests` + ESPN `site.api` + `sports.core.api` |
| **Monitor ao vivo** | `requests` + ESPN `site.api` (sem autenticação) |
| **IA generativa** | ✅ **Google Gemini Flash 2.0** (`google-generativeai`) |
| **Logos/assets** | TheSportsDB free API |
| **Dashboard** | Streamlit |
| **Armazenamento** | CSV + JSON local |
| **Dependências** | `pandas`, `requests`, `google-generativeai`, `streamlit` |

---

## Plano de Execução para Hoje (22/07/2026)

| Horário | Ação |
|---|---|
| **Agora (14h)** | Implementar `config.py` + `coleta_temporada.py` |
| **14h30** | Rodar `coleta_temporada.py` — gerar CSVs de Goiás e Sport |
| **16h** | Implementar + testar `analise_prejogo.py` |
| **17h** | Gerar e revisar `relatorio_prejogo.md` com a comissão |
| **18h** | Implementar `monitor_ao_vivo.py` + `insight_engine.py` |
| **19h30** | Testar sistema completo em modo simulado |
| **20h** | Ligar dashboard, iniciar monitoramento |
| **20h30** | ⚽ Partida começa — sistema ao vivo |

---

## Open Questions

> [!NOTE]
> ✅ **Modelo de IA:** Confirmado — **Google Gemini Flash 2.0** com a chave do usuário.

> [!NOTE]
> ✅ **API de dados:** Confirmado — **ESPN API** como fonte única (gratuita, sem chave). API-Football descartada (só até 2024). TheSportsDB apenas para logos.

> [!IMPORTANT]
> **Chave do Gemini:** Para iniciar a implementação, precisamos da sua `GEMINI_API_KEY`. Você pode fornecê-la diretamente ou configurar como variável de ambiente (`GEMINI_API_KEY=...`).

> [!IMPORTANT]
> **Dashboard ao vivo:** A comissão técnica verá o sistema em **tablet/laptop em campo** ou numa **TV/telão na sala de reunião?** Isso define se o dashboard precisa ser responsivo para mobile ou pode ser uma tela wide de desktop.

---

## Verification Plan

### Testes Automáticos
- `pytest` básico para validar que os endpoints respondem e retornam o formato esperado
- Teste de mock do loop ao vivo com um jogo já encerrado

### Validação Manual
- Confirmar que `goias_temporada.csv` e `sport_temporada.csv` têm todos os jogos de 2026
- Executar `analise_prejogo.py` e revisar o relatório gerado antes das 20h
- Simular um "gol" manual no estado do JSON e verificar que o insight é gerado corretamente
- Teste real nos primeiros minutos da partida (20h30)
