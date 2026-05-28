# Micro-Simulação Social com Agentes Generativos

Recriação simplificada da arquitetura do paper *Generative Agents: Interactive
Simulacra of Human Behavior* (Park et al., UIST 2023). Cinco agentes com
persona, memória, reflexão e planejamento convivem numa vila textual por 3 dias.

**Grupo G7** — Tópicos em Engenharia de Software · PUC-Campinas · 2026/1

---

## Sobre o Projeto

Cada agente tem persona detalhada, mantém um *memory stream* indexado por
recência, relevância e importância, gera reflexões periódicas e planeja
sua agenda diária. A simulação avalia duas métricas:

- **Consistência de persona** — quão alinhadas as ações de cada agente estão
  com sua bio (cosine similarity sobre embeddings, ou TF-IDF no modo mock).
- **Propagação de informação** — a partir de uma info-semente injetada na
  Helena ("vai ter uma feira de artesanato no sábado"), quantos agentes ficam
  sabendo ao longo dos 3 dias e quando.

## Arquitetura

```
Simulation
├── TimeManager (dias × horas)
├── Village (locais + ocupantes)
├── PropagationTracker (rastreia info-semente)
└── Agent ×5
    ├── persona (bio, traits, known_info)
    ├── MemoryStream — observation | reflection | plan | conversation
    │   retrieve = α·recência + β·relevância + γ·importância
    ├── ReflectionModule (insights de alto nível)
    ├── DailyPlanner (agenda 7h–21h)
    └── decide_interaction + converse
                │
                ▼
        LLMClient ─┬─ OpenAIClient  (modo llm)
                   └─ MockClient    (modo mock)
```

Diagrama detalhado em [docs/architecture.md](docs/architecture.md).

## Como Rodar

### Pré-requisitos

- Python 3.11+
- (Opcional) Chave de API OpenAI para o modo `llm`

### Instalação

```bash
git clone https://github.com/SEU-USUARIO/generative-agents-sim.git
cd generative-agents-sim
python3 -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env          # opcional; cole sua chave OpenAI
```

### Execução

```bash
# Modo demo (sem API key, respostas via templates)
python main.py --mode mock --verbose

# Modo com LLM real (requer OPENAI_API_KEY no .env)
python main.py --mode llm --verbose

# Rodar 1 dia só pra testar rápido
python main.py --mode mock --days 1
```

### Flags

| Flag        | Default     | Descrição                                       |
|-------------|-------------|-------------------------------------------------|
| `--mode`    | `mock`      | `mock` (templates) ou `llm` (chamadas OpenAI)   |
| `--days`    | `3`         | Quantos dias virtuais simular                   |
| `--output`  | `output/`   | Pasta de saída para os logs                     |
| `--verbose` | `False`     | Imprime cada hora simulada no terminal          |

## Saídas

Ao rodar, três arquivos são gerados em `output/`:

- `simulation_log.json` — log completo (conversas, reflexões, propagação)
- `conversations.md` — todas as conversas geradas, em markdown legível
- `summary.md` — resumo com métricas e timeline de propagação

E no terminal, ao final:

```
📊 AVALIAÇÃO
--- Consistência de persona ---
   Helena: similaridade média = 0.39 (n=30, método=embeddings)
   ...
--- Propagação de informação ---
   Taxa final: 100% (5/5)
   Timeline:
      Helena — Dia 1, 07h
      Camila — Dia 1, 10h
      ...
```

## Estrutura do Repositório

```
.
├── main.py                 # entry point + argparse
├── config/
│   ├── personas.py         # 5 personas (Helena, Roberto, Camila, Marcos, Júlia)
│   └── settings.py         # constantes (locais, dias, seed info)
├── src/
│   ├── agent.py            # classe Agent
│   ├── memory.py           # MemoryStream + recuperação 3-fatores
│   ├── reflection.py       # módulo de reflexão
│   ├── planner.py          # planejador diário
│   ├── environment.py      # Village + TimeManager
│   ├── simulation.py       # loop principal
│   └── llm.py              # OpenAIClient + MockClient
├── evaluation/
│   ├── consistency.py      # cosine/TF-IDF persona × ações
│   └── propagation.py      # rastreamento da info-semente
├── output/                 # logs gerados (gitignored exceto .gitkeep)
└── docs/
    └── architecture.md     # diagrama textual da arquitetura
```

## Métricas de Avaliação

- **Consistência de persona** — para cada agente, comparamos sua bio com cada
  ação/observação/reflexão registrada. No modo `llm` usamos embeddings
  (`text-embedding-3-small`) + cosine similarity. No modo `mock` o proxy é
  TF-IDF (scikit-learn).
- **Propagação de informação** — uma frase ("vai ter uma feira de artesanato no
  próximo sábado") é injetada apenas na Helena no início do Dia 1. A cada
  conversa, checamos se as keywords da semente aparecem e se um participante
  já informado conversou com um não-informado. Rastreamos quem soube quando.

## Equipe

| Integrante       | Responsabilidade                                    |
|------------------|-----------------------------------------------------|
| Pedro Rocha      | Desenvolvimento central, arquitetura, integração    |
| Victor Accorsi   | Documentação, README, relatórios                    |
| Luiza Pedroso    | Pesquisa, personas, módulo de reflexão              |
| Breno Figueira   | Módulo de ambiente, simulação                       |
| Milena Capelli   | Pipeline de avaliação, métricas, propagação         |

## Referências

1. Park, J. S., O'Brien, J., Cai, C. J., Morris, M. R., Liang, P., & Bernstein,
   M. S. (2023). *Generative Agents: Interactive Simulacra of Human Behavior*.
   UIST '23.
2. Wang, L., Ma, C., Feng, X., et al. (2024). *A Survey on Large Language
   Model based Autonomous Agents*. Frontiers of Computer Science.
3. Xi, Z., Chen, W., Guo, X., et al. (2023). *The Rise and Potential of Large
   Language Model Based Agents: A Survey*. arXiv:2309.07864.
4. Sumers, T. R., Yao, S., Narasimhan, K., & Griffiths, T. L. (2023).
   *Cognitive Architectures for Language Agents*. TMLR.
5. Shao, Y., Li, L., Dai, J., & Qiu, X. (2023). *Character-LLM: A Trainable
   Agent for Role-Playing*. EMNLP '23.
6. OpenAI (2024). *GPT-4o-mini Technical Report*. https://openai.com/research/
7. Tan, F., Wang, Y., Zheng, R., et al. (2023). *Multi-Agent Collaboration:
   Harnessing the Power of Intelligent LLM Agents*. arXiv:2306.03314.
8. Andreas, J. (2022). *Language Models as Agent Models*. EMNLP Findings.
