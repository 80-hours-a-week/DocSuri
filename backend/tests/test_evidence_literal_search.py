from __future__ import annotations

from docsuri_shared._generated.dtos.evidence_schema import EvidenceRequest

from backend.modules.evidence.assembler import EvidenceComparisonAssembler
from backend.modules.evidence.models import (
    AgentRunContext,
    EvidenceSession,
    EvidenceTurn,
    LiteralMatch,
    LiteralSearchResult,
    TurnAbstainResult,
    TurnSuccessResult,
)
from backend.modules.evidence.orchestrator import EvidenceAgentOrchestrator
from backend.modules.evidence.tools import PaperSearchUnavailable


def _ctx(topic: str, prior_paper_ids: tuple[str, ...] = ()) -> tuple[AgentRunContext, EvidenceRequest]:
    request = EvidenceRequest(topic=topic, scope='auto', paperIds=[])
    session = EvidenceSession(owner_id='owner-1')
    turn = EvidenceTurn(session_id=session.session_id, request=request)
    ctx = AgentRunContext(
        session=session,
        current_turn=turn,
        owner_id='owner-1',
        request_id='req-1',
        budget_signal={'state': 'ok'},
        prior_paper_ids=prior_paper_ids,
    )
    return ctx, request


class _NoToolAllowed:
    """비교 경로(DocModel/LLM)로는 절대 못 들어간다 — 속성 접근 자체가 실패."""

    def __getattr__(self, name: str):
        raise AssertionError(f'literal path must not touch comparison tools ({name})')


class _StubLiteralSearch:
    def __init__(self, result: LiteralSearchResult) -> None:
        self._result = result
        self.calls: list[tuple[str, tuple[str, ...] | None]] = []

    def literal_search(self, phrase: str, paper_ids=None):
        self.calls.append((phrase, tuple(paper_ids) if paper_ids else None))
        return self._result


def _orchestrator(search_tool) -> EvidenceAgentOrchestrator:
    return EvidenceAgentOrchestrator(
        search_tool=search_tool,
        doc_model_tool=_NoToolAllowed(),
        extractor=_NoToolAllowed(),
        assembler=EvidenceComparisonAssembler(),
    )


def test_literal_quote_topic_bypasses_llm_and_returns_matches() -> None:
    topic = '"self-attention reduces computation" 라는 문장이 있는 논문 찾아줘'
    result = LiteralSearchResult(
        phrase='self-attention reduces computation',
        matches=(
            LiteralMatch(paper_id='2001.00001', anchor='s3.p2', quote='... self-attention reduces computation ...'),
            LiteralMatch(paper_id='2001.00002', anchor='s2.p1', quote='... self-attention reduces computation ...'),
        ),
    )
    search = _StubLiteralSearch(result)
    ctx, request = _ctx(topic)

    outcome = _orchestrator(search).run(ctx, request)

    assert isinstance(outcome, TurnSuccessResult)
    assert outcome.resolved_paper_ids == ('2001.00001', '2001.00002')
    assert outcome.outcome.claims[0].supporting[0].paperId == '2001.00001'
    assert outcome.outcome.claims[0].supporting[0].anchor == 's3.p2'
    assert outcome.outcome.answer is not None
    assert '2001.00001' in outcome.outcome.answer


def test_literal_quote_topic_abstains_when_no_matches() -> None:
    topic = '"완전히 없는 문장입니다" 라는 문장이 있는 논문 찾아줘'
    search = _StubLiteralSearch(LiteralSearchResult(phrase='완전히 없는 문장입니다', matches=()))
    ctx, request = _ctx(topic)

    outcome = _orchestrator(search).run(ctx, request)

    assert isinstance(outcome, TurnAbstainResult)
    assert outcome.outcome.abstainReason == 'out_of_corpus'


def test_literal_quote_topic_abstains_when_index_unavailable() -> None:
    class _Failing:
        def literal_search(self, phrase, paper_ids=None):
            raise PaperSearchUnavailable('down')

    topic = '"anything" 라는 문장이 있는 논문 찾아줘'
    ctx, request = _ctx(topic)

    outcome = _orchestrator(_Failing()).run(ctx, request)

    assert isinstance(outcome, TurnAbstainResult)
    assert outcome.outcome.abstainReason == 'out_of_corpus'


def test_followup_narrowing_restricts_literal_search_to_prior_papers() -> None:
    topic = '그 중에서 "self-attention" 문장이 있는 논문만 다시 보여줘'
    result = LiteralSearchResult(
        phrase='self-attention',
        matches=(LiteralMatch(paper_id='2001.00001', anchor='s3.p2', quote='... self-attention ...'),),
    )
    search = _StubLiteralSearch(result)
    ctx, request = _ctx(topic, prior_paper_ids=('2001.00001', '2001.00002'))

    _orchestrator(search).run(ctx, request)

    assert search.calls == [('self-attention', ('2001.00001', '2001.00002'))]


def test_assemble_literal_answer_lists_papers() -> None:
    result = LiteralSearchResult(
        phrase='self-attention reduces computation',
        matches=(
            LiteralMatch(paper_id='2001.00001', anchor='s3.p2', quote='q1'),
            LiteralMatch(paper_id='2001.00002', anchor=None, quote='q2'),
        ),
    )
    outcome = EvidenceComparisonAssembler().assemble_literal(result)

    assert outcome.coverage.paperCount == 2
    assert outcome.answer is not None
    assert '2편' in outcome.answer
