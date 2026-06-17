"""OpenSearch read adapters — real ``VectorStoreAdapter`` + ``LexicalIndexAdapter``.

The reader mirror of U1's ``OpenSearchVectorIndex`` writer: the SAME index
(``docsuri-corpus-v1``), one store serving both k-NN (cosine, ``vector``) and BM25
(``lexicalTerms``) — hybrid retrieval (FR-2). Hits are deserialized straight back into the
shared ``IndexRecord`` (SSOT round-trip; no forked shape). OpenSearch is one store, so ANY
query failure raises ``IndexUnavailable`` → the orchestrator fail-closes (INV-3/SEC-15);
there is no index fallback (only embedding has a fallback).

ports declares ``VectorStoreAdapter`` and ``LexicalIndexAdapter`` as two protocols; they are
exposed as two adapter objects but share one OpenSearch client via ``OpenSearchClientFactory``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from docsuri_shared.vector_spec import IndexRecord

from ..ports.search_ports import IndexUnavailable, ScoredRecord


class OpenSearchClientFactory:
    """Builds the shared ``opensearch-py`` client (lazy import; the ``real`` extra)."""

    @staticmethod
    def build(
        *,
        endpoint: str,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool = True,
        verify_certs: bool = True,
    ) -> Any:
        from opensearchpy import OpenSearch

        http_auth = (username, password) if username and password else None
        return OpenSearch(
            hosts=[endpoint],
            http_auth=http_auth,
            use_ssl=use_ssl,
            verify_certs=verify_certs,
        )


def _to_scored(hits: list[dict[str, Any]]) -> list[ScoredRecord]:
    """Deserialize OpenSearch hits → (IndexRecord, store score), preserving rank order."""
    scored: list[ScoredRecord] = []
    for hit in hits:
        record = IndexRecord.model_validate(hit["_source"])
        scored.append((record, float(hit.get("_score") or 0.0)))
    return scored


class OpenSearchVectorStoreAdapter:
    """k-NN (ANN) reader over the shared OpenSearch index (cosine; FR-2)."""

    def __init__(self, client: Any, index_name: str) -> None:
        self._client = client
        self._index = index_name

    def knn_search(self, vector: Sequence[float], top_k: int) -> list[ScoredRecord]:
        body = {
            "size": top_k,
            "query": {"knn": {"vector": {"vector": list(vector), "k": top_k}}},
        }
        try:
            response = self._client.search(index=self._index, body=body)
            hits = response["hits"]["hits"]
        except Exception as exc:  # noqa: BLE001 — one store; any failure → fail-closed (INV-3)
            raise IndexUnavailable("OpenSearch k-NN query failed") from exc
        return _to_scored(hits)


class OpenSearchLexicalIndexAdapter:
    """BM25 lexical reader over the shared OpenSearch index (``lexicalTerms``; FR-2)."""

    def __init__(self, client: Any, index_name: str) -> None:
        self._client = client
        self._index = index_name

    def bm25_search(self, terms: Sequence[str], top_k: int) -> list[ScoredRecord]:
        body = {
            "size": top_k,
            "query": {"match": {"lexicalTerms": " ".join(terms)}},
        }
        try:
            response = self._client.search(index=self._index, body=body)
            hits = response["hits"]["hits"]
        except Exception as exc:  # noqa: BLE001 — one store; any failure → fail-closed (INV-3)
            raise IndexUnavailable("OpenSearch BM25 query failed") from exc
        return _to_scored(hits)
