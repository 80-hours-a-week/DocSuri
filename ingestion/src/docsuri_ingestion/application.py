from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from .config import CORPUS_SLICE_CATEGORIES
from .domain.enums import DedupDecision, FailureClass, FailureReason, JobKind
from .domain.errors import IngestionError, PermanentIngestionError
from .domain.models import EmbeddingBatch, IngestionJob, Tombstone
from .ports import (
    ArxivSourcePort,
    ClockPort,
    ControlPlaneStorePort,
    EmbeddingPort,
    FullTextStorePort,
    ObservabilityPort,
    QueuePort,
    VectorIndexPort,
    dedup_decision_applies_to_index,
)
from .processors import (
    Chunker,
    DeduplicationGuard,
    FetchParseProcessor,
    IndexRecordAssembler,
    assert_writer_embedding_role,
)
from .resilience import IngestFailureHandler, IngestionResilienceService


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class IngestionPipelineService:
    def __init__(
        self,
        *,
        arxiv: ArxivSourcePort,
        full_text_store: FullTextStorePort,
        embedding: EmbeddingPort,
        vector_index: VectorIndexPort,
        control_plane: ControlPlaneStorePort,
        observability: ObservabilityPort,
        resilience: IngestionResilienceService,
        failure_handler: IngestFailureHandler | None = None,
        chunker: Chunker | None = None,
        parser: FetchParseProcessor | None = None,
        assembler: IndexRecordAssembler | None = None,
        clock: ClockPort | None = None,
        embedding_v2: EmbeddingPort | None = None,
        vector_index_v2: VectorIndexPort | None = None,
    ) -> None:
        assert_writer_embedding_role()
        self._arxiv = arxiv
        self._full_text_store = full_text_store
        self._embedding = embedding
        self._vector_index = vector_index
        self._control_plane = control_plane
        self._observability = observability
        self._resilience = resilience
        self._failure_handler = failure_handler
        self._chunker = chunker or Chunker()
        self._parser = parser or FetchParseProcessor()
        self._assembler = assembler or IndexRecordAssembler()
        self._clock = clock or SystemClock()
        self._embedding_v2 = embedding_v2
        self._vector_index_v2 = vector_index_v2

    def ingest_one(self, job: IngestionJob) -> DedupDecision:
        if not job.arxiv_ref:
            raise PermanentIngestionError(
                "ingest_one requires arxiv_ref",
                reason=FailureReason.VALIDATION_VIOLATION,
                stage="dispatch",
            )
        self._observability.emit_log(
            {
                "type": "ingestion_job_started",
                "jobId": job.job_id,
                "kind": job.kind.value,
                "correlationId": job.correlation_id,
            }
        )
        self._control_plane.record_job_started(job)
        try:
            metadata = self._resilience.dependency_call(
                "arxiv",
                "fetch_metadata",
                lambda: self._arxiv.fetch_metadata(job.arxiv_ref or ""),
            )
            raw_document = self._resilience.dependency_call(
                "arxiv",
                "fetch_full_text",
                lambda: self._arxiv.fetch_full_text(metadata),
            )
            paper = self._parser.parse(raw_document)

            if paper.withdrawal_detected:
                return self._tombstone(job, paper)

            dedup = DeduplicationGuard(self._control_plane)
            result = dedup.evaluate(paper)
            if result.decision in {DedupDecision.DUPLICATE, DedupDecision.STALE}:
                self._observability.emit_metric(
                    "ingestion.short_circuit",
                    1.0,
                    {"decision": result.decision.value},
                )
                self._control_plane.record_job_finished(job.job_id, success=True, detail="dedup")
                return result.decision

            if not dedup_decision_applies_to_index(result.decision):
                self._control_plane.record_job_finished(job.job_id, success=True, detail="skip")
                return result.decision

            if not dedup.begin_upsert(paper):
                self._control_plane.record_job_finished(job.job_id, success=True, detail="stale")
                return DedupDecision.STALE

            object_ref = self._resilience.dependency_call(
                "s3",
                "put_full_text",
                lambda: self._full_text_store.put_full_text(paper),
            )
            paper = replace(paper, stored_full_text_ref=object_ref)
            chunks = self._chunker.chunk(paper)
            vectors = self._resilience.dependency_call(
                "bedrock",
                "embed",
                lambda: self._embedding.embed_documents(
                    [chunk.text for chunk in chunks.chunks],
                    correlation_id=job.correlation_id,
                ),
            )
            embeddings = EmbeddingBatch(
                chunk_ids=tuple(chunk.chunk_id for chunk in chunks.chunks),
                vectors=tuple(tuple(vector) for vector in vectors),
            )
            batch = self._assembler.assemble(paper, chunks, embeddings)

            self._resilience.dependency_call(
                "opensearch",
                "bulk_upsert",
                lambda: self._vector_index.bulk_upsert(batch),
            )
            self._resilience.dependency_call(
                "opensearch",
                "delete_stale_chunks",
                lambda: self._vector_index.delete_stale_chunks(
                    paper.paper_id,
                    {record.chunkId for record in batch.records},
                ),
            )
            if self._embedding_v2 and self._vector_index_v2:
                try:
                    vectors_v2 = self._resilience.dependency_call(
                        "bedrock_v2",
                        "embed",
                        lambda: self._embedding_v2.embed_documents(
                            [chunk.text for chunk in chunks.chunks],
                            correlation_id=job.correlation_id,
                        ),
                    )
                    embeddings_v2 = EmbeddingBatch(
                        chunk_ids=tuple(chunk.chunk_id for chunk in chunks.chunks),
                        vectors=tuple(tuple(vector) for vector in vectors_v2),
                    )
                    batch_v2 = self._assembler.assemble(paper, chunks, embeddings_v2)
                    self._resilience.dependency_call(
                        "opensearch_v2",
                        "bulk_upsert",
                        lambda: self._vector_index_v2.bulk_upsert(batch_v2),
                    )
                    self._resilience.dependency_call(
                        "opensearch_v2",
                        "delete_stale_chunks",
                        lambda: self._vector_index_v2.delete_stale_chunks(
                            paper.paper_id,
                            {record.chunkId for record in batch_v2.records},
                        ),
                    )
                except Exception as e:
                    self._observability.emit_log(
                        {"type": "dual_write_v2_failed", "jobId": job.job_id, "error": str(e)}
                    )
            dedup.mark_ingested(paper)
            self._control_plane.advance_watermark("arxiv", paper.updated_at)
            self._control_plane.record_job_finished(job.job_id, success=True)
            self._observability.emit_metric(
                "ingestion.paper.indexed",
                1.0,
                {"kind": job.kind.value, "chunks": str(len(batch.records))},
            )
            return result.decision
        except IngestionError as exc:
            self._control_plane.record_job_finished(
                job.job_id, success=False, detail=exc.public_error()
            )
            if self._failure_handler is not None:
                self._failure_handler.emit_failure_signal(job.job_id, exc)
                if exc.failure_class is FailureClass.PERMANENT:
                    self._failure_handler.send_to_dlq(
                        {
                            "jobId": job.job_id,
                            "kind": job.kind.value,
                            "arxivRef": job.arxiv_ref,
                            "eventId": job.event_id,
                            "correlationId": job.correlation_id,
                        },
                        reason=exc.public_error(),
                        job_id=job.job_id,
                    )
            raise

    def _tombstone(self, job: IngestionJob, paper) -> DedupDecision:
        dedup = DeduplicationGuard(self._control_plane)
        if not dedup.begin_tombstone(paper):
            self._control_plane.record_job_finished(
                job.job_id, success=True, detail="stale_tombstone"
            )
            return DedupDecision.STALE
        tombstone = Tombstone(paper_id=paper.paper_id, version=paper.version)
        self._resilience.dependency_call(
            "opensearch",
            "tombstone",
            lambda: self._vector_index.tombstone_paper(tombstone),
        )
        if self._vector_index_v2:
            try:
                self._resilience.dependency_call(
                    "opensearch_v2",
                    "tombstone",
                    lambda: self._vector_index_v2.tombstone_paper(tombstone),
                )
            except Exception as e:
                self._observability.emit_log({"type": "dual_write_v2_tombstone_failed", "error": str(e)})
        self._control_plane.advance_watermark("arxiv", paper.updated_at)
        self._control_plane.record_job_finished(job.job_id, success=True, detail="tombstoned")
        self._observability.emit_metric("ingestion.paper.tombstoned", 1.0, {"kind": job.kind.value})
        return DedupDecision.CHANGED


