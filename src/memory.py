"""Memory Stream: armazena entradas e recupera por recência + relevância + importância.

No paper original (Park et al., 2023), o score de recuperação combina três
fatores normalizados. Nós seguimos a mesma ideia, com fallback gracioso quando
embeddings não estão disponíveis (modo mock).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from config.settings import (
    IMPORTANCE_WEIGHT,
    RECENCY_HALF_LIFE_HOURS,
    RECENCY_WEIGHT,
    RELEVANCE_WEIGHT,
)


@dataclass
class MemoryEntry:
    text: str
    timestamp: tuple  # (day, hour)
    importance: float  # 1..10
    embedding: Optional[list[float]] = None
    entry_type: str = "observation"  # observation | reflection | plan | conversation

    def absolute_hours(self) -> int:
        day, hour = self.timestamp
        return day * 24 + hour


def _cosine(a: Optional[list[float]], b: Optional[list[float]]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class MemoryStream:
    """Memória episódica do agente."""

    def __init__(self):
        self.entries: list[MemoryEntry] = []

    def add(self, entry: MemoryEntry) -> None:
        self.entries.append(entry)

    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        return self.entries[-n:]

    def retrieve(
        self,
        query: str,
        k: int = 5,
        current_time: Optional[tuple] = None,
        query_embedding: Optional[list[float]] = None,
    ) -> list[MemoryEntry]:
        """Top-k entradas por score combinado.

        - recency: decay exponencial por meia-vida (RECENCY_HALF_LIFE_HOURS)
        - relevance: cosine sim entre query_embedding e entry.embedding (0 se sem embedding)
        - importance: entry.importance / 10
        """
        if not self.entries:
            return []

        now_abs = (
            current_time[0] * 24 + current_time[1]
            if current_time
            else self.entries[-1].absolute_hours()
        )

        scored = []
        for entry in self.entries:
            # Recency
            age = max(0, now_abs - entry.absolute_hours())
            recency = math.pow(0.5, age / RECENCY_HALF_LIFE_HOURS)

            # Relevance (0 se embeddings ausentes)
            relevance = _cosine(query_embedding, entry.embedding)

            # Importance normalizada
            importance = max(0.0, min(1.0, entry.importance / 10.0))

            score = (
                RECENCY_WEIGHT * recency
                + RELEVANCE_WEIGHT * relevance
                + IMPORTANCE_WEIGHT * importance
            )
            scored.append((score, entry))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [e for _, e in scored[:k]]

    def __len__(self) -> int:
        return len(self.entries)
