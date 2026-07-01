from __future__ import annotations

import logging

from docsuri_shared._generated.dtos.docmodel_schema import DocModel
from docsuri_shared._generated.dtos.evidence_schema import (
    EvidenceAbstainResult,
    EvidenceRequest,
    EvidenceResult,
    EvidenceScope,
)

from .assembler import EvidenceComparisonAssembler
from .extractor import EvidenceExtractor, LlmUnavailable
from .models import (
    AgentRunContext,
    TurnAbstainResult,
    TurnErrorResult,
    TurnResult,
    TurnSuccessResult,
)
from .tools import EvidenceDocModelTool, EvidencePaperSearchTool, PaperSearchUnavailable

logger = logging.getLogger(__name__)

_ABSTAIN_NO_CORPUS = 'out_of_corpus'
_ABSTAIN_INSUFFICIENT = 'insufficient_evidence'
_ABSTAIN_LLM_FAILURE = 'llm_unavailable'


class EvidenceAgentOrchestrator:
    """Tool 자율 오케스트레이션 — Search→DocModel→Extract→Assemble."""

    def __init__(
        self,
        *,
        search_tool: EvidencePaperSearchTool,
        doc_model_tool: EvidenceDocModelTool,
        extractor: EvidenceExtractor,
        assembler: EvidenceComparisonAssembler,
    ) -> None:
        self._search = search_tool
        self._doc_model = doc_model_tool
        self._extractor = extractor
        self._assembler = assembler

    def run(self, ctx: AgentRunContext, request: EvidenceRequest) -> TurnResult:
        # --- 1. 비용 게이트 확인(BR-EV-7) ---
        budget_state = ctx.budget_signal.get('state', 'ok')
        if budget_state != 'ok':
            return TurnErrorResult(error_code='cost_degraded')

        # --- 2. 논문 검색(BR-EV-2 scope 분기) ---
        scope = EvidenceScope(request.scope) if request.scope else EvidenceScope.auto
        paper_ids: list[str] = list(request.paperIds or [])

        try:
            search_result = self._search.search(
                topic=request.topic,
                scope=scope,
                paper_ids=paper_ids,
            )
        except PaperSearchUnavailable:
            logger.warning('paper search unavailable — abstaining')
            return TurnAbstainResult(
                outcome=EvidenceAbstainResult(
                    state='abstain',
                    abstainReason=_ABSTAIN_NO_CORPUS,
                )
            )

        if not search_result.records:
            return TurnAbstainResult(
                outcome=EvidenceAbstainResult(
                    state='abstain',
                    abstainReason=_ABSTAIN_NO_CORPUS,
                )
            )

        # --- 3. DocModel 로드 ---
        doc_models: list[tuple[str, DocModel]] = []
        for record in search_result.records:
            paper_id = _get_paper_id(record)
            if not paper_id:
                continue
            doc_model = self._doc_model.get_doc_model(paper_id)
            if doc_model is not None:
                doc_models.append((paper_id, doc_model))

        if not doc_models:
            return TurnAbstainResult(
                outcome=EvidenceAbstainResult(
                    state='abstain',
                    abstainReason=_ABSTAIN_NO_CORPUS,
                )
            )

        # --- 4. LLM 추출 (INV-EV-3 날조 금지 extractor 내부 강제) ---
        try:
            items = self._extractor.extract(topic=request.topic, doc_models=doc_models)
        except LlmUnavailable:
            logger.warning('LLM unavailable during evidence extraction — fail-closed(BR-EV-12)')
            return TurnAbstainResult(
                outcome=EvidenceAbstainResult(
                    state='abstain',
                    abstainReason=_ABSTAIN_LLM_FAILURE,
                )
            )

        # INV-EV-2 — 빈 성공 금지
        if not items:
            return TurnAbstainResult(
                outcome=EvidenceAbstainResult(
                    state='abstain',
                    abstainReason=_ABSTAIN_INSUFFICIENT,
                )
            )

        # --- 5. 비교표 조립(BR-EV-5) ---
        result: EvidenceResult = self._assembler.assemble(
            items=items,
            search_result=search_result,
            paper_count=len(doc_models),
        )
        return TurnSuccessResult(outcome=result)


def _get_paper_id(record: object) -> str | None:
    """IndexRecord 또는 ScoredRecord에서 arxivId 추출 (INV-EV-5: 점수 미노출)."""
    for attr in ('arxivId', 'paper_id', 'paperId', 'id'):
        val = getattr(record, attr, None)
        if val:
            return str(val)
    return None
