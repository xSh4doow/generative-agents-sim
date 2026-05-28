"""Entry point da Micro-Simulação Social com Agentes Generativos.

Uso:
    python main.py --mode mock --verbose
    python main.py --mode llm --verbose
    python main.py --mode mock --days 1 --output output/

Flags:
    --mode {mock,llm}   mock: templates sem API. llm: OpenAI gpt-4o-mini.
    --days N            número de dias (default: 3)
    --output DIR        diretório de saída (default: output/)
    --verbose           printa tudo no terminal
"""

from __future__ import annotations

import argparse
import sys

from src.simulation import Simulation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Micro-Simulação Social com Agentes Generativos"
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "llm"],
        default="mock",
        help="mock: sem API key. llm: chamadas reais à OpenAI.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Número de dias (default: 3 do settings).",
    )
    parser.add_argument(
        "--output", default="output", help="Diretório de saída."
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print detalhado no terminal."
    )
    args = parser.parse_args()

    print(f"🏘️  Iniciando simulação no modo: {args.mode}")
    if args.mode == "llm":
        print("    (chamadas reais à OpenAI — pode ser lento)")

    try:
        sim = Simulation(mode=args.mode, num_days=args.days, verbose=args.verbose)
    except RuntimeError as e:
        print(f"\n[ERRO] {e}")
        return 1

    sim.setup()
    sim.run()

    print("\n" + "=" * 60)
    print("📊 AVALIAÇÃO")
    print("=" * 60)

    print("\n--- Consistência de persona ---")
    consistency_results = []
    for name, agent in sim.agents.items():
        result = sim.consistency_evaluator.evaluate(agent)
        consistency_results.append(result)
        print(
            f"  {name:>8}: similaridade média = {result['mean_similarity']:.3f} "
            f"(n={result['n']}, método={result['method']})"
        )

    if consistency_results:
        overall = sum(r["mean_similarity"] for r in consistency_results) / len(
            consistency_results
        )
        print(f"  {'Média geral':>8}: {overall:.3f}")

    print("\n--- Propagação de informação ---")
    rate = sim.propagation_tracker.get_propagation_rate(len(sim.agents))
    n_inf = len(sim.propagation_tracker.informed_agents)
    print(f"  Info-semente: \"{sim.propagation_tracker.seed_info}\"")
    print(f"  Taxa final: {rate*100:.0f}% ({n_inf}/{len(sim.agents)})")
    print("  Timeline:")
    for event in sim.propagation_tracker.get_propagation_timeline():
        day, hour = event["time"]
        via = event.get("via", "")
        suffix = f" [{via}]" if via else ""
        print(f"    {event['agent']:>8} — Dia {day}, {hour:02d}h{suffix}")

    sim.save_results(args.output)
    print(f"\n✅ Resultados salvos em {args.output}/")
    print(f"   - {args.output}/simulation_log.json")
    print(f"   - {args.output}/conversations.md")
    print(f"   - {args.output}/summary.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
