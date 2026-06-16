from __future__ import annotations

from datetime import UTC, datetime

import pytest

from docsuri_ingestion.adapters.local import (
    FailingEmbeddingPort,
    FakeArxivSource,
    InMemoryControlPlaneStore,
    InMemoryQueue,
    InMemoryVectorIndex,
    sample_metadata,
)
from docsuri_ingestion.application import RefreshOrchestrationService
from docsuri_ingestion.domain.enums import DedupDecision, FailureReason, JobKind
from docsuri_ingestion.domain.errors import PermanentIngestionError, RetriableIngestionError
from docsuri_ingestion.domain.models import IngestionJob
from docsuri_ingestion.worker import job_from_payload

from .conftest import build_test_pipeline


def test_successful_ingestion_end_to_end_with_fake_adapters() -> None:
    pipeline, control, index, _, _ = build_test_pipeline()
    decision = pipeline.ingest_one(
        IngestionJob(job_id="job-1", kind=JobKind.EVENT, arxiv_ref="2401.00001v1")
    )
    assert decision is DedupDecision.NEW
    assert index.records
    assert control.dedup_states["2401.00001"].fingerprint
    assert control.get_watermark().updated_at == datetime(2024, 1, 1, tzinfo=UTC)


def test_duplicate_redelivery_short_circuits() -> None:
    pipeline, _, index, _, _ = build_test_pipeline()
    job = IngestionJob(job_id="job-1", kind=JobKind.EVENT, arxiv_ref="2401.00001v1")
    assert pipeline.ingest_one(job) is DedupDecision.NEW
    assert (
        pipeline.ingest_one(
            IngestionJob(job_id="job-2", kind=JobKind.EVENT, arxiv_ref="2401.00001v1")
        )
        is DedupDecision.DUPLICATE
    )
    assert index.bulk_calls == 1


def test_bulk_partial_failure_does_not_mark_ingested() -> None:
    pipeline, control, _, _, failures = build_test_pipeline(
        vector_index=InMemoryVectorIndex(fail_bulk=True)
    )
    with pytest.raises(RetriableIngestionError):
        pipeline.ingest_one(
            IngestionJob(job_id="job-1", kind=JobKind.EVENT, arxiv_ref="2401.00001v1")
        )
    state = control.dedup_states["2401.00001"]
    assert state.fingerprint is None
    assert failures.failures[-1]["stage"] == "index"


def test_bedrock_retry_recovers_after_429_like_failure() -> None:
    embedding = FailingEmbeddingPort(fail_times=1, reason=FailureReason.RATE_LIMITED)
    pipeline, _, index, _, metrics = build_test_pipeline(embedding=embedding, retry_attempts=2)
    assert (
        pipeline.ingest_one(
            IngestionJob(job_id="job-1", kind=JobKind.EVENT, arxiv_ref="2401.00001v1")
        )
        is DedupDecision.NEW
    )
    assert index.records
    assert any(name == "ingestion.retry" for name, _, _ in metrics.metrics)


class FlakyArxivSource(FakeArxivSource):
    def __init__(self):
        super().__init__([sample_metadata()])
        self.calls = 0

    def fetch_metadata(self, arxiv_ref: str):
        self.calls += 1
        if self.calls == 1:
            raise RetriableIngestionError(
                "temporary arXiv 5xx",
                reason=FailureReason.FETCH_FAILURE,
                stage="fetch_metadata",
            )
        return super().fetch_metadata(arxiv_ref)


class NotFoundArxivSource(FakeArxivSource):
    def __init__(self):
        super().__init__([sample_metadata()])

    def fetch_metadata(self, arxiv_ref: str):
        raise PermanentIngestionError(
            "arXiv 404",
            reason=FailureReason.FETCH_FAILURE,
            stage="fetch_metadata",
        )


def test_arxiv_5xx_retries_then_succeeds() -> None:
    arxiv = FlakyArxivSource()
    pipeline, _, index, _, _ = build_test_pipeline(arxiv=arxiv, retry_attempts=2)
    assert (
        pipeline.ingest_one(
            IngestionJob(job_id="job-1", kind=JobKind.EVENT, arxiv_ref="2401.00001v1")
        )
        is DedupDecision.NEW
    )
    assert arxiv.calls == 2
    assert index.records


def test_arxiv_404_permanent_failure_goes_to_dlq() -> None:
    pipeline, _, _, queue, _ = build_test_pipeline(arxiv=NotFoundArxivSource(), retry_attempts=1)
    with pytest.raises(PermanentIngestionError):
        pipeline.ingest_one(
            IngestionJob(job_id="job-1", kind=JobKind.EVENT, arxiv_ref="2401.99999v1")
        )
    assert queue.dlq[-1]["reason"] == FailureReason.FETCH_FAILURE.value


def test_poison_event_payload_becomes_permanent_error_for_dlq_boundary() -> None:
    with pytest.raises(PermanentIngestionError):
        job_from_payload({"kind": "EVENT"})


def test_rebuild_lock_defers_incremental_and_event_paths() -> None:
    control = InMemoryControlPlaneStore()
    queue = InMemoryQueue()
    observability = type(
        "Obs",
        (),
        {
            "metrics": [],
            "emit_metric": lambda self, name, value, tags=None: self.metrics.append(
                (name, value, tags or {})
            ),
            "emit_log": lambda self, entry: None,
            "emit_failure_signal": lambda self, job_id, stage, error: None,
        },
    )()
    service = RefreshOrchestrationService(
        arxiv=FakeArxivSource([sample_metadata()]),
        control_plane=control,
        queue=queue,
        observability=observability,
    )
    assert control.acquire_rebuild_lock("test")
    assert service.on_schedule_tick() == 0
    assert not service.on_new_arxiv_event(
        type("Event", (), {"eventId": "e1", "arxivRef": "2401.00001v1"})()
    )
    assert not queue.jobs
