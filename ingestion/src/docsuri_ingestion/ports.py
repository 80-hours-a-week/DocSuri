from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from docsuri_shared.events import NewArxivEvent

from .domain.enums import DedupDecision, JobKind
from .domain.models import (
    CategoryFilter,
    DedupResult,
    IndexRecordBatch,
    IndexStats,
    IngestionJob,
    MetadataRecord,
    ParsedPaper,
    RawDocument,
    Tombstone,
    Watermark,
)


@runtime_checkable
class ClockPort(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class ArxivSourcePort(Protocol):
    def harvest_seed(self, category_filter: CategoryFilter) -> Iterable[MetadataRecord]: ...

    def fetch_incremental(
        self, since: datetime, categories: Sequence[str]
    ) -> Iterable[MetadataRecord]: ...

    def fetch_metadata(self, arxiv_ref: str) -> MetadataRecord: ...

    def fetch_full_text(self, metadata: MetadataRecord) -> RawDocument: ...


@runtime_checkable
class FullTextStorePort(Protocol):
    def put_full_text(self, paper: ParsedPaper) -> str: ...


@runtime_checkable
class EmbeddingPort(Protocol):
    def embed_documents(
        self, texts: Sequence[str], *, correlation_id: str | None = None
    ) -> list[list[float]]: ...


@runtime_checkable
class VectorIndexPort(Protocol):
    def bulk_upsert(self, batch: IndexRecordBatch) -> None: ...

    def tombstone_paper(self, tombstone: Tombstone) -> None: ...

    def delete_stale_chunks(self, paper_id: str, keep_chunk_ids: set[str]) -> None: ...

    def index_stats(self) -> IndexStats: ...


@runtime_checkable
class ControlPlaneStorePort(Protocol):
    def get_watermark(self, name: str = "arxiv") -> Watermark: ...

    def advance_watermark(self, name: str, candidate: datetime) -> Watermark: ...

    def reset_watermark_for_rebuild(self, name: str, value: datetime) -> Watermark: ...

    def evaluate_dedup(
        self,
        paper_id: str,
        version: int,
        fingerprint: str,
    ) -> DedupResult: ...

    def try_claim_upsert(self, paper_id: str, version: int, fingerprint: str) -> bool: ...

    def mark_ingested(self, paper_id: str, version: int, fingerprint: str) -> None: ...

    def try_claim_tombstone(self, paper_id: str, version: int) -> bool: ...

    def acquire_rebuild_lock(self, owner: str) -> bool: ...

    def release_rebuild_lock(self, owner: str) -> None: ...

    def is_rebuild_active(self) -> bool: ...

    def record_job_started(self, job: IngestionJob) -> None: ...

    def record_job_finished(
        self, job_id: str, *, success: bool, detail: str | None = None
    ) -> None: ...


@runtime_checkable
class QueueMessage(Protocol):
    message_id: str
    receipt_handle: str
    body: Mapping[str, Any]


@runtime_checkable
class QueuePort(Protocol):
    def send_job(self, job: IngestionJob) -> None: ...

    def receive_messages(self, max_messages: int = 10) -> Sequence[QueueMessage]: ...

    def ack(self, message: QueueMessage) -> None: ...

    def send_to_dlq(self, payload: Mapping[str, Any], *, reason: str) -> None: ...

    def parse_new_arxiv_event(self, payload: Mapping[str, Any]) -> NewArxivEvent: ...


@runtime_checkable
class ObservabilityPort(Protocol):
    def emit_metric(
        self, name: str, value: float, tags: Mapping[str, str] | None = None
    ) -> None: ...

    def emit_log(self, entry: Mapping[str, Any]) -> None: ...

    def emit_failure_signal(self, job_id: str, *, stage: str, error: str) -> None: ...


def dedup_decision_applies_to_index(decision: DedupDecision) -> bool:
    return decision in {DedupDecision.NEW, DedupDecision.CHANGED}


def job_can_run_during_rebuild(kind: JobKind) -> bool:
    return kind is JobKind.SEED_REBUILD
