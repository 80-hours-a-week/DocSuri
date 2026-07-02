from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from .models import EvidenceStatus
from .security import sanitize_external_query


@dataclass(frozen=True)
class RetrievalBundle:
    items: list[dict[str, Any]] = field(default_factory=list)
    evidenceStatus: EvidenceStatus = EvidenceStatus.ABSTAINED
    degradedReason: str | None = None


class CorpusRetrievalPort(Protocol):
    def full_search(self, owner_id: str, query: str) -> RetrievalBundle: ...


class ExternalSearchPort(Protocol):
    def search(self, query: str) -> RetrievalBundle: ...


class SimilarityPort(Protocol):
    def check(self, owner_id: str, manuscript_ref: dict[str, Any]) -> RetrievalBundle: ...


class NotionExportPort(Protocol):
    def export(self, owner_id: str, preview: dict[str, Any]) -> str: ...


class NoopCorpusRetrievalClient:
    def full_search(self, owner_id: str, query: str) -> RetrievalBundle:
        return RetrievalBundle(
            items=[],
            degradedReason=(
                f"U2 full search adapter not configured for {sanitize_external_query(query)}"
            ),
        )


class U2FullSearchCorpusRetrievalClient:
    def __init__(self, orchestrator: Any, grounding_hook: Any) -> None:
        self._orchestrator = orchestrator
        self._grounding_hook = grounding_hook

    def full_search(self, owner_id: str, query: str) -> RetrievalBundle:
        from discovery.api.gateway_seam import run_search
        from discovery.domain.models import AuthSession, RequestContext
        from discovery.service.orchestrator import SearchUnavailable
        from docsuri_shared.dtos import (
            AbstainDTO,
            DegradedResultDTO,
            SearchRequest,
            SearchResultPageDTO,
            ValidationErrorDTO,
        )

        ctx = RequestContext(
            auth_session=AuthSession(user_id=owner_id),
            request_id=f"novelty-{uuid4().hex}",
        )
        try:
            response = run_search(
                self._orchestrator,
                self._grounding_hook,
                SearchRequest(query=query, scope="full"),
                ctx,
            )
        except SearchUnavailable:
            return RetrievalBundle(degradedReason="U2 full search unavailable")

        root = response.root
        if isinstance(root, (SearchResultPageDTO, DegradedResultDTO)):
            items = [_card_item(card) for card in root.cards]
            degraded = getattr(root.meta, "degraded", False)
            mode = getattr(getattr(root, "mode", None), "root", None)
            return RetrievalBundle(
                items=items,
                evidenceStatus=(
                    EvidenceStatus.SUPPORTED if items else EvidenceStatus.ABSTAINED
                ),
                degradedReason=(
                    f"U2 full search returned degraded results: {mode or 'partial'}"
                    if degraded
                    else None
                ),
            )
        if isinstance(root, AbstainDTO):
            return RetrievalBundle(degradedReason=f"U2 full search abstained: {root.reason}")
        if isinstance(root, ValidationErrorDTO):
            return RetrievalBundle(degradedReason=f"U2 full search rejected query: {root.message}")
        return RetrievalBundle(degradedReason="U2 full search returned an unsupported response")


def _card_item(card: Any) -> dict[str, Any]:
    url = card.sourceUrl or card.arxivUrl
    source_name = card.sourceName or "arXiv"
    source_ref = {
        "type": "url",
        "identifier": card.arxivId,
        "title": card.title,
        "url": url,
        "sourceName": source_name,
    }
    return {
        "title": card.title,
        "authors": card.authors,
        "year": card.year,
        "abstractSnippet": card.abstractSnippet,
        "arxivId": card.arxivId,
        "sourceName": source_name,
        "sourceUrl": url,
        "evidenceStatus": EvidenceStatus.SUPPORTED.value,
        "sourceRefs": [source_ref],
    }


class NoopExternalSearchClient:
    def search(self, query: str) -> RetrievalBundle:
        return RetrievalBundle(
            items=[],
            degradedReason=(
                f"external browser adapter not configured for {sanitize_external_query(query)}"
            ),
        )


class NoopSimilarityClient:
    def check(self, owner_id: str, manuscript_ref: dict[str, Any]) -> RetrievalBundle:
        return RetrievalBundle(items=[], degradedReason="similarity adapter not configured")


