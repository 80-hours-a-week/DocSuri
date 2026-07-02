from __future__ import annotations

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
    return NoveltyAdapters(
        corpus=build_u2_full_search_corpus_adapter(
            observability=observability,
            cost_guard=cost_guard,
        )
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
