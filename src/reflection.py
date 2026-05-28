"""Módulo de reflexão.

Periodicamente, o agente olha pra suas memórias recentes e tira insights de
alto nível. Esses insights viram novas entradas no memory stream com
importância alta, e influenciam decisões futuras.
"""

from __future__ import annotations

from config.settings import (
    REFLECTION_IMPORTANCE_THRESHOLD,
    REFLECTION_OBSERVATION_THRESHOLD,
)
from src.llm import LLMClient
from src.memory import MemoryEntry, MemoryStream


class ReflectionModule:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _entries_since_last_reflection(self, mem: MemoryStream) -> list[MemoryEntry]:
        last_idx = -1
        for i in range(len(mem.entries) - 1, -1, -1):
            if mem.entries[i].entry_type == "reflection":
                last_idx = i
                break
        return mem.entries[last_idx + 1:]

    def should_reflect(self, memory_stream: MemoryStream) -> bool:
        since = self._entries_since_last_reflection(memory_stream)
        if not since:
            return False
        importance_sum = sum(e.importance for e in since)
        obs_count = sum(1 for e in since if e.entry_type == "observation")
        return (
            importance_sum > REFLECTION_IMPORTANCE_THRESHOLD
            or obs_count >= REFLECTION_OBSERVATION_THRESHOLD
        )

    def reflect(
        self,
        agent_name: str,
        agent_bio: str,
        memory_stream: MemoryStream,
        current_time: tuple,
    ) -> list[str]:
        recent = memory_stream.get_recent(20)
        if not recent:
            return []

        memories_formatted = "\n".join(
            f"- (D{e.timestamp[0]} {e.timestamp[1]:02d}h) {e.text}" for e in recent
        )

        system = "Você simula o pensamento de uma pessoa real. Responda em primeira pessoa."
        user = (
            f"Você é {agent_name}. {agent_bio}\n\n"
            f"Suas memórias recentes:\n{memories_formatted}\n\n"
            "Com base nessas experiências, quais são os 3 insights ou conclusões "
            f"mais importantes que você tiraria? Responda como {agent_name} falaria, "
            "em primeira pessoa. Um insight por linha, começando com \"- \"."
        )

        raw = self.llm.generate(system, user)
        insights = self._parse_insights(raw)

        # Cada insight vira reflexão no stream
        for insight in insights:
            entry = MemoryEntry(
                text=insight,
                timestamp=current_time,
                importance=8.0,
                embedding=self.llm.embed(insight),
                entry_type="reflection",
            )
            memory_stream.add(entry)

        return insights

    @staticmethod
    def _parse_insights(raw: str) -> list[str]:
        lines = []
        for line in raw.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("-", "•", "*")):
                stripped = stripped.lstrip("-•* ").strip()
            if stripped:
                lines.append(stripped)
        return lines[:3] if lines else [raw.strip()] if raw.strip() else []
