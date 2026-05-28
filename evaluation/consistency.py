"""Avalia consistência entre a bio do agente e suas ações/observações.

- Modo LLM: usa embeddings (text-embedding-3-small) + cosine similarity.
- Modo mock: usa TF-IDF como proxy (scikit-learn).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from src.llm import LLMClient

if TYPE_CHECKING:
    from src.agent import Agent


class ConsistencyEvaluator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def evaluate(self, agent: "Agent") -> dict:
        bio = agent.bio
        actions = [
            e.text
            for e in agent.memory.entries
            if e.entry_type in ("conversation", "observation", "reflection")
        ]
        actions = actions[:30]  # cap pra não explodir embeddings

        if not actions:
            return {
                "agent": agent.name,
                "mean_similarity": 0.0,
                "scores": [],
                "n": 0,
                "method": "n/a",
            }

        bio_emb = self.llm.embed(bio)
        if bio_emb is not None:
            scores = []
            for act in actions:
                act_emb = self.llm.embed(act)
                if act_emb is not None:
                    scores.append(self._cosine(bio_emb, act_emb))
            method = "embeddings"
        else:
            scores = self._tfidf_scores(bio, actions)
            method = "tfidf"

        mean = sum(scores) / len(scores) if scores else 0.0
        return {
            "agent": agent.name,
            "mean_similarity": float(mean),
            "scores": [float(s) for s in scores],
            "n": len(actions),
            "method": method,
        }

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    @staticmethod
    def _tfidf_scores(bio: str, actions: list[str]) -> list[float]:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            return [0.0] * len(actions)

        texts = [bio] + actions
        vec = TfidfVectorizer()
        try:
            mat = vec.fit_transform(texts)
        except ValueError:
            return [0.0] * len(actions)
        sims = cosine_similarity(mat[0:1], mat[1:]).flatten()
        return sims.tolist()
