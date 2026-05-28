"""Loop principal da simulação."""

from __future__ import annotations

import json
import os

from config.personas import PERSONAS
from config.settings import HOURS_PER_DAY, NUM_DAYS, SEED_AGENT, SEED_INFO
from evaluation.consistency import ConsistencyEvaluator
from evaluation.propagation import PropagationTracker
from src.agent import Agent
from src.environment import TimeManager, Village
from src.llm import LLMClient, MockClient, OpenAIClient
from src.memory import MemoryEntry


class Simulation:
    def __init__(
        self,
        mode: str = "mock",
        num_days: int | None = None,
        verbose: bool = False,
    ):
        self.mode = mode
        self.num_days = num_days or NUM_DAYS
        self.verbose = verbose
        self.llm: LLMClient = MockClient() if mode == "mock" else OpenAIClient()
        self.village = Village()
        self.time = TimeManager(num_days=self.num_days)
        self.agents: dict[str, Agent] = {}
        self.log: list[dict] = []
        self.propagation_tracker = PropagationTracker(SEED_INFO, SEED_AGENT)
        self.consistency_evaluator = ConsistencyEvaluator(self.llm)

    # ---- setup ---------------------------------------------------------

    def setup(self) -> None:
        for persona in PERSONAS:
            agent = Agent(persona, self.llm)
            self.agents[agent.name] = agent
            self.village.place_agent(agent.name, agent.location)
            self._log(f"  + {agent.name} colocada em {agent.location}")

        if SEED_AGENT in self.agents:
            seed_agent = self.agents[SEED_AGENT]
            seed_agent.known_info.add(SEED_INFO)
            obs = f"Eu soube hoje: {SEED_INFO}"
            seed_agent.memory.add(
                MemoryEntry(
                    text=obs,
                    timestamp=(1, 7),
                    importance=7.0,
                    embedding=self.llm.embed(obs),
                    entry_type="observation",
                )
            )
            self._log(f"  >> info-semente plantada na {SEED_AGENT}: \"{SEED_INFO}\"")

    # ---- loop principal -----------------------------------------------

    def run(self) -> None:
        # Plano do Dia 1
        self._log("\n--- Planejando Dia 1 ---")
        for agent in self.agents.values():
            agent.start_day(1, self.village.list_locations())

        while True:
            day, hour = self.time.current_time()
            self._log(f"\n=== Dia {day}, {hour:02d}h ===")

            # 1. Mover agentes para o local planejado
            for agent in self.agents.values():
                planned = agent.get_planned_location(hour)
                if planned not in self.village.locations:
                    continue
                self.village.move_agent(agent.name, planned)
                agent.location = planned

            # 2. Interações por local
            for loc_name in list(self.village.locations.keys()):
                names = self.village.get_agents_at(loc_name)
                if len(names) < 2:
                    continue
                a_name, b_name = names[0], names[1]
                agent_a = self.agents[a_name]
                agent_b = self.agents[b_name]

                decision = agent_a.decide_interaction(
                    [agent_b], loc_name, (day, hour)
                )
                if not decision:
                    continue
                _, topic = decision
                turns = agent_a.converse(agent_b, topic, (day, hour))
                if not turns:
                    continue

                self._log(f"[{loc_name}] {a_name} ↔ {b_name} — tópico: {topic}")
                for t in turns:
                    self._log(f"    {t['speaker']}: {t['text']}")

                newly = self.propagation_tracker.check_conversation(
                    turns, [a_name, b_name], (day, hour)
                )
                for name in newly:
                    self.agents[name].known_info.add(SEED_INFO)
                    self._log(f"    >> {name} ficou sabendo da feira!")

                self.log.append(
                    {
                        "type": "conversation",
                        "time": [day, hour],
                        "location": loc_name,
                        "participants": [a_name, b_name],
                        "topic": topic,
                        "turns": turns,
                        "propagation_event": newly,
                    }
                )

            # 3. Observações de cada agente
            for agent in self.agents.values():
                loc = self.village.get_location_of(agent.name) or agent.location
                others = [n for n in self.village.get_agents_at(loc) if n != agent.name]
                activity = agent.get_planned_activity(hour)
                if others:
                    obs = f"Estive em {loc} fazendo: {activity}. Estavam aqui: {', '.join(others)}."
                else:
                    obs = f"Estive em {loc} sozinho(a) fazendo: {activity}."
                agent.observe(obs, (day, hour))

            # 4. Reflexão (se devido)
            for agent in self.agents.values():
                insights = agent.maybe_reflect((day, hour))
                if insights:
                    self._log(f"[REFLEXÃO] {agent.name}:")
                    for ins in insights:
                        self._log(f"    - {ins}")
                    self.log.append(
                        {
                            "type": "reflection",
                            "time": [day, hour],
                            "agent": agent.name,
                            "insights": insights,
                        }
                    )

            # 5. Avança tempo
            advanced = self.time.advance()
            if not advanced:
                break

            # 6. Novo dia → replanejar
            if self.time.is_new_day():
                new_day = self.time.day
                self._log(f"\n--- Planejando Dia {new_day} ---")
                for agent in self.agents.values():
                    agent.start_day(new_day, self.village.list_locations())

    # ---- output --------------------------------------------------------

    def save_results(self, output_dir: str = "output") -> None:
        os.makedirs(output_dir, exist_ok=True)

        # JSON log completo
        with open(
            os.path.join(output_dir, "simulation_log.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "mode": self.mode,
                    "num_days": self.num_days,
                    "log": self.log,
                    "propagation": {
                        "seed_info": self.propagation_tracker.seed_info,
                        "informed_agents": {
                            a: list(t)
                            for a, t in self.propagation_tracker.informed_agents.items()
                        },
                        "timeline": self.propagation_tracker.get_propagation_timeline(),
                        "rate": self.propagation_tracker.get_propagation_rate(len(self.agents)),
                    },
                },
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        # Markdown das conversas
        convs = [l for l in self.log if l["type"] == "conversation"]
        with open(
            os.path.join(output_dir, "conversations.md"), "w", encoding="utf-8"
        ) as f:
            f.write("# Conversas da Vila\n\n")
            f.write(f"Modo: `{self.mode}` · Dias: {self.num_days}\n\n")
            for c in convs:
                day, hour = c["time"]
                f.write(f"## Dia {day}, {hour:02d}h — em {c['location']}\n")
                f.write(f"**Tópico:** {c['topic']}\n\n")
                for t in c["turns"]:
                    f.write(f"- **{t['speaker']}:** {t['text']}\n")
                if c.get("propagation_event"):
                    f.write(
                        f"\n> Info-semente se propagou para: "
                        f"{', '.join(c['propagation_event'])}\n"
                    )
                f.write("\n")

        # Summary
        rate = self.propagation_tracker.get_propagation_rate(len(self.agents))
        n_inf = len(self.propagation_tracker.informed_agents)
        with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as f:
            f.write("# Resumo da Simulação\n\n")
            f.write(f"- **Modo:** `{self.mode}`\n")
            f.write(f"- **Agentes:** {len(self.agents)}\n")
            f.write(f"- **Dias simulados:** {self.num_days}\n")
            f.write(f"- **Horas por dia:** {len(HOURS_PER_DAY)} ({HOURS_PER_DAY[0]}h–{HOURS_PER_DAY[-1]}h)\n")
            f.write(f"- **Conversas geradas:** {len(convs)}\n")
            f.write(
                f"- **Reflexões geradas:** "
                f"{sum(1 for l in self.log if l['type'] == 'reflection')}\n\n"
            )
            f.write("## Propagação da info-semente\n\n")
            f.write(f"> {self.propagation_tracker.seed_info}\n\n")
            f.write(f"**Taxa final:** {rate*100:.0f}% ({n_inf}/{len(self.agents)})\n\n")
            f.write("### Quem soube quando\n\n")
            for event in self.propagation_tracker.get_propagation_timeline():
                day, hour = event["time"]
                f.write(f"- **{event['agent']}** — Dia {day}, {hour:02d}h\n")

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)
