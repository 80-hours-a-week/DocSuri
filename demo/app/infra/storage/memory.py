"""In-memory paper store (Sprint 1).

Per AGENTS.md §4.2: PDFs MUST NOT persist to disk; session-scope only.
Production will replace with Redis + Postgres metadata.
"""

from __future__ import annotations

import asyncio

from app.domain.papers.models import Paper


class PaperStore:
    def __init__(self) -> None:
        self._papers: dict[str, Paper] = {}
        self._lock = asyncio.Lock()

    async def put(self, paper: Paper) -> None:
        async with self._lock:
            self._papers[paper.summary.id] = paper

    async def get(self, paper_id: str) -> Paper | None:
        return self._papers.get(paper_id)

    async def all_ids(self) -> list[str]:
        return list(self._papers.keys())


store = PaperStore()
