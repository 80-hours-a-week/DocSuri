"""real_wiring — assemble the orchestrator from real adapters (TD-S12, real-first).

The single shipped wiring: Bedrock LLM + S3/Redis store + S3 full-text + RDS glossary,
with the U6 cost-guard / observability hubs injected (single authority). No mock wiring
ships; tests build the orchestrator directly with Fixtures/Stubs.
"""

from __future__ import annotations

from dataclasses import dataclass

from docsuri_shared.ports import CostGuardCircuitBreaker, ObservabilityHub

from .adapters.bedrock_llm import BedrockLlmGateway
from .adapters.rds_glossary import RdsGlossaryRepository
from .adapters.s3_full_text import S3FullTextSource
from .adapters.s3_redis_store import S3RedisSummaryStore
from .adapters.settings import SummarizationSettings
from .domain.assembler import ResultAssembler
from .domain.glossary import GlossaryResolver
from .domain.grounding import GroundingValidator
from .domain.length_router import LengthRouter
from .domain.refiner import InputRefiner
from .domain.source_selector import SourceSelector
from .service.orchestrator import SummarizationOrchestrationService


@dataclass(frozen=True, slots=True)
class SummarizationBundle:
    orchestrator: SummarizationOrchestrationService
    settings: SummarizationSettings


from typing import Callable


def build_real_orchestrator(
    settings: SummarizationSettings,
    *,
    cost_guard: CostGuardCircuitBreaker,
    observability: ObservabilityHub,
    abstract_lookup: Callable[[str], str | None] | None = None,
) -> SummarizationBundle:
    assert settings.s3_bucket is not None  # noqa: S101 — gated by summarization_enabled

    llm = BedrockLlmGateway(
        summary_model_id=settings.summary_model_id,
        translate_model_id=settings.translate_model_id,
        region_name=settings.region_name,
    )
    store = S3RedisSummaryStore(
        bucket=settings.s3_bucket,
        ttl_seconds=settings.redis_ttl_seconds,
        region_name=settings.region_name,
        redis_url=settings.redis_url,
    )
    full_text = S3FullTextSource(bucket=settings.s3_bucket, region_name=settings.region_name)
    glossary_repo = RdsGlossaryRepository(dsn=settings.database_url)

    orchestrator = SummarizationOrchestrationService(
        store=store,
        source_selector=SourceSelector(full_text, abstract_lookup=abstract_lookup),
        refiner=InputRefiner(),
        glossary_resolver=GlossaryResolver(glossary_repo),
        length_router=LengthRouter(),
        llm=llm,
        grounding=GroundingValidator(),
        assembler=ResultAssembler(),
        cost_guard=cost_guard,
        observability=observability,
        model_ver=settings.model_ver,
    )
    return SummarizationBundle(orchestrator=orchestrator, settings=settings)
