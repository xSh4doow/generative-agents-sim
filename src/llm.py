"""Wrapper de LLM: OpenAIClient (real) e MockClient (templates).

A interface é a mesma — o resto do código não sabe qual está usando.
"""

from __future__ import annotations

import os
import random
import re
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


SEED_KEYWORDS = ["feira", "artesanato", "sábado", "sabado"]


class LLMClient(ABC):
    """Interface base para clientes de LLM."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...

    def embed(self, text: str) -> Optional[list[float]]:
        """Retorna embedding do texto. Default: None (sem embeddings)."""
        return None


class OpenAIClient(LLMClient):
    """Chamadas reais via openai SDK. Modelo: gpt-4o-mini."""

    def __init__(self, model: str = "gpt-4o-mini",
                 embedding_model: str = "text-embedding-3-small"):
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY não configurada. Copie .env.example para .env "
                "e cole sua chave, ou rode com --mode mock."
            )
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.embedding_model = embedding_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return (resp.choices[0].message.content or "").strip()

    def embed(self, text: str) -> Optional[list[float]]:
        if not text:
            return None
        resp = self.client.embeddings.create(
            model=self.embedding_model,
            input=text[:8000],
        )
        return resp.data[0].embedding


class MockClient(LLMClient):
    """Cliente fake: detecta intent do prompt e devolve template variado.

    O objetivo é deixar a simulação rodar sem API key e ainda assim ter
    variabilidade suficiente pra ser observável.
    """

    # Pools de respostas
    _ACTIVITIES = [
        "Acordar e tomar café",
        "Trabalhar no ofício",
        "Caminhar pela vila",
        "Cumprimentar vizinhos",
        "Almoçar com calma",
        "Descansar um pouco",
        "Ler ou refletir",
        "Visitar um amigo",
        "Cuidar de tarefas pessoais",
        "Conversar com quem aparecer",
        "Jantar tranquilamente",
        "Preparar-se para dormir",
        "Organizar pensamentos",
        "Observar o movimento",
        "Tomar um café fresco",
    ]

    _INSIGHTS = [
        "Percebo que as pessoas aqui se importam umas com as outras de verdade.",
        "Tenho notado padrões interessantes no dia a dia da vila.",
        "Acho que preciso me abrir mais para novas conversas.",
        "A rotina daqui me traz mais paz do que eu esperava.",
        "Aprendo coisas novas sobre os outros quando paro para escutar.",
        "Algumas conversas recentes mexeram comigo de um jeito bom.",
        "Sinto que estou criando vínculos verdadeiros com a vizinhança.",
        "Cada dia traz uma surpresa pequena, e isso é bonito.",
        "Tem coisas circulando pela vila que merecem atenção.",
        "Preciso lembrar de cuidar de mim também, não só dos outros.",
        "Reparei que silêncios às vezes dizem mais que palavras.",
        "Talvez eu esteja vendo a vila com olhos novos hoje.",
    ]

    _GENERIC_TOPICS = [
        "como foi o dia",
        "o tempo na vila",
        "novidades da vizinhança",
        "planos para amanhã",
        "um livro ou ideia recente",
        "lembranças antigas",
        "um café que tomei",
    ]

    _OPENERS = ["Oi!", "E aí!", "Tudo bem?", "Olá!", "Bom te ver!"]

    _CLOSINGS = [
        "Foi bom conversar, até mais!",
        "Acho que vou indo, a gente se vê.",
        "Cuide-se, tchau!",
        "Bom papo, até logo.",
        "Vamos nos falando.",
    ]

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        full = (system_prompt + "\n" + user_prompt).lower()

        if "crie um plano" in full or "plano para o seu dia" in full:
            return self._mock_plan(user_prompt)
        if any(k in full for k in ["insights", "conclusões", "reflexão"]):
            return self._mock_reflection()
        if "quer conversar" in full:
            return self._mock_interaction(user_prompt)
        if "gere uma conversa" in full or "gere o diálogo" in full or "uma conversa curta" in full:
            return self._mock_conversation(user_prompt)
        return "Tudo certo por aqui."

    # ---- intent handlers --------------------------------------------------

    def _mock_plan(self, user_prompt: str) -> str:
        locations = self._extract_locations(user_prompt)
        if not locations:
            locations = ["praca", "cafe", "biblioteca"]

        # Home: respeita "Sua casa é: X" se presente, senão pega a primeira casa_
        home_match = re.search(r"Sua casa é:\s*(\w+)", user_prompt)
        if home_match:
            home = home_match.group(1).strip()
        else:
            home = next((l for l in locations if l.startswith("casa_")), locations[0])

        # Locais "públicos" pra mistura no meio do dia
        public_locs = [l for l in locations if not l.startswith("casa_")]
        if not public_locs:
            public_locs = locations

        lines = []
        for h in range(7, 22):
            if h < 9 or h >= 20:
                loc = home
            elif h in (12, 13):
                # Almoço em casa às vezes
                loc = random.choice([home] + public_locs)
            else:
                loc = random.choice(public_locs)
            activity = random.choice(self._ACTIVITIES)
            lines.append(f"{h:02d}:00 | {loc} | {activity}")
        return "\n".join(lines)

    def _mock_reflection(self) -> str:
        picks = random.sample(self._INSIGHTS, k=3)
        return "\n".join(f"- {p}" for p in picks)

    def _mock_interaction(self, user_prompt: str) -> str:
        # ~70% chance de querer conversar
        if random.random() > 0.7:
            return "Não."

        topics = list(self._GENERIC_TOPICS)
        # Tópicos vindos do "Você sabe atualmente sobre:" no prompt
        m = re.search(r"sabe atualmente sobre:\s*\n((?:- .+\n?)+)", user_prompt)
        if m:
            for item in re.findall(r"- (.+)", m.group(1)):
                topics.append(item.strip())

        chosen = random.choice(topics)
        return f"Sim, sobre {chosen}."

    def _mock_conversation(self, user_prompt: str) -> str:
        a, b = self._extract_two_names(user_prompt)
        topic_match = re.search(r"sobre [\"'`]([^\"'`]+)[\"'`]", user_prompt)
        topic = topic_match.group(1) if topic_match else "o dia"

        # Detecta se algum participante "sabe" sobre a feira
        seed_known = (
            "feira de artesanato" in user_prompt.lower()
            or any(k in topic.lower() for k in SEED_KEYWORDS)
        )

        if seed_known and (
            any(k in topic.lower() for k in SEED_KEYWORDS) or random.random() < 0.6
        ):
            turns = [
                f"{a}: Você ouviu que vai ter uma feira de artesanato no próximo sábado na praça?",
                f"{b}: Não sabia disso! Conta mais.",
                f"{a}: Acho que vai ser bom pra vila, todo mundo está animado.",
                f"{b}: Vou tentar passar lá no sábado, obrigado por contar.",
            ]
        else:
            opener = random.choice(self._OPENERS)
            mid_a = random.choice([
                f"Como foi seu dia?",
                f"Algo interessante sobre {topic}?",
                f"O que anda achando da vila?",
                f"Conta uma novidade.",
            ])
            mid_b = random.choice([
                "Tudo tranquilo, e com você?",
                "Foi um dia comum, mas bom.",
                f"Sobre {topic}, é algo pra pensar mesmo.",
                "Aos poucos vou me acostumando.",
            ])
            close = random.choice(self._CLOSINGS)
            turns = [
                f"{a}: {opener} {mid_a}",
                f"{b}: {mid_b}",
                f"{a}: Faz sentido. {random.choice(self._GENERIC_TOPICS).capitalize()}, né?",
                f"{b}: {close}",
            ]
        return "\n".join(turns)

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _extract_locations(prompt: str) -> list[str]:
        m = re.search(r"Locais disponíveis:\s*([^\n]+)", prompt)
        if not m:
            return []
        raw = m.group(1)
        return [tok.strip() for tok in re.split(r"[,;]", raw) if tok.strip()]

    @staticmethod
    def _extract_two_names(prompt: str) -> tuple[str, str]:
        a_match = re.search(r"Você é (\w+)\.", prompt)
        b_match = re.search(r"conversando com (\w+)\.", prompt)
        if a_match and b_match:
            return a_match.group(1), b_match.group(1)
        # Fallback genérico
        return "Agente A", "Agente B"
