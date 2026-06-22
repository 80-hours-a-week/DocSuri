from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from datetime import datetime

from docsuri_ingestion.domain.enums import FailureReason
from docsuri_ingestion.domain.errors import PermanentIngestionError, RetriableIngestionError
from docsuri_ingestion.domain.models import CategoryFilter, MetadataRecord, RawDocument
from docsuri_ingestion.resilience import TokenBucket

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
OAI_NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "arxiv": "http://arxiv.org/OAI/arXiv/",
}


class ArxivHttpSource:
    def __init__(
        self,
        *,
        atom_base_url: str = "https://export.arxiv.org/api/query",
        oai_base_url: str = "https://export.arxiv.org/oai2",
        eprint_base_url: str = "https://arxiv.org/e-print",
        timeout_seconds: float = 30.0,
        rate_limiter: TokenBucket | None = None,
    ) -> None:
        self._atom_base_url = atom_base_url
        self._oai_base_url = oai_base_url
        self._eprint_base_url = eprint_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._rate_limiter = rate_limiter or TokenBucket(rate_per_second=0.33)

    def harvest_seed(self, category_filter: CategoryFilter) -> Iterable[MetadataRecord]:
        for category in category_filter.categories:
            yield from self._oai_list_records(category, category_filter)

    def fetch_incremental(
        self, since: datetime, categories: Sequence[str]
    ) -> Iterable[MetadataRecord]:
        query = "+OR+".join(f"cat:{category}" for category in categories)
        params = {
            "search_query": query,
            "sortBy": "lastUpdatedDate",
            "sortOrder": "ascending",
            "start": "0",
            "max_results": "100",
        }
        body = self._get_text(self._atom_base_url, params=params, stage="fetch_incremental")
        for record in parse_atom_feed(body):
            if record.updated_at > since:
                yield record

    def fetch_metadata(self, arxiv_ref: str) -> MetadataRecord:
        params = {"id_list": arxiv_ref, "max_results": "1"}
        body = self._get_text(self._atom_base_url, params=params, stage="fetch_metadata")
        records = parse_atom_feed(body)
        if not records:
            raise PermanentIngestionError(
                "arXiv metadata not found",
                reason=FailureReason.FETCH_FAILURE,
                stage="fetch_metadata",
            )
        return records[0]

    def fetch_full_text(self, metadata: MetadataRecord) -> RawDocument:
        identifier = metadata.identifier
        url = f"{self._eprint_base_url}/{identifier.arxiv_id}"
        body = self._get_bytes(url, params=None, stage="fetch_full_text")
        return RawDocument(
            metadata=metadata,
            text=body.decode("utf-8", errors="replace"),
            source_url=url,
            content_type="application/octet-stream",
        )

    def _oai_list_records(
        self,
        category: str,
        category_filter: CategoryFilter,
    ) -> Iterable[MetadataRecord]:
        params = {
            "verb": "ListRecords",
            "metadataPrefix": "arXiv",
            "set": category,
            "from": category_filter.updated_after.date().isoformat(),
            "until": category_filter.updated_before.date().isoformat(),
        }
        while True:
            body = self._get_text(self._oai_base_url, params=params, stage="harvest_seed")
            yield from parse_oai_records(body)
            token = parse_oai_resumption_token(body)
            if not token:
                return
            params = {"verb": "ListRecords", "resumptionToken": token}

    def _get_text(self, url: str, *, params: dict[str, str] | None, stage: str) -> str:
        return self._get_bytes(url, params=params, stage=stage).decode("utf-8", errors="replace")

    def _get_bytes(self, url: str, *, params: dict[str, str] | None, stage: str) -> bytes:
        import httpx

        self._rate_limiter.acquire()
        try:
            with httpx.Client(timeout=self._timeout_seconds, follow_redirects=True) as client:
                response = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise RetriableIngestionError(
                "arXiv request timed out",
                reason=FailureReason.TIMEOUT,
                stage=stage,
            ) from exc
        except httpx.HTTPError as exc:
            raise RetriableIngestionError(
                "arXiv request failed",
                reason=FailureReason.FETCH_FAILURE,
                stage=stage,
            ) from exc

        if response.status_code == 404:
            raise PermanentIngestionError(
                "arXiv resource not found",
                reason=FailureReason.FETCH_FAILURE,
                stage=stage,
            )
        if response.status_code == 429 or response.status_code >= 500:
            raise RetriableIngestionError(
                f"arXiv returned retriable status {response.status_code}",
                reason=FailureReason.RATE_LIMITED
                if response.status_code == 429
                else FailureReason.FETCH_FAILURE,
                stage=stage,
            )
        if response.status_code >= 400:
            raise PermanentIngestionError(
                f"arXiv returned permanent status {response.status_code}",
                reason=FailureReason.FETCH_FAILURE,
                stage=stage,
            )
        return response.content


