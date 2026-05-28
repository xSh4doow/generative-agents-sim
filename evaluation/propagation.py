"""Rastreia propagação de uma informação-semente entre agentes."""

from __future__ import annotations

from config.settings import SEED_KEYWORDS


class PropagationTracker:
    def __init__(self, seed_info: str, seed_agent: str):
        self.seed_info = seed_info
        self.seed_keywords = SEED_KEYWORDS
        # agente -> (dia, hora) quando soube
        self.informed_agents: dict[str, tuple] = {seed_agent: (1, 7)}
        self.events: list[dict] = [
            {"agent": seed_agent, "time": (1, 7), "via": "seed"}
        ]

    def mark_informed(self, agent_name: str, time: tuple, via: str = "conversation") -> bool:
        if agent_name in self.informed_agents:
            return False
        self.informed_agents[agent_name] = time
        self.events.append({"agent": agent_name, "time": time, "via": via})
        return True

    def check_conversation(
        self,
        conversation: list[dict],
        participants: list[str],
        time: tuple,
    ) -> list[str]:
        """Verifica se a seed_info circulou na conversa.

        Heurística: ao menos 2 keywords da seed presentes no texto da conversa.
        Se algum participante já sabia e há outro que não sabia → o outro fica
        sabendo agora.

        Retorna lista de nomes recém-informados.
        """
        if not conversation:
            return []

        text = " ".join(t.get("text", "") for t in conversation).lower()
        hits = sum(1 for k in self.seed_keywords if k in text)
        if hits < 2:
            return []

        informed_in_chat = [p for p in participants if p in self.informed_agents]
        if not informed_in_chat:
            return []

        newly = []
        for p in participants:
            if p in self.informed_agents:
                continue
            if self.mark_informed(p, time):
                newly.append(p)
        return newly

    def get_propagation_timeline(self) -> list[dict]:
        return sorted(
            (
                {"agent": a, "time": list(t)}
                for a, t in self.informed_agents.items()
            ),
            key=lambda e: (e["time"][0], e["time"][1]),
        )

    def get_propagation_rate(self, total_agents: int) -> float:
        if not total_agents:
            return 0.0
        return len(self.informed_agents) / total_agents
