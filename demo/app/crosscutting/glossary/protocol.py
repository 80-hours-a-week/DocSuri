"""Owner port for the session glossary (AGENTS.md §6.2).

Shared by #02 summarization and #03 translation. Implementation lives in
`store.py` (Redis hash in production; in-memory dict in this demo).
"""

from __future__ import annotations

from typing import Protocol

from app.domain.papers.models import GlossaryEntry


class GlossaryPort(Protocol):
    async def lookup(self, session_id: str, english: str) -> GlossaryEntry | None:
        ...

    async def add(self, session_id: str, entry: GlossaryEntry) -> None:
        ...

    async def list_for_session(self, session_id: str) -> list[GlossaryEntry]:
        ...
