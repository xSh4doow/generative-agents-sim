# Arquitetura — Micro-Simulação Social

## Visão geral

A arquitetura segue, em escala reduzida, a do paper *Generative Agents: Interactive
Simulacra of Human Behavior* (Park et al., UIST 2023). Cada agente é uma entidade
autônoma com persona, memória de longo prazo, capacidade de refletir sobre
experiências e planejar o próprio dia.

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Simulation                                │
│   (loop principal: tempo discreto, dias × horas)                     │
│                                                                      │
│  ┌───────────┐   ┌────────────┐   ┌────────────────────────┐         │
│  │ TimeMgr   │   │  Village   │   │ PropagationTracker     │         │
│  │ day, hour │   │ locations  │   │ (rastreia info-semente)│         │
│  └───────────┘   └────────────┘   └────────────────────────┘         │
│                                                                      │
│  ┌─────────────────────────── Agent ─────────────────────────────┐   │
│  │                                                               │   │
│  │  persona (name, bio, traits, known_info)                      │   │
│  │     │                                                         │   │
│  │     ├── MemoryStream  ── observation | reflection | plan |    │   │
│  │     │   (retrieve)        conversation                        │   │
│  │     │   recência + relevância + importância                   │   │
│  │     │                                                         │   │
│  │     ├── ReflectionModule  ── insights de alto nível           │   │
│  │     │                                                         │   │
│  │     ├── DailyPlanner      ── plano horário 7h–21h             │   │
│  │     │                                                         │   │
│  │     └── decide_interaction + converse                         │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                            │                                         │
│                            ▼                                         │
│                    ┌───────────────┐                                 │
│                    │   LLMClient   │   (interface única)             │
│                    │ ┌───────────┐ │                                 │
│                    │ │ OpenAI    │ │   modo --mode llm               │
│                    │ │ Mock      │ │   modo --mode mock              │
│                    │ └───────────┘ │                                 │
│                    └───────────────┘                                 │
└──────────────────────────────────────────────────────────────────────┘

         ┌──────── Evaluation (rodada ao final) ────────┐
         │  ConsistencyEvaluator (bio × ações)          │
         │  PropagationTracker.rate (% que ficou ciente)│
         └──────────────────────────────────────────────┘
```

## Fluxo por hora simulada

1. **Mover** — cada agente vai pro local previsto no plano diário.
2. **Interagir** — para cada local com 2+ agentes, um decide se conversa.
   Se sim, gera diálogo de 4 turnos via LLM. Ambos memorizam a conversa.
3. **Propagar** — se a conversa cita a info-semente e um dos participantes já
   sabia, o outro passa a saber também.
4. **Observar** — todos registram onde estiveram e com quem.
5. **Refletir** — se acumulou importância > 50 ou ≥ 8 observações desde a última
   reflexão, o agente sintetiza 3 insights e os guarda como memória de alta
   importância.

No início de cada dia, todos replanjam.

## Memória — recuperação por 3 fatores

```
score(memory, query) = α·recency + β·relevance + γ·importance

  recency    = 0.5 ^ (Δhours / half_life)        # decay exponencial
  relevance  = cos(emb(query), emb(memory))      # 0 no modo mock
  importance = memory.importance / 10            # normalizado
```

No modo `mock`, sem embeddings, o score recai sobre recência + importância.
Para a avaliação de consistência, o fallback é TF-IDF (scikit-learn).

## Decisões de design simplificadoras vs. paper

- **Tempo discreto** por hora cheia (paper usa minutos / segundos).
- **Sem mapa 2D** — locais são nodos com lista de ocupantes.
- **Interações 1-a-1** por local — pega o primeiro par; outros aguardam a hora
  seguinte.
- **Reflexões limitadas a 3 insights** por gatilho (paper deriva árvore inteira).
- **Sem perception system separado** — observação direta do estado da Village.

Essas escolhas mantêm a estrutura central do paper (Memory Stream, Reflection,
Planning, Interaction) num escopo possível de implementar e demonstrar em poucas
horas.
