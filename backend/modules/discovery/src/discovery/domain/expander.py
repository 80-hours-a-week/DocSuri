"""QueryUnderstandingExpander — FR-2 / Q1=A (BR-3).

expand = query embedding (reader=search_query, cross-lingual) + lexical terms (tokenized).
NO synonym/LLM rewrite (determinism + NFR-C1). When ``llm_enabled`` is false (cost
degrade LEXICAL_ONLY), the embedding is skipped and the plan is lexical-only.

Embedding failure propagates ``EmbeddingUnavailable`` — the orchestrator catches it and
falls back to lexical-only (dependency fail-fast, BR-16/Q1).
"""

from __future__ import annotations

from ..ports.search_ports import EmbeddingAdapter
from .models import DegradationSignal, NormalizedQuery, QueryPlan, RetrievalMode


def _tokenize(text: str) -> tuple[str, ...]:
    """Deterministic lexical terms: lowercase whitespace split (no stemming/synonyms)."""
    return tuple(t for t in text.lower().split() if t)


class QueryUnderstandingExpander:
    def __init__(self, embedding_adapter: EmbeddingAdapter) -> None:
        self._embedding = embedding_adapter

    def expand(self, query: NormalizedQuery, degradation: DegradationSignal) -> QueryPlan:
        lexical_terms = _tokenize(query.text)
        if not degradation.llm_enabled:
            return QueryPlan(lexical_terms=lexical_terms, mode=RetrievalMode.LEXICAL_ONLY)
        # search_query inputType is the adapter's responsibility (vector-spec.md asymmetry).
        vector = tuple(self._embedding.embed_query(query.text))
        return QueryPlan(
            lexical_terms=lexical_terms,
            mode=RetrievalMode.HYBRID,
            embedding_vector=vector,
        )
