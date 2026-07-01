"""OpenSearch read adapters — real ``VectorStoreAdapter`` + ``LexicalIndexAdapter``.

The reader mirror of U1's ``OpenSearchVectorIndex`` writer: the SAME index
(``docsuri-corpus-v1``), one store serving both k-NN (cosine, ``vector``) and BM25
(``title``/``abstract``/``lexicalTerms``) — hybrid retrieval (FR-2). Hits are
deserialized straight back into the shared ``IndexRecord`` (SSOT round-trip; no forked
shape). OpenSearch is one store, so ANY
query failure raises ``IndexUnavailable`` → the orchestrator fail-closes (INV-3/SEC-15);
there is no index fallback (only embedding has a fallback).

ports declares ``VectorStoreAdapter`` and ``LexicalIndexAdapter`` as two protocols; they are
exposed as two adapter objects but share one OpenSearch client via ``OpenSearchClientFactory``.
"""

from __future__ import annotations

import logging
import time
import re
from collections.abc import Sequence
from typing import Any

from docsuri_shared.vector_spec import IndexRecord
from pydantic import ValidationError

from ..ports.search_ports import IndexUnavailable, ScoredRecord

_log = logging.getLogger(__name__)

# Bounded transient-retry for the single OpenSearch store. Search is a read (idempotent), and
# under heavy concurrent indexing (e.g. a corpus rebuild) the cluster returns brief transient
# failures — a shard relocating, a GC pause, a momentary timeout. A short retry absorbs most of
# those so one unlucky moment does not surface to the user as a 503; repeated failure still
# fail-closes (INV-3). Kept small so an added retry never blows the P50<3s search budget.
_SEARCH_MAX_ATTEMPTS = 3
_SEARCH_RETRY_BACKOFF_S = (0.1, 0.25)  # sleeps before attempt 2 and attempt 3


def _search_hits(
    client: Any, index: str, body: dict[str, Any], *, label: str, message: str
) -> list[dict[str, Any]]:
    """Run a search and return its hits, retrying transient store failures before fail-closing to
    ``IndexUnavailable``. On exhaustion the underlying error is logged (type + truncated message)
    — the previous ``raise ... from exc`` discarded it from the logs, so a real outage vs. a
    transient blip was indistinguishable."""
    last_exc: Exception | None = None
    for attempt in range(_SEARCH_MAX_ATTEMPTS):
        try:
            response = client.search(index=index, body=body)
            return response["hits"]["hits"]
        except Exception as exc:  # noqa: BLE001 — one store; transient-tolerant then fail-closed
            last_exc = exc
            if attempt < _SEARCH_MAX_ATTEMPTS - 1:
                time.sleep(_SEARCH_RETRY_BACKOFF_S[attempt])
    _log.warning(
        "discovery.%s failed after %d attempt(s): %s: %s",
        label,
        _SEARCH_MAX_ATTEMPTS,
        type(last_exc).__name__,
        str(last_exc)[:200],
    )
    raise IndexUnavailable(message) from last_exc
# arXiv version suffix ("v3"). paperId is stored version-less, so stripping the requested id's
# version lets the detail lookup resolve a paper indexed at a *different* version than the one
# asked for. Mirrors ingestion's normalize_arxiv_ref (ingestion/.../domain/ids.py); cross-module
# id parsing isn't shared yet, so this small strip is duplicated.
_VERSION_SUFFIX_RE = re.compile(r"v[1-9][0-9]*$", re.IGNORECASE)


def _hit_id(hit: dict[str, Any]) -> str:
    """Best-effort identifier for a hit, for drop diagnostics. Uses only id-shaped fields
    (never title/abstract/body) so a drop log can never leak indexed content (SEC-9/SEC-15)."""
    source = hit.get("_source") or {}
    return str(hit.get("_id") or source.get("chunkId") or source.get("paperId") or "<unknown>")


def _drift_fields(exc: ValidationError) -> list[str]:
    """Dotted field paths that failed validation — locations ONLY, never the offending values
    (a value would carry indexed content). Surfaces WHICH part of the contract drifted."""
    return sorted({".".join(str(p) for p in err["loc"]) for err in exc.errors()})


class OpenSearchClientFactory:
    """Builds the shared ``opensearch-py`` client (lazy import; the ``real`` extra)."""

    @staticmethod
    def build(
        *,
        endpoint: str,
        region_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool = True,
        verify_certs: bool = True,
    ) -> Any:
        from opensearchpy import OpenSearch

        # Auth order mirrors the U1 writer (ingestion.build_opensearch_client): basic-auth if
        # both creds are given (local/override), else SigV4 (``Urllib3AWSV4SignerAuth``, service
        # ``es``) when a region is set — the managed VPC domain authorizes the ECS task role by
        # resource policy, so signed requests are required — else unsigned (local open cluster).
        http_auth: Any
        if username and password:
            http_auth = (username, password)
        elif region_name:
            import boto3
            from opensearchpy import Urllib3AWSV4SignerAuth

            http_auth = Urllib3AWSV4SignerAuth(
                boto3.Session().get_credentials(), region_name, "es"
            )
        else:
            http_auth = None
        return OpenSearch(
            hosts=[endpoint],
            http_auth=http_auth,
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            timeout=10,
        )


