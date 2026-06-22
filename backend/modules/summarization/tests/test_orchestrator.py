"""Orchestrator — pipeline paths: cache hit, cost degrade, source unavailable, summary,
grounding-fail abstain, translate (business-logic-model.md §2)."""

from __future__ import annotations

from summarization.domain.models import (
    AbstainDTO,
    Anchor,
    AnchorTarget,
    AuthSession,
    CostDegradedDTO,
    RequestContext,
    SourceUnavailableDTO,
    SummaryDraft,
    SummaryRequest,
    Task,
)
from tests.stubs import (
    StubCostGuard,
    StubFullText,
    StubLlm,
    StubStore,
    _Budget,
    make_orchestrator,
)


def _ctx() -> RequestContext:
    return RequestContext(auth_session=AuthSession(user_id="u1"), request_id="r1")


def _req(task: Task = Task.SUMMARY, abstract: str | None = None) -> SummaryRequest:
    return SummaryRequest(paper_id="2401.1", version=1, task=task, abstract=abstract)


def test_cache_hit_skips_llm() -> None:
    store = StubStore()
    llm = StubLlm()
    orch = make_orchestrator(store=store, llm=llm)
    # First run populates the cache.
    first = orch.run(_req(), _ctx())
    assert first.to_dict()["status"] == "ok"
    # Second run is a HIT — no new put, marked cached.
    puts_after_first = store.puts
    second = orch.run(_req(), _ctx())
    assert second.to_dict()["cached"] is True
    assert store.puts == puts_after_first  # no regeneration


def test_cost_degraded_abstains_before_llm() -> None:
    orch = make_orchestrator(cost_guard=StubCostGuard(_Budget(degrade_mode="lexical-only")))
    result = orch.run(_req(), _ctx())
    assert isinstance(result, CostDegradedDTO)


def test_source_unavailable() -> None:
    orch = make_orchestrator(full_text=StubFullText(text=None))
    result = orch.run(_req(), _ctx())  # no abstract → no source
    assert isinstance(result, SourceUnavailableDTO)


def test_summary_ok_writes_through() -> None:
    store = StubStore()
    orch = make_orchestrator(store=store)
    result = orch.run(_req(), _ctx())
    assert result.to_dict()["status"] == "ok"
    assert store.puts == 1


def test_grounding_failure_abstains_after_retry() -> None:
    bad_draft = SummaryDraft(
        tldr="x", contributions=("c",), method="m", results="achieves 42.7% accuracy",
        limitations="l", reproducibility={"code": "", "data": ""},
        anchors=(Anchor("results", AnchorTarget.TABLE, span="42.7% on nowhere"),),
    )
    llm = StubLlm(draft=bad_draft)
    orch = make_orchestrator(llm=llm)
    result = orch.run(_req(), _ctx())
    assert isinstance(result, AbstainDTO)
    assert result.reason == "insufficient_grounding"
    assert llm._calls == 2  # one retry (BR-S7)


def test_llm_outage_then_recovery() -> None:
    llm = StubLlm(raise_n=1)  # first call raises, retry succeeds
    orch = make_orchestrator(llm=llm)
    result = orch.run(_req(), _ctx())
    assert result.to_dict()["status"] == "ok"


def test_translate_path() -> None:
    orch = make_orchestrator()
    result = orch.run(_req(Task.TRANSLATE, abstract="An abstract about BERT."), _ctx())
    out = result.to_dict()
    assert out["status"] == "ok"
    assert out["task"] == "translate"
    assert "translation" in out


def test_orchestrator_abstains_on_map_reduce_length() -> None:
    from summarization.domain.length_router import LengthRouter
    length_router = LengthRouter(context_budget=10, input_cap=100)
    orch = make_orchestrator()
    orch._length = length_router

    result = orch.run(_req(), _ctx())
    assert isinstance(result, AbstainDTO)
    assert result.reason == "input_too_long"