class RefreshOrchestrationService:
    def __init__(
        self,
        *,
        arxiv: ArxivSourcePort,
        control_plane: ControlPlaneStorePort,
        queue: QueuePort,
        observability: ObservabilityPort,
        clock: ClockPort | None = None,
    ) -> None:
        self._arxiv = arxiv
        self._control_plane = control_plane
        self._queue = queue
        self._observability = observability
        self._clock = clock or SystemClock()

    def trigger_full_rebuild(self, owner: str = "u1-worker") -> int:
        if not self._control_plane.acquire_rebuild_lock(owner):
            self._observability.emit_metric("ingestion.rebuild.rejected", 1.0, {"reason": "lock"})
            return 0
        queued = 0
        try:
            self._control_plane.reset_watermark_for_rebuild(
                "arxiv", datetime(1970, 1, 1, tzinfo=UTC)
            )
            from .config import CORPUS_END, CORPUS_START
            from .domain.models import CategoryFilter

            category_filter = CategoryFilter(
                categories=CORPUS_SLICE_CATEGORIES,
                updated_after=CORPUS_START,
                updated_before=CORPUS_END,
            )
            for metadata in self._arxiv.harvest_seed(category_filter):
                self._queue.send_job(
                    IngestionJob(
                        job_id=new_job_id("seed"),
                        kind=JobKind.SEED_REBUILD,
                        arxiv_ref=metadata.arxiv_ref,
                    )
                )
                queued += 1
            self._observability.emit_metric("ingestion.rebuild.queued", float(queued), {})
            return queued
        finally:
            self._control_plane.release_rebuild_lock(owner)

    def on_schedule_tick(self) -> int:
        if self._control_plane.is_rebuild_active():
            self._observability.emit_metric(
                "ingestion.incremental.deferred", 1.0, {"reason": "rebuild"}
            )
            return 0
        watermark = self._control_plane.get_watermark("arxiv")
        queued = 0
        for metadata in self._arxiv.fetch_incremental(
            watermark.updated_at, CORPUS_SLICE_CATEGORIES
        ):
            self._queue.send_job(
                IngestionJob(
                    job_id=new_job_id("incremental"),
                    kind=JobKind.INCREMENTAL,
                    arxiv_ref=metadata.arxiv_ref,
                )
            )
            queued += 1
        self._observability.emit_metric("ingestion.incremental.queued", float(queued), {})
        return queued

    def on_new_arxiv_event(self, event) -> bool:
        if self._control_plane.is_rebuild_active():
            self._observability.emit_metric("ingestion.event.deferred", 1.0, {"reason": "rebuild"})
            return False
        self._queue.send_job(
            IngestionJob(
                job_id=new_job_id("event"),
                kind=JobKind.EVENT,
                arxiv_ref=event.arxivRef,
                event_id=event.eventId,
                correlation_id=event.eventId,
            )
        )
        self._observability.emit_metric("ingestion.event.queued", 1.0, {})
        return True


def new_job_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"