class S3ManuscriptSimilarityClient:
    def __init__(
        self,
        *,
        bucket: str,
        corpus: CorpusRetrievalPort,
        client: Any,
        prefix: str = "novelty/",
    ) -> None:
        self._bucket = bucket
        self._corpus = corpus
        self._client = client
        self._prefix = prefix

    def check(self, owner_id: str, manuscript_ref: dict[str, Any]) -> RetrievalBundle:
        object_key = str(manuscript_ref.get("objectKey") or "")
        content_type = str(manuscript_ref.get("contentType") or "").lower()
        if not object_key:
            return RetrievalBundle(degradedReason="manuscript objectKey is required")
        if not object_key.startswith(self._prefix):
            return RetrievalBundle(degradedReason="manuscript objectKey is outside novelty prefix")
        if content_type not in {"text/plain", "text/markdown"}:
            return RetrievalBundle(
                degradedReason=f"similarity text extraction not configured for {content_type}"
            )

        text = self._read_text(object_key)
        sentences = _candidate_sentences(text)
        items = _ai_style_items(text)
        for sentence in sentences[:3]:
            bundle = self._corpus.full_search(owner_id, sentence[:500])
            match = _best_supported_match(bundle.items)
            if match is not None:
                items.append(_similarity_item(sentence, match))

        supported = any(
            item.get("evidenceStatus") == EvidenceStatus.SUPPORTED.value for item in items
        )
        return RetrievalBundle(
            items=items,
            evidenceStatus=EvidenceStatus.SUPPORTED if supported else EvidenceStatus.ABSTAINED,
        )

    def _read_text(self, object_key: str) -> str:
        # ponytail: first 256 KiB is enough for a fast risk signal; stream extraction if needed.
        response = self._client.get_object(
            Bucket=self._bucket,
            Key=object_key,
            Range="bytes=0-262143",
        )
        return response["Body"].read().decode("utf-8", errors="replace")


def _candidate_sentences(text: str) -> list[str]:
    sentences = [
        re.sub(r"\s+", " ", part).strip()
        for part in re.split(r"(?<=[.!?。！？])\s+", text)
    ]
    return sorted(
        [sentence for sentence in sentences if len(sentence) >= 80],
        key=len,
        reverse=True,
    )


def _best_supported_match(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        refs = item.get("sourceRefs") or item.get("source_refs") or []
        if refs:
            return item
    return None


def _similarity_item(sentence: str, match: dict[str, Any]) -> dict[str, Any]:
    refs = match.get("sourceRefs") or match.get("source_refs") or []
    return {
        "title": f"Potential overlap with {match.get('title') or 'corpus result'}",
        "riskType": "sentence_similarity",
        "sentence": sentence[:500],
        "matchedTitle": match.get("title"),
        "evidenceStatus": EvidenceStatus.SUPPORTED.value,
        "sourceRefs": refs,
    }


def _ai_style_items(text: str) -> list[dict[str, Any]]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) < 400:
        return []
    markers = (
        "delve",
        "underscore",
        "pivotal",
        "landscape",
        "robust framework",
        "comprehensive analysis",
    )
    hits = [marker for marker in markers if marker in normalized.lower()]
    if not hits:
        return []
    return [
        {
            "title": "AI-style phrasing risk",
            "riskType": "ai_style",
            "markers": hits[:5],
            "evidenceStatus": EvidenceStatus.ABSTAINED.value,
            "sourceRefs": [],
        }
    ]


class NoopNotionExportClient:
    def export(self, owner_id: str, preview: dict[str, Any]) -> str:
        raise RuntimeError("Notion export adapter is not configured")


@dataclass(frozen=True)
class NoveltyAdapters:
    corpus: CorpusRetrievalPort = field(default_factory=NoopCorpusRetrievalClient)
    external: ExternalSearchPort = field(default_factory=NoopExternalSearchClient)
    similarity: SimilarityPort = field(default_factory=NoopSimilarityClient)
    notion: NotionExportPort = field(default_factory=NoopNotionExportClient)


def build_default_novelty_adapters(observability=None, cost_guard=None) -> NoveltyAdapters:
    corpus = build_u2_full_search_corpus_adapter(
        observability=observability,
        cost_guard=cost_guard,
    )
    return NoveltyAdapters(
        corpus=corpus,
        similarity=build_similarity_adapter(corpus),
    )


def build_u2_full_search_corpus_adapter(observability=None, cost_guard=None) -> CorpusRetrievalPort:
    try:
        from discovery.adapters.settings import DiscoverySettings
    except ModuleNotFoundError:
        return NoopCorpusRetrievalClient()

    settings = DiscoverySettings.from_env()
    if not settings.search_enabled:
        return NoopCorpusRetrievalClient()

    from discovery.real_wiring import build_real_orchestrator
    from docsuri_ops.grounding import GroundingEnforcementHook

    bundle = build_real_orchestrator(
        settings,
        observability=observability,
        cost_guard=cost_guard,
    )
    return U2FullSearchCorpusRetrievalClient(bundle.orchestrator, GroundingEnforcementHook())


def build_similarity_adapter(corpus: CorpusRetrievalPort) -> SimilarityPort:
    bucket = os.getenv("DOCSURI_NOVELTY_ARTIFACT_BUCKET")
    if not bucket:
        return NoopSimilarityClient()

    import boto3

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    return S3ManuscriptSimilarityClient(
        bucket=bucket,
        corpus=corpus,
        client=boto3.client("s3", region_name=region),
        prefix=os.getenv("DOCSURI_NOVELTY_ARTIFACT_PREFIX", "novelty/"),
    )
