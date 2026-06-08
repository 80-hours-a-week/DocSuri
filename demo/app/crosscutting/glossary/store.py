"""In-memory glossary store (Sprint 1 walking-skeleton).

Implements `GlossaryPort` (AGENTS.md §6.2) for shared use by #02
summarization and #03 translation. Sprint 1 DoD nominally calls for
Redis hash + 24h TTL — a per-session dict suffices for the demo and
keeps the contract identical so the production swap is one line in
`container.py`.

Pre-seeds a few common AI terms so the demo shows a non-empty glossary
immediately when the UI first lands on a paper.
"""

from __future__ import annotations

import asyncio

from app.domain.papers.models import GlossaryEntry

# Pre-seeded common AI terms (§6.2 glossing rule). The first-occurrence
# decision is "frozen" the moment a user starts a session.
_SEED: list[GlossaryEntry] = [
    GlossaryEntry(english="transformer", korean="트랜스포머"),
    GlossaryEntry(english="attention", korean="주의"),
    GlossaryEntry(english="embedding", korean="임베딩"),
    GlossaryEntry(english="neural network", korean="신경망"),
    GlossaryEntry(english="language model", korean="언어 모델"),
    GlossaryEntry(english="self-attention", korean="자기 주의"),
    GlossaryEntry(english="encoder", korean="인코더"),
    GlossaryEntry(english="decoder", korean="디코더"),
    GlossaryEntry(english="token", korean="토큰"),
    GlossaryEntry(english="fine-tuning", korean="미세 조정"),
    GlossaryEntry(english="pre-training", korean="사전 학습"),
]


class InMemoryGlossary:
    """Per-session dict implementation of `GlossaryPort`."""

    def __init__(self) -> None:
        # session_id -> {english_lower -> entry}
        self._store: dict[str, dict[str, GlossaryEntry]] = {}
        self._lock = asyncio.Lock()

    async def _ensure_session(self, session_id: str) -> dict[str, GlossaryEntry]:
        async with self._lock:
            if session_id not in self._store:
                self._store[session_id] = {e.english.lower(): e for e in _SEED}
            return self._store[session_id]

    async def lookup(self, session_id: str, english: str) -> GlossaryEntry | None:
        session = await self._ensure_session(session_id)
        return session.get(english.lower())

    async def add(self, session_id: str, entry: GlossaryEntry) -> None:
        session = await self._ensure_session(session_id)
        async with self._lock:
            # First-write-wins: §6.2 demands stable per-session mapping.
            session.setdefault(entry.english.lower(), entry)

    async def list_for_session(self, session_id: str) -> list[GlossaryEntry]:
        session = await self._ensure_session(session_id)
        return list(session.values())
