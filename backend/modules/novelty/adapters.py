from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse
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


class ExternalApiSearchClient:
    def __init__(
        self,
        client: Any,
        *,
        github_token: str | None = None,
        per_source: int = 3,
    ) -> None:
        self._client = client
        self._github_token = github_token
        self._per_source = per_source

    def search(self, query: str) -> RetrievalBundle:
        cleaned = sanitize_external_query(query)
        items: list[dict[str, Any]] = []
        degraded: list[str] = []
        for source, search in (
            ("github", self._github_repos),
            ("huggingface", self._huggingface_datasets),
            ("zenodo", self._zenodo_records),
            ("gdelt", self._gdelt_news),
        ):
            try:
                items.extend(search(cleaned))
            except Exception:  # noqa: BLE001 - one external source must not fail the job.
                degraded.append(f"{source} external search unavailable")

        deduped = _dedupe_by_url(items)
        return RetrievalBundle(
            items=deduped,
            evidenceStatus=(
                EvidenceStatus.SUPPORTED if deduped else EvidenceStatus.ABSTAINED
            ),
            degradedReason="; ".join(degraded) or None,
        )

    def _github_repos(self, query: str) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._github_token:
            headers["Authorization"] = f"Bearer {self._github_token}"
        payload = self._json(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{query} in:name,description,readme",
                "sort": "updated",
                "order": "desc",
                "per_page": self._per_source,
            },
            headers=headers,
        )
        return [
            _external_item(
                source_type="github_repo",
                source_name="GitHub",
                title=str(repo.get("full_name") or ""),
                url=str(repo.get("html_url") or ""),
                summary=str(repo.get("description") or ""),
                identifier=str(repo.get("full_name") or ""),
                updatedAt=repo.get("updated_at"),
                stars=repo.get("stargazers_count"),
                language=repo.get("language"),
                license=((repo.get("license") or {}).get("spdx_id")),
                topics=repo.get("topics") or [],
            )
            for repo in payload.get("items", [])[: self._per_source]
        ]

    def _huggingface_datasets(self, query: str) -> list[dict[str, Any]]:
        payload = self._json(
            "https://huggingface.co/api/datasets",
            params={"search": query, "limit": self._per_source},
        )
        return [
            _external_item(
                source_type="dataset",
                source_name="Hugging Face",
                title=str(dataset.get("id") or ""),
                url=f"https://huggingface.co/datasets/{dataset.get('id')}",
                summary=_summary_from_hf_dataset(dataset),
                identifier=str(dataset.get("id") or ""),
                provider="huggingface",
                downloads=dataset.get("downloads"),
                likes=dataset.get("likes"),
                updatedAt=dataset.get("lastModified"),
                tags=dataset.get("tags") or [],
            )
            for dataset in payload[: self._per_source]
            if dataset.get("id")
        ]

    def _zenodo_records(self, query: str) -> list[dict[str, Any]]:
        payload = self._json(
            "https://zenodo.org/api/records",
            params={
                "q": f"{query} dataset",
                "type": "dataset",
                "sort": "mostrecent",
                "size": self._per_source,
            },
        )
        records = (payload.get("hits") or {}).get("hits") or []
        return [
            _external_item(
                source_type="dataset",
                source_name="Zenodo",
                title=str((record.get("metadata") or {}).get("title") or ""),
                url=str((record.get("links") or {}).get("html") or ""),
                summary=_strip_html(str((record.get("metadata") or {}).get("description") or "")),
                identifier=str(record.get("doi") or record.get("id") or ""),
                provider="zenodo",
                publishedAt=(record.get("metadata") or {}).get("publication_date"),
                keywords=(record.get("metadata") or {}).get("keywords") or [],
            )
            for record in records[: self._per_source]
        ]

    def _gdelt_news(self, query: str) -> list[dict[str, Any]]:
        payload = self._json(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": query,
                "mode": "artlist",
                "format": "json",
                "sort": "datedesc",
                "timespan": "1week",
                "maxrecords": self._per_source,
            },
        )
        return [
            _external_item(
                source_type="news",
                source_name="GDELT",
                title=str(article.get("title") or ""),
                url=str(article.get("url") or ""),
                summary=str(article.get("domain") or article.get("sourcecountry") or ""),
                identifier=str(article.get("url") or ""),
                publishedAt=article.get("seendate"),
                domain=article.get("domain"),
                language=article.get("language"),
            )
            for article in payload.get("articles", [])[: self._per_source]
        ]

    def _json(
        self,
        url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        response = self._client.get(url, params=params, headers=headers or {})
        if getattr(response, "status_code", 200) >= 400:
            raise RuntimeError("external API unavailable")
        raise_for_status = getattr(response, "raise_for_status", None)
        if raise_for_status is not None:
            raise_for_status()
        return response.json()


def _external_item(
    *,
    source_type: str,
    source_name: str,
    title: str,
    url: str,
    summary: str,
    identifier: str,
    **extra: Any,
) -> dict[str, Any]:
    if not title or not _safe_https_url(url):
        return {}
    source_ref = {
        "type": "url",
        "identifier": identifier or url,
        "title": title,
        "url": url,
        "sourceName": source_name,
    }
    return {
        "title": title,
        "summary": summary[:1000],
        "url": url,
        "sourceType": source_type,
        "sourceName": source_name,
        "evidenceStatus": EvidenceStatus.SUPPORTED.value,
        "sourceRefs": [source_ref],
        **{key: value for key, value in extra.items() if value not in (None, "", [])},
    }


def _dedupe_by_url(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(str(url))
        deduped.append(item)
    return deduped


def _safe_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.hostname)


def _summary_from_hf_dataset(dataset: dict[str, Any]) -> str:
    card = dataset.get("cardData") or {}
    description = card.get("description") if isinstance(card, dict) else None
    if description:
        return str(description)
    return ", ".join(str(tag) for tag in dataset.get("tags") or [])[:1000]


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


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
        external=build_external_adapter(),
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


def build_external_adapter() -> ExternalSearchPort:
    import httpx

    return ExternalApiSearchClient(
        httpx.Client(
            timeout=5.0,
            headers={"User-Agent": "DocSuri-Novelty/1.0"},
        ),
        github_token=os.getenv("DOCSURI_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN"),
    )
