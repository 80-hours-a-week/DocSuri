from __future__ import annotations

from dataclasses import dataclass

from .adapters.arxiv import ArxivHttpSource
from .adapters.aws import (
    BedrockCohereEmbeddingPort,
    OpenSearchVectorIndex,
    S3FullTextStore,
    SqsQueue,
)
from .adapters.local import (
    CapturingObservabilityHub,
    FakeArxivSource,
    FakeEmbeddingPort,
    InMemoryControlPlaneStore,
    InMemoryFullTextStore,
    InMemoryQueue,
    InMemoryVectorIndex,
    sample_metadata,
)
from .adapters.postgres import PostgresControlPlaneStore
from .application import IngestionPipelineService, RefreshOrchestrationService
from .observability import LoggingObservabilityHub
from .resilience import IngestFailureHandler, IngestionResilienceService
from .settings import IngestionSettings


@dataclass(frozen=True, slots=True)
class RuntimeServices:
    pipeline: IngestionPipelineService
    refresh: RefreshOrchestrationService
    queue: object
    observability: object


def build_local_runtime() -> RuntimeServices:
    metadata = [sample_metadata()]
    arxiv = FakeArxivSource(metadata)
    control = InMemoryControlPlaneStore()
    queue = InMemoryQueue()
    observability = CapturingObservabilityHub()
    resilience = IngestionResilienceService(observability, timeout_seconds=2.0)
    failure_handler = IngestFailureHandler(queue, observability)
    pipeline = IngestionPipelineService(
        arxiv=arxiv,
        full_text_store=InMemoryFullTextStore(),
        embedding=FakeEmbeddingPort(),
        vector_index=InMemoryVectorIndex(),
        control_plane=control,
        observability=observability,
        resilience=resilience,
        failure_handler=failure_handler,
    )
    refresh = RefreshOrchestrationService(
        arxiv=arxiv,
        control_plane=control,
        queue=queue,
        observability=observability,
    )
    return RuntimeServices(
        pipeline=pipeline, refresh=refresh, queue=queue, observability=observability
    )


def build_production_runtime(settings: IngestionSettings) -> RuntimeServices:
    settings.require_production()
    observability = LoggingObservabilityHub()
    arxiv = ArxivHttpSource(
        timeout_seconds=settings.request_timeout_seconds,
        rate_limiter=None,
    )
    control = PostgresControlPlaneStore(settings.control_plane_dsn or "")
    queue = SqsQueue(
        queue_url=settings.sqs_queue_url or "",
        dlq_url=settings.sqs_dlq_url or "",
        region_name=settings.aws_region,
    )
    resilience = IngestionResilienceService(
        observability,
        timeout_seconds=settings.request_timeout_seconds,
    )
    failure_handler = IngestFailureHandler(queue, observability)
    pipeline = IngestionPipelineService(
        arxiv=arxiv,
        full_text_store=S3FullTextStore(bucket=settings.s3_bucket or ""),
        embedding=BedrockCohereEmbeddingPort(
            model_id=settings.bedrock_model_id or "",
            region_name=settings.aws_region,
        ),
        vector_index=OpenSearchVectorIndex(
            endpoint=settings.opensearch_endpoint or "",
            index_name=settings.opensearch_index,
            stats_ttl_seconds=settings.index_stats_ttl_seconds,
        ),
        control_plane=control,
        observability=observability,
        resilience=resilience,
        failure_handler=failure_handler,
    )
    refresh = RefreshOrchestrationService(
        arxiv=arxiv,
        control_plane=control,
        queue=queue,
        observability=observability,
    )
    return RuntimeServices(
        pipeline=pipeline, refresh=refresh, queue=queue, observability=observability
    )
