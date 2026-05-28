"""Classe Agent: persona + memória + reflexão + planejamento + interação."""

from __future__ import annotations

import re

from src.llm import LLMClient
from src.memory import MemoryEntry, MemoryStream
from src.planner import DailyPlanner
from src.reflection import ReflectionModule


class Agent:
    def __init__(self, persona: dict, llm: LLMClient):
        self.name = persona["name"]
        self.bio = persona["bio"]
        self.traits = list(persona.get("traits", []))
        self.location = persona["initial_location"]
        self.home = persona["initial_location"]
        self.memory = MemoryStream()
        self.reflection = ReflectionModule(llm)
        self.planner = DailyPlanner(llm)
        self.daily_plan: list[dict] = []
        self.llm = llm
        self.known_info: set[str] = set()

    # ---- ciclo de vida --------------------------------------------------

    def start_day(self, day: int, available_locations: list[str]) -> None:
        recent = [e.text for e in self.memory.get_recent(8)]
        plan = self.planner.plan_day(
            self.name, self.bio, day, recent, available_locations, home=self.home
        )
        self.daily_plan = plan
        summary = (
            f"Planejei meu dia {day}: "
            f"{', '.join(set(p['location'] for p in plan[:5]))}..."
        )
        self.memory.add(
            MemoryEntry(
                text=summary,
                timestamp=(day, 7),
                importance=3.0,
                embedding=self.llm.embed(summary),
                entry_type="plan",
            )
        )

    def get_planned_location(self, hour: int) -> str:
        for p in self.daily_plan:
            if p["hour"] == hour:
                return p["location"]
        return self.location

    def get_planned_activity(self, hour: int) -> str:
        for p in self.daily_plan:
            if p["hour"] == hour:
                return p["activity"]
        return "Existindo na vila"

    def observe(self, observation: str, time: tuple) -> None:
        self.memory.add(
            MemoryEntry(
                text=observation,
                timestamp=time,
                importance=self._importance_heuristic(observation),
                embedding=self.llm.embed(observation),
                entry_type="observation",
            )
        )

    # ---- interação social ----------------------------------------------

    def decide_interaction(
        self,
        other_agents: list["Agent"],
        location: str,
        time: tuple,
    ) -> tuple["Agent", str] | None:
        if not other_agents:
            return None
        other = other_agents[0]

        known_block = (
            "\n".join(f"- {info}" for info in self.known_info)
            if self.known_info
            else "- (nada além do dia a dia)"
        )
        recent = self.memory.get_recent(5)
        mem_block = (
            "\n".join(f"- {e.text}" for e in recent)
            if recent
            else "- (sem memórias relevantes)"
        )

        system = "Você simula a decisão social de um humano. Seja conciso."
        user = (
            f"Você é {self.name}. {self.bio}\n\n"
            f"Você está em {location}.\n"
            f"{other.name} também está aqui.\n\n"
            f"Você sabe atualmente sobre:\n{known_block}\n\n"
            f"Suas memórias recentes:\n{mem_block}\n\n"
            f"Você quer conversar com {other.name}? Se sim, sobre o quê? "
            "Se não, responda apenas \"Não.\"\n"
            "Formato: \"Sim, sobre [tópico].\" OU \"Não.\""
        )

        response = self.llm.generate(system, user).strip()
        topic = self._parse_interaction(response)
        if topic is None:
            return None
        return other, topic

    def converse(self, other: "Agent", topic: str, time: tuple) -> list[dict]:
        my_known = (
            "\n".join(f"- {info}" for info in self.known_info)
            if self.known_info
            else "- (nada além do dia a dia)"
        )
        other_known = (
            "\n".join(f"- {info}" for info in other.known_info)
            if other.known_info
            else "- (nada além do dia a dia)"
        )

        system = "Você gera diálogos curtos e naturais entre dois moradores de uma vila."
        user = (
            f"Você é {self.name}. {self.bio}\n"
            f"Está conversando com {other.name}. {other.bio}\n\n"
            f"O tópico é \"{topic}\".\n\n"
            f"{self.name} sabe atualmente sobre:\n{my_known}\n\n"
            f"{other.name} sabe atualmente sobre:\n{other_known}\n\n"
            "Gere uma conversa curta de 4 turnos (cada um fala 2 vezes), alternando.\n"
            f"Formato (uma fala por linha):\n"
            f"{self.name}: ...\n{other.name}: ...\n{self.name}: ...\n{other.name}: ..."
        )

        raw = self.llm.generate(system, user)
        turns = self._parse_conversation(raw, self.name, other.name)

        if not turns:
            return []

        joined = " | ".join(f"{t['speaker']}: {t['text']}" for t in turns)

        # Cada agente registra a conversa do seu próprio ponto de vista
        for agent, peer in ((self, other), (other, self)):
            obs = f"Conversei com {peer.name} sobre \"{topic}\": {joined}"
            agent.memory.add(
                MemoryEntry(
                    text=obs,
                    timestamp=time,
                    importance=5.0,
                    embedding=agent.llm.embed(obs),
                    entry_type="conversation",
                )
            )

        return turns

    def maybe_reflect(self, current_time: tuple) -> list[str]:
        if self.reflection.should_reflect(self.memory):
            return self.reflection.reflect(self.name, self.bio, self.memory, current_time)
        return []

    # ---- helpers -------------------------------------------------------

    @staticmethod
    def _importance_heuristic(text: str) -> float:
        score = 2.0
        lower = text.lower()
        keywords = ["importante", "preciso", "decisão", "ajuda", "feira",
                    "artesanato", "novidade", "problema"]
        score += sum(1 for k in keywords if k in lower) * 1.0
        if len(text) > 100:
            score += 1.0
        return float(min(score, 10.0))

    @staticmethod
    def _parse_interaction(response: str) -> str | None:
        if not response:
            return None
        lower = response.strip().lower()
        if lower.startswith("não") or lower.startswith("nao") or lower == "n":
            return None
        # Tentar extrair "sobre X"
        m = re.search(r"sobre\s+(.+?)\.?\s*$", response, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip().strip(".").strip()
        # Senão, devolve a resposta limpa como tópico
        cleaned = re.sub(r"^sim[,.]?\s*", "", response.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.strip(".").strip()
        return cleaned or None

    @staticmethod
    def _parse_conversation(raw: str, name_a: str, name_b: str) -> list[dict]:
        turns = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            speaker, text = line.split(":", 1)
            speaker = speaker.strip()
            text = text.strip()
            if not text:
                continue
            if name_a.lower() in speaker.lower():
                actual = name_a
            elif name_b.lower() in speaker.lower():
                actual = name_b
            else:
                # Ignora linha sem speaker identificável (provavelmente lixo)
                continue
            turns.append({"speaker": actual, "text": text})
        return turns[:6]  # cap de segurança
