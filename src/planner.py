"""Planejador diário.

Antes de cada dia, o agente gera um plano horário (7h–21h) baseado em quem ele
é e nas memórias recentes mais relevantes.
"""

from __future__ import annotations

import re

from src.llm import LLMClient


class DailyPlanner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan_day(
        self,
        agent_name: str,
        agent_bio: str,
        day: int,
        recent_memories: list[str],
        available_locations: list[str],
        home: str | None = None,
    ) -> list[dict]:
        mem_block = (
            "\n".join(f"- {m}" for m in recent_memories)
            if recent_memories
            else "- (sem memórias relevantes ainda)"
        )
        home_block = f"\nSua casa é: {home}\n" if home else "\n"

        system = (
            "Você é um planejador de rotinas. Gera planos realistas para o dia "
            "do agente, fiéis à personalidade dele."
        )
        user = (
            f"Você é {agent_name}. {agent_bio}{home_block}\n"
            f"Hoje é o dia {day} na vila. Suas memórias recentes mais relevantes:\n"
            f"{mem_block}\n\n"
            f"Locais disponíveis: {', '.join(available_locations)}\n\n"
            "Crie um plano para o seu dia de hoje (7h às 21h), com atividades "
            "realistas para quem você é. Formato por linha:\n"
            "HH:00 | local | atividade breve\n\n"
            "Exemplo:\n"
            "07:00 | casa_helena | Acordar e preparar café\n"
            "08:00 | cafe | Abrir o café e arrumar as mesas\n"
        )

        raw = self.llm.generate(system, user)
        return self._parse(raw, available_locations)

    @staticmethod
    def _parse(text: str, available_locations: list[str]) -> list[dict]:
        plan: dict[int, dict] = {}
        for line in text.split("\n"):
            line = line.strip().lstrip("-•* ").strip()
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            time_str, loc, activity = parts[0], parts[1], parts[2]
            hour_match = re.search(r"(\d{1,2})", time_str)
            if not hour_match:
                continue
            hour = int(hour_match.group(1))
            if not (7 <= hour <= 21):
                continue
            # Snap location pra alguma válida
            if loc not in available_locations:
                # Tenta match parcial
                match = next((l for l in available_locations if loc in l or l in loc), None)
                loc = match or available_locations[0]
            plan[hour] = {"hour": hour, "location": loc, "activity": activity}

        # Preenche horas faltantes com fallback (continuação do último plano)
        result = []
        last = None
        for hour in range(7, 22):
            entry = plan.get(hour)
            if entry is None:
                if last:
                    entry = {"hour": hour, "location": last["location"], "activity": last["activity"]}
                else:
                    entry = {"hour": hour, "location": available_locations[0], "activity": "Descansar"}
            result.append(entry)
            last = entry
        return result
