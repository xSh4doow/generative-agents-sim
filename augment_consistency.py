"""Avaliação de consistência relativa (own-vs-cross) a partir do log salvo.

Motivação: o cosine similarity absoluto entre a bio e uma ação individual no
`text-embedding-3-small` vive num intervalo comprimido (~0.3–0.5 para textos
relacionados-mas-distintos). Um limiar fixo de 0.70 não faz sentido nesse espaço.

A medida cientificamente honesta é *relativa*: cada agente deveria ser mais
similar à PRÓPRIA persona do que às persona dos OUTROS. Se own > cross de forma
consistente, as personas são distinguíveis e os agentes se mantêm coerentes.

Este script só faz chamadas de *embedding* (baratíssimas) sobre texto que já
foi salvo em output/simulation_log.json — não re-roda a simulação completa.

Atualiza:
  - output/metrics.json          (consistency vira {own, cross, delta} por agente)
  - output/consistency_chart.png (barras agrupadas: própria persona × outras)
"""

from __future__ import annotations

import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config.personas import PERSONAS
from src.llm import OpenAIClient

AZUL_ESCURO = "#0F3460"
AZUL_MEDIO = "#2E75B6"
CINZA = "#A9B7C9"
LOG_PATH = "output/simulation_log.json"
METRICS_PATH = "output/metrics.json"
CHART_PATH = "output/consistency_chart.png"


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def build_agent_texts(log: list[dict]) -> dict[str, list[str]]:
    """Texto de cada agente: falas (turnos onde é speaker) + insights de reflexão."""
    texts: dict[str, list[str]] = {p["name"]: [] for p in PERSONAS}
    for entry in log:
        if entry["type"] == "conversation":
            for t in entry["turns"]:
                sp = t.get("speaker")
                if sp in texts:
                    texts[sp].append(t.get("text", ""))
        elif entry["type"] == "reflection":
            ag = entry.get("agent")
            if ag in texts:
                texts[ag].extend(entry.get("insights", []))
    # remove vazios e limita pra não explodir embeddings
    return {k: [x for x in v if x.strip()][:30] for k, v in texts.items()}


def main() -> int:
    if not os.path.exists(LOG_PATH):
        print(f"[ERRO] {LOG_PATH} não encontrado. Rode run_evaluation.py --mode llm antes.")
        return 1

    with open(LOG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    log = data["log"]

    bios = {p["name"]: p["bio"] for p in PERSONAS}
    agent_texts = build_agent_texts(log)

    print("Gerando embeddings (somente texto já salvo)...")
    llm = OpenAIClient()

    # embeddings das bios
    bio_emb = {name: llm.embed(bio) for name, bio in bios.items()}
    if any(v is None for v in bio_emb.values()):
        print("[ERRO] embeddings indisponíveis (sem API key?). Abortando.")
        return 1

    # embeddings das ações (cache por texto)
    cache: dict[str, list[float]] = {}
    for texts in agent_texts.values():
        for t in texts:
            if t not in cache:
                cache[t] = llm.embed(t)

    names = [p["name"] for p in PERSONAS]
    own_scores: dict[str, float] = {}
    cross_scores: dict[str, float] = {}

    for name in names:
        be = bio_emb[name]
        own = [cosine(be, cache[t]) for t in agent_texts[name] if cache.get(t)]
        cross = [
            cosine(be, cache[t])
            for other in names if other != name
            for t in agent_texts[other] if cache.get(t)
        ]
        own_scores[name] = float(np.mean(own)) if own else 0.0
        cross_scores[name] = float(np.mean(cross)) if cross else 0.0

    # ---- atualiza metrics.json ----
    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics = json.load(f)

    metrics["consistency"] = {
        name: {
            "own": round(own_scores[name], 4),
            "cross": round(cross_scores[name], 4),
            "delta": round(own_scores[name] - cross_scores[name], 4),
        }
        for name in names
    }
    metrics["consistency_method"] = {
        "embedding_model": "text-embedding-3-small",
        "measure": "cosine(bio, ação) — média sobre falas e reflexões do agente",
        "interpretation": (
            "Comparação relativa: 'own' = similaridade com a própria persona; "
            "'cross' = média de similaridade com as personas dos outros agentes. "
            "own > cross indica que a persona se mantém distinguível e consistente."
        ),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # ---- regenera o gráfico (barras agrupadas) ----
    own = [own_scores[n] for n in names]
    cross = [cross_scores[n] for n in names]
    y = np.arange(len(names))
    h = 0.36

    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    ax.barh(y + h / 2, own, height=h, color=AZUL_MEDIO, label="Própria persona", zorder=3)
    ax.barh(y - h / 2, cross, height=h, color=CINZA, label="Outras personas (média)", zorder=3)

    for i, (o, c) in enumerate(zip(own, cross)):
        ax.text(o + 0.006, i + h / 2, f"{o:.2f}", va="center", fontsize=9.5, color=AZUL_ESCURO)
        ax.text(c + 0.006, i - h / 2, f"{c:.2f}", va="center", fontsize=9.5, color="#5a6675")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlim(0, max(own + cross) * 1.16)
    ax.set_xlabel("Cosine similarity (text-embedding-3-small)", fontsize=11.5)
    ax.set_title(
        "Consistência de Persona — própria vs. outras",
        fontsize=14, fontweight="bold", color=AZUL_ESCURO, pad=12,
    )
    ax.legend(
        fontsize=10.5, loc="upper center", bbox_to_anchor=(0.5, -0.13),
        ncol=2, frameon=False,
    )
    ax.grid(axis="x", linestyle=":", alpha=0.5, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(CHART_PATH, dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- resumo ----
    print("\n" + "=" * 56)
    print("CONSISTÊNCIA RELATIVA (own vs cross)")
    print("=" * 56)
    for name in names:
        o, c = own_scores[name], cross_scores[name]
        flag = "✓" if o > c else "✗"
        print(f"  {flag} {name:>8}: própria={o:.3f}  outras={c:.3f}  Δ={o-c:+.3f}")
    mo = np.mean(own)
    mc = np.mean(cross)
    print(f"\n  média: própria={mo:.3f}  outras={mc:.3f}  Δ={mo-mc:+.3f}")
    consistent = sum(1 for n in names if own_scores[n] > cross_scores[n])
    print(f"  {consistent}/{len(names)} agentes mais próximos da própria persona")
    print(f"\n✅ Atualizado: {METRICS_PATH} e {CHART_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
