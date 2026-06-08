# Design — Entrega Final G7 (Generative Agents)

Data: 2026-06-07 · Apresentação: 11/Jun/2026 · Status: aprovado pelo Pedro

## Escopo

Redesign do poster A1 + criação do one-pager A4 frente/verso, mais entregáveis
burocráticos exigidos pelo plano do trabalho (referencias.md ABNT, pasta
painel/, push).

## Decisões

- **Redesign completo** do poster (não só polish) + one-pager na mesma direção
- **3 direções visuais** geradas como demos-snippet pelo fluxo Huashu; Pedro escolhe:
  1. Editorial Científico (minimal, quase P&B + 1 accent)
  2. Swiss Info-Design (grid modular, dados protagonistas)
  3. Dark Tech / Terminal (fundo #0f0f0f, monospace, estética de log)
- **100% diagramas** — sem ilustração gerada (Higgsfield descartado)
- Referências: montadas do zero, 8 itens em ABNT
- Conteúdo do poster atual é a fonte; diagramas redesenhados em SVG

## Restrições fixas (plano do professor)

- Fonte ≥24pt corpo, ≥14pt referências/legendas (físico no A1)
- ≤40% texto corrido
- Identidade PUC-Campinas no cabeçalho
- QR code → repo GitHub (obrigatório)
- Template 6 blocos em ordem fixa: Contexto, Conceitos, Estado da Arte,
  Arquitetura, Experimento/Demo, Discussão + Referências
- A1 retrato 594×841mm + 3mm sangria

## Artefatos

| Artefato | Formato |
|---|---|
| `painel/poster_a1.pdf` | A1 retrato, HTML mm-units → Chrome headless |
| `painel/onepager_a4.pdf` | A4, 2 páginas (frente/verso) |
| `referencias.md` | ABNT, 8 refs |
| README atualizado | aponta referencias.md e painel/ |

## Quality gate

Playwright screenshots → audit 5 dimensões → correção → PDF final.
Legibilidade A1: corpo ≥24pt físico (~9px/mm no HTML).

## Sequência

1. 3 direções → escolha do Pedro (gate)
2. Poster A1 completo → review → PDF
3. One-pager A4 → review → PDF
4. referencias.md + rename poster/→painel/ + README + commit logs + push

## Decisão de direção visual (2026-06-07)
**Swiss Info-Design** (grid modular, Archivo, vermelho #E63312, numeração gigante) **incorporando elementos Dark Tech/Terminal**: blocos de log como janelas de terminal escuras (#0F0F0F), labels em JetBrains Mono, statusbar de simulação. Aprovado pelo Pedro em 07/Jun.
