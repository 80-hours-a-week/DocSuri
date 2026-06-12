"""어댑터 팩토리 — DOCSURI_ADAPTER_MODE(mock|aws)로 U0 포트 묶음을 조립한다.

조립 구조는 component-model §2를 따른다: LlmPort는 항상 CostGuard·Telemetry를
내장한 게이트웨이로 감싸서 노출한다 (ADR-D4 결과 — 하드 거부 정책).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..cost_guard import CostGuard, InMemoryCostStore
from ..llm_gateway import LlmGateway
from ..ports import (
    CachePort,
    CitationApi,
    EmbeddingPort,
    Glossary,
    SessionPort,
    Telemetry,
)


@dataclass(frozen=True)
class U0Ports:
    embedding: EmbeddingPort
    llm: LlmGateway
    cache: CachePort
    session: SessionPort
    telemetry: Telemetry
    glossary: Glossary
    citation: CitationApi
    cost_guard: CostGuard


def build_u0(settings: Settings) -> U0Ports:
    if settings.adapter_mode == "aws":
        return _build_aws(settings)
    return _build_mock(settings)


def _build_mock(settings: Settings) -> U0Ports:
    from . import mock

    telemetry = mock.ListTelemetry(echo=False)
    guard = CostGuard(
        store=InMemoryCostStore(),
        monthly_cap_usd=settings.cost_monthly_cap_usd,
        price_in_per_mtok=settings.llm_price_in_per_mtok,
        price_out_per_mtok=settings.llm_price_out_per_mtok,
    )
    return U0Ports(
        embedding=mock.DeterministicEmbedding(settings.corpus_path),
        llm=LlmGateway(mock.CannedKoreanLlm(), guard, telemetry),
        cache=mock.InMemoryTtlCache(),
        session=mock.AnonymousSession(persona_mode=settings.default_persona),
        telemetry=telemetry,
        glossary=mock.FixtureGlossary(settings.glossary_path),
        citation=mock.FixtureCitation(settings.corpus_path),
        cost_guard=guard,
    )


def _build_aws(settings: Settings) -> U0Ports:
    from . import aws, mock

    telemetry = aws.EmfTelemetry()
    guard = CostGuard(
        store=aws.DynamoCostStore(settings),
        monthly_cap_usd=settings.cost_monthly_cap_usd,
        price_in_per_mtok=settings.llm_price_in_per_mtok,
        price_out_per_mtok=settings.llm_price_out_per_mtok,
    )
    cache = aws.DynamoCache(settings)
    return U0Ports(
        embedding=aws.BedrockEmbedding(settings),
        llm=LlmGateway(aws.BedrockLlm(settings), guard, telemetry),
        cache=cache,
        # 익명 세션은 서버 무상태 (ADR §12) — aws 모드에서도 동일 mock 구현 사용
        session=mock.AnonymousSession(persona_mode=settings.default_persona),
        telemetry=telemetry,
        glossary=aws.DynamoGlossary(settings),
        # 데모 스코프: 코퍼스 시드가 합성 arXiv ID(2606.xxxxx, 미래 날짜)라 Semantic
        # Scholar에 존재하지 않아 1-hop 조회가 항상 404→빈 그래프가 된다. 외부 API
        # 의존을 끊고 코퍼스 기반 결정적 fixture로 인용 흐름을 구성한다(frontend
        # buildMockCitations와 동일 정책). 실데이터 연동(실 arXiv ID 코퍼스 +
        # SemanticScholarCitation 재배선)은 후속 라운드 — 클래스·직접 테스트는 보존.
        citation=mock.FixtureCitation(settings.corpus_path),
        cost_guard=guard,
    )