def _to_scored(hits: list[dict[str, Any]]) -> list[ScoredRecord]:
    """Deserialize OpenSearch hits → (IndexRecord, store score), preserving rank order.

    A hit whose stored ``_source`` no longer satisfies the current ``IndexRecord`` contract
    (schema drift — e.g. a document indexed under an earlier vector-spec) is DROPPED and logged,
    NOT allowed to fail the whole query: one stale document must not turn the entire search into
    a 500 (this mirrors the assembler dropping a single malformed card rather than sinking the
    page — the read path was previously the only place missing that per-record tolerance). Each
    drop logs the hit id and the drifted field paths (locations only — never values, so indexed
    content can't leak); the per-call drop count makes corpus drift observable and falls to zero
    once a reindex completes. A genuine store/query outage is a separate failure mode the callers
    already map to ``IndexUnavailable`` (INV-3) before this function runs."""
    scored: list[ScoredRecord] = []
    dropped = 0
    for hit in hits:
        try:
            # ``.get(...) or {}`` — a missing ``_source`` (e.g. a stored_fields/_source-disabled
            # response) would raise KeyError on subscript, which is NOT a ValidationError and
            # would escape this guard into the caller's 500. Feeding {} instead routes it through
            # the SAME drop path (empty dict fails IndexRecord validation), upholding the
            # "one bad hit must not sink the query" invariant for the malformed-hit case too.
            record = IndexRecord.model_validate(hit.get("_source") or {})
        except ValidationError as exc:
            dropped += 1
            _log.warning(
                "discovery.search dropped non-conforming index record id=%s fields=%s",
                _hit_id(hit),
                _drift_fields(exc),
            )
            continue
        scored.append((record, float(hit.get("_score") or 0.0)))
    if dropped:
        _log.warning(
            "discovery.search dropped %d/%d hit(s) failing IndexRecord validation "
            "(schema drift — reindex pending)",
            dropped,
            len(hits),
        )
    return scored


class OpenSearchVectorStoreAdapter:
    """k-NN (ANN) reader over the shared OpenSearch index (cosine; FR-2)."""

    def __init__(self, client: Any, index_name: str) -> None:
        self._client = client
        self._index = index_name

    def knn_search(
        self, vector: Sequence[float], top_k: int, abstract_only: bool = False
    ) -> list[ScoredRecord]:
        knn: dict[str, Any] = {"vector": list(vector), "k": top_k}
        if abstract_only:
            # Efficient k-NN filtering: restrict the ANN search to abstract chunks (lite scope).
            knn["filter"] = {"term": {"section": "abstract"}}
        body = {
            "size": top_k,
            "query": {"knn": {"vector": knn}},
        }
        hits = _search_hits(
            self._client, self._index, body, label="knn_search",
            message="OpenSearch k-NN query failed",
        )
        return _to_scored(hits)


class OpenSearchPaperLookupAdapter:
    """Single-document reader over the shared OpenSearch index — one record for a paper id
    (matched on ``paperId`` or display ``arxivId``). Powers the paper-detail metadata endpoint."""

    def __init__(self, client: Any, index_name: str) -> None:
        self._client = client
        self._index = index_name

    def fetch_paper(self, paper_id: str) -> IndexRecord | None:
        # Match the version-less paperId, the exact display arxivId, OR the version-stripped id
        # against paperId — so a request for one version (e.g. ...v1) still resolves a paper
        # indexed at another (...v3), instead of 404-ing on an exact-version miss. size=1: any
        # chunk carries the paper-level metadata.
        bare_id = _VERSION_SUFFIX_RE.sub("", paper_id)
        body = {
            "size": 1,
            "query": {
                "bool": {
                    "should": [
                        {"term": {"paperId": paper_id}},
                        {"term": {"paperId": bare_id}},
                        {"term": {"arxivId": paper_id}},
                    ],
                    "minimum_should_match": 1,
                }
            },
        }
        hits = _search_hits(
            self._client, self._index, body, label="paper_lookup",
            message="OpenSearch paper lookup failed",
        )
        if not hits:
            return None
        # A non-conforming stored record (schema drift) is treated like "not indexed": return
        # None → the route 404s and the detail page degrades to the arXiv id + link-out, rather
        # than 500-ing. The drop is logged (field paths only, no values) for drift visibility.
        try:
            return IndexRecord.model_validate(hits[0].get("_source") or {})
        except ValidationError as exc:
            _log.warning(
                "discovery.paper_lookup dropped non-conforming record id=%s fields=%s",
                _hit_id(hits[0]),
                _drift_fields(exc),
            )
            return None


class OpenSearchLexicalIndexAdapter:
    """BM25 reader over analyzed title, abstract, and chunk-body lexical fields (FR-2)."""

    def __init__(self, client: Any, index_name: str) -> None:
        self._client = client
        self._index = index_name

    def bm25_search(
        self,
        terms: Sequence[str],
        top_k: int,
        fields: Sequence[str] = ("title", "abstract", "lexicalTerms"),
    ) -> list[ScoredRecord]:
        body = {
            "size": top_k,
            "query": {
                "multi_match": {
                    "query": " ".join(terms),
                    "fields": list(fields),
                }
            },
        }
        hits = _search_hits(
            self._client, self._index, body, label="bm25_search",
            message="OpenSearch BM25 query failed",
        )
        return _to_scored(hits)
