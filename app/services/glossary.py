from __future__ import annotations

import re
from collections import defaultdict

from app.models import GlossaryTerm


DEFAULT_TERMS = {
    "attention": "주의",
    "embedding": "임베딩",
    "embeddings": "임베딩",
    "retrieval": "검색",
    "retrieval-augmented": "검색 증강",
    "summary": "요약",
    "summarization": "요약",
    "translation": "번역",
    "verifier": "검증기",
    "validation": "검증",
    "language model": "언어 모델",
    "pgvector": "PGVector",
    "postgresql": "PostgreSQL",
    "vector": "벡터",
    "chunk": "청크",
    "chunks": "청크",
}


class GlossaryStore:
    def __init__(self) -> None:
        self._terms: dict[str, dict[str, str]] = defaultdict(dict)

    def list_terms(self, session_id: str) -> list[GlossaryTerm]:
        return [
            GlossaryTerm(source=source, target=target, first_seen=False)
            for source, target in sorted(self._terms[session_id].items())
        ]

    def lookup(self, session_id: str, text: str) -> list[GlossaryTerm]:
        found: list[GlossaryTerm] = []
        session_terms = self._terms[session_id]
        for source, target in DEFAULT_TERMS.items():
            if re.search(rf"\b{re.escape(source)}\b", text, flags=re.IGNORECASE):
                normalized = source.lower()
                first_seen = normalized not in session_terms
                session_terms.setdefault(normalized, target)
                found.append(GlossaryTerm(source=normalized, target=session_terms[normalized], first_seen=first_seen))
        return found

    def upsert_many(self, session_id: str, terms: list[GlossaryTerm]) -> list[GlossaryTerm]:
        session_terms = self._terms[session_id]
        updated: list[GlossaryTerm] = []
        for term in terms:
            source = term.source.lower().strip()
            target = term.target.strip()
            if not source or not target:
                continue
            first_seen = source not in session_terms
            session_terms[source] = target
            updated.append(GlossaryTerm(source=source, target=target, first_seen=first_seen))
        return updated
