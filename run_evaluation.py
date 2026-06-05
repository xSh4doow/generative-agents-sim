"""Script de avaliação do Checkpoint 3.

Roda a simulação UMA vez, salva os logs padrão e em cima dela computa:
  1. ConsistencyEvaluator por agente (cosine similarity bio↔ações)
  2. Timeline de propagação da info-semente (quem soube de quem, e quando)

Saídas:
  - output/simulation_log.json   (via Simulation.save_results)
  - output/conversations.md      (idem)
  - output/summary.md            (idem)
  - output/metrics.json          (dados brutos da avaliação)
  - output/consistency_chart.png (barras horizontais: similarity por agente)
  - output/propagation_chart.png (step function: agentes informados no tempo)

Uso:
    python run_evaluation.py --mode mock
    python run_evaluation.py --mode llm --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")  # backend sem display (WSL/headless)
import matplotlib.pyplot as plt

from config.settings import HOURS_PER_DAY, SEED_AGENT, SEED_INFO
from src.simulation import Simulation

# Paleta do poster (mantém consistência visual com o A1)
AZUL_ESCURO = "#0F3460"
AZUL_MEDIO = "#2E75B6"
VERMELHO = "#E74C3C"
THRESHOLD = 0.70


# --------------------------------------------------------------------------- #
# Coleta de métricas
# --------------------------------------------------------------------------- #
def collect_consistency(sim: Simulation) -> dict[str, float]:
    """Roda o ConsistencyEvaluator em cada agente vivo da simulação."""
    out: dict[str, float] = {}
    for name, agent in sim.agents.items():
        result = sim.consistency_evaluator.evaluate(agent)
        out[name] = round(float(result["mean_similarity"]), 4)
    return out


def collect_propagation(sim: Simulation) -> dict:
    """Reconstrói a timeline de propagação com a fonte (de quem cada um soube).

    O PropagationTracker guarda quando cada agente soube, mas não de quem.
    Aqui reproduzimos o log de conversas em ordem cronológica: quando alguém
    fica sabendo numa conversa, a fonte é o participante que já sabia.
    """
    tracker = sim.propagation_tracker
    total = len(sim.agents)

    # ordena conversas cronologicamente
    convs = sorted(
        (l for l in sim.log if l["type"] == "conversation"),
        key=lambda c: (c["time"][0], c["time"][1]),
    )

    source_of: dict[str, str] = {SEED_AGENT: "initial"}
    known: set[str] = {SEED_AGENT}
    for c in convs:
        newly = c.get("propagation_event") or []
        if not newly:
            continue
        participants = c.get("participants", [])
        src = next((p for p in participants if p in known), None) or SEED_AGENT
        for name in newly:
            if name not in source_of:
                source_of[name] = src
            known.add(name)

    timeline = []
    for event in tracker.get_propagation_timeline():
        day, hour = event["time"]
        agent = event["agent"]
        timeline.append(
            {
                "agent": agent,
                "day": day,
                "hour": hour,
                "source": source_of.get(agent, "initial" if agent == SEED_AGENT else "?"),
            }
        )

    return {
        "seed_info": tracker.seed_info,
        "seed_agent": SEED_AGENT,
        "timeline": timeline,
        "propagation_rate": round(tracker.get_propagation_rate(total), 4),
        "total_agents": total,
        "informed_agents": len(tracker.informed_agents),
        "total_days": sim.num_days,
    }


def collect_stats(sim: Simulation) -> dict:
    convs = sum(1 for l in sim.log if l["type"] == "conversation")
    refls = sum(1 for l in sim.log if l["type"] == "reflection")
    obs = sum(
        1
        for agent in sim.agents.values()
        for e in agent.memory.entries
        if e.entry_type == "observation"
    )
    return {
        "total_days": sim.num_days,
        "total_conversations": convs,
        "total_reflections": refls,
        "total_observations": obs,
    }


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def chart_consistency(consistency: dict[str, float], path: str) -> None:
    names = list(consistency.keys())
    values = [consistency[n] for n in names]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    y = range(len(names))
    colors = [AZUL_MEDIO if v >= THRESHOLD else "#9FB6CF" for v in values]
    ax.barh(list(y), values, color=colors, height=0.62, zorder=3)

    for i, v in enumerate(values):
        ax.text(v + 0.012, i, f"{v:.2f}", va="center", fontsize=11, color=AZUL_ESCURO)

    ax.axvline(THRESHOLD, color=VERMELHO, linestyle="--", linewidth=1.6, zorder=2)
    ax.text(
        THRESHOLD + 0.005, len(names) - 0.4, "limiar 0.70",
        color=VERMELHO, fontsize=10, rotation=90, va="top",
    )

    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Cosine similarity (bio ↔ ações)", fontsize=12)
    ax.set_title(
        "Consistência de Persona (Cosine Similarity)",
        fontsize=14, fontweight="bold", color=AZUL_ESCURO, pad=12,
    )
    ax.grid(axis="x", linestyle=":", alpha=0.5, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def chart_propagation(propagation: dict, path: str) -> None:
    timeline = propagation["timeline"]
    total = propagation["total_agents"]

    # eixo x = horas absolutas desde o início (dia 1, 7h = 0)
    hours_per_day = len(HOURS_PER_DAY)
    base = HOURS_PER_DAY[0]

    def abs_hour(day: int, hour: int) -> int:
        return (day - 1) * hours_per_day + (hour - base)

    xs = [abs_hour(e["day"], e["hour"]) for e in timeline]
    ys = list(range(1, len(timeline) + 1))

    # estende a linha até o fim da simulação pra mostrar o platô
    days = propagation.get("total_days") or max(e["day"] for e in timeline)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)

    step_x = [0] + xs + [days * hours_per_day - 1]
    step_y = [0] + ys + [ys[-1]]
    ax.step(step_x, step_y, where="post", color=AZUL_ESCURO, linewidth=2.2, zorder=2)
    ax.scatter(xs, ys, color=VERMELHO, s=70, zorder=4)

    for e, x, yv in zip(timeline, xs, ys):
        ax.annotate(
            e["agent"], (x, yv), textcoords="offset points",
            xytext=(8, -2), fontsize=11, color=AZUL_ESCURO, fontweight="bold",
        )

    # marcadores de início de dia
    day_ticks, day_labels = [], []
    for d in range(1, days + 1):
        tick = (d - 1) * hours_per_day
        day_ticks.append(tick)
        day_labels.append(f"Dia {d}\n{base}h")
        if d > 1:
            ax.axvline(tick, color="#CCCCCC", linestyle=":", linewidth=1, zorder=0)

    ax.set_xticks(day_ticks)
    ax.set_xticklabels(day_labels, fontsize=10)
    ax.set_ylim(0, total + 0.5)
    ax.set_yticks(range(0, total + 1))
    ax.set_ylabel("Agentes informados", fontsize=12)
    ax.set_xlabel("Tempo de simulação", fontsize=12)
    ax.set_title(
        "Propagação da Informação-Semente",
        fontsize=14, fontweight="bold", color=AZUL_ESCURO, pad=12,
    )
    ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="Avaliação da micro-simulação")
    parser.add_argument("--mode", choices=["mock", "llm"], default="mock")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--output", default="output")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print(f"🏘️  Rodando simulação ({args.mode}) para avaliação...")
    try:
        sim = Simulation(mode=args.mode, num_days=args.days, verbose=args.verbose)
    except RuntimeError as e:
        print(f"\n[ERRO] {e}")
        return 1

    sim.setup()
    sim.run()
    sim.save_results(args.output)

    os.makedirs(args.output, exist_ok=True)

    print("\n📊 Coletando métricas...")
    consistency = collect_consistency(sim)
    propagation = collect_propagation(sim)
    stats = collect_stats(sim)

    metrics = {
        "mode": args.mode,
        "consistency": consistency,
        "propagation": propagation,
        "simulation_stats": stats,
    }

    metrics_path = os.path.join(args.output, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    cons_png = os.path.join(args.output, "consistency_chart.png")
    prop_png = os.path.join(args.output, "propagation_chart.png")
    chart_consistency(consistency, cons_png)
    chart_propagation(propagation, prop_png)

    # ---- resumo no terminal ----
    print("\n" + "=" * 56)
    print("RESUMO DA AVALIAÇÃO")
    print("=" * 56)
    print("\nConsistência de persona (cosine similarity):")
    for name, v in consistency.items():
        flag = "✅" if v >= THRESHOLD else "⚠️ "
        print(f"  {flag} {name:>8}: {v:.3f}")
    mean = sum(consistency.values()) / len(consistency) if consistency else 0.0
    print(f"     {'média':>8}: {mean:.3f}")

    print(f"\nPropagação da info-semente: \"{SEED_INFO}\"")
    print(
        f"  taxa: {propagation['propagation_rate']*100:.0f}% "
        f"({propagation['informed_agents']}/{propagation['total_agents']})"
    )
    for e in propagation["timeline"]:
        via = "" if e["source"] == "initial" else f"  ← {e['source']}"
        print(f"    Dia {e['day']}, {e['hour']:02d}h  {e['agent']:>8}{via}")

    print(f"\nStats: {stats}")
    print(f"\n✅ Arquivos gerados em {args.output}/:")
    for p in (metrics_path, cons_png, prop_png):
        print(f"   - {p}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