def parse_atom_feed(body: str) -> list[MetadataRecord]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        raise PermanentIngestionError(
            f"Failed to parse XML Atom feed: {e}",
            reason=FailureReason.PARSE_FAILURE,
            stage="parse_atom_feed",
        ) from e
    records: list[MetadataRecord] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        arxiv_ref = _required_text(entry, "atom:id", ATOM_NS).rsplit("/", 1)[-1]
        title = _required_text(entry, "atom:title", ATOM_NS)
        abstract = _required_text(entry, "atom:summary", ATOM_NS)
        authors = tuple(
            author.findtext("atom:name", default="", namespaces=ATOM_NS).strip()
            for author in entry.findall("atom:author", ATOM_NS)
        )
        categories = tuple(
            node.attrib["term"]
            for node in entry.findall("atom:category", ATOM_NS)
            if node.attrib.get("term")
        )
        license_url = entry.findtext("arxiv:license", default=None, namespaces=ATOM_NS)
        records.append(
            MetadataRecord(
                arxiv_ref=arxiv_ref,
                title=title,
                authors=tuple(author for author in authors if author),
                abstract=abstract,
                categories=categories,
                updated_at=datetime.fromisoformat(_required_text(entry, "atom:updated", ATOM_NS)),
                published_at=datetime.fromisoformat(
                    _required_text(entry, "atom:published", ATOM_NS)
                ),
                license_url=license_url,
                primary_category=categories[0] if categories else None,
            )
        )
    return records


def parse_oai_records(body: str) -> list[MetadataRecord]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        raise PermanentIngestionError(
            f"Failed to parse XML OAI records: {e}",
            reason=FailureReason.PARSE_FAILURE,
            stage="parse_oai_records",
        ) from e
    records: list[MetadataRecord] = []
    for metadata in root.findall(".//oai:metadata/arxiv:arXiv", OAI_NS):
        arxiv_ref = _required_text(metadata, "arxiv:id", OAI_NS)
        categories = tuple(_required_text(metadata, "arxiv:categories", OAI_NS).split())
        created = datetime.fromisoformat(_required_text(metadata, "arxiv:created", OAI_NS))
        updated_text = metadata.findtext("arxiv:updated", default=None, namespaces=OAI_NS)
        records.append(
            MetadataRecord(
                arxiv_ref=arxiv_ref,
                title=_required_text(metadata, "arxiv:title", OAI_NS),
                authors=tuple(_required_text(metadata, "arxiv:authors", OAI_NS).split(", ")),
                abstract=_required_text(metadata, "arxiv:abstract", OAI_NS),
                categories=categories,
                updated_at=datetime.fromisoformat(updated_text) if updated_text else created,
                published_at=created,
                license_url=metadata.findtext("arxiv:license", default=None, namespaces=OAI_NS),
                primary_category=categories[0] if categories else None,
            )
        )
    return records


def parse_oai_resumption_token(body: str) -> str | None:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        raise PermanentIngestionError(
            f"Failed to parse XML OAI resumption token: {e}",
            reason=FailureReason.PARSE_FAILURE,
            stage="parse_oai_resumption_token",
        ) from e
    token = root.findtext(".//oai:resumptionToken", default="", namespaces=OAI_NS).strip()
    return token or None


def _required_text(element: ET.Element, path: str, namespaces: dict[str, str]) -> str:
    value = element.findtext(path, default="", namespaces=namespaces).strip()
    if not value:
        raise PermanentIngestionError(
            f"missing arXiv field {path}",
            reason=FailureReason.VALIDATION_VIOLATION,
            stage="parse_metadata",
        )
    return value
