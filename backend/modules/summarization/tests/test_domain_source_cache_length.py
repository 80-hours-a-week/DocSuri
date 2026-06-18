"""SourceSelector (Q1), cache key (BR-S1/INV-5), LengthRouter (Q3)."""

from __future__ import annotations

from summarization.domain.cache_key import build_cache_key
from summarization.domain.length_router import LengthRoute, LengthRouter
from summarization.domain.models import SourceKind, SummaryRequest, Task
from summarization.domain.source_selector import SourceSelector
from tests.stubs import StubFullText


def _req(task: Task, abstract: str | None = None) -> SummaryRequest:
    return SummaryRequest(paper_id="2401.00001", version=1, task=task, abstract=abstract)


def test_summary_uses_full_text() -> None:
    src = SourceSelector(StubFullText(text="full body")).select(_req(Task.SUMMARY))
    assert src is not None and src.kind == SourceKind.FULL_TEXT


def test_summary_falls_back_to_abstract() -> None:
    src = SourceSelector(StubFullText(text=None)).select(_req(Task.SUMMARY, abstract="abs"))
    assert src is not None and src.kind == SourceKind.ABSTRACT
    assert src.fallback_reason == "full_text_unavailable"


def test_summary_none_when_no_source() -> None:
    assert SourceSelector(StubFullText(text=None)).select(_req(Task.SUMMARY)) is None


def test_translate_uses_abstract() -> None:
    src = SourceSelector(StubFullText()).select(_req(Task.TRANSLATE, abstract="abs"))
    assert src is not None and src.kind == SourceKind.ABSTRACT


def test_cache_key_is_immutable_and_pathed() -> None:
    key = build_cache_key(_req(Task.SUMMARY), glossary_ver=0, model_ver="m1")
    same = build_cache_key(_req(Task.SUMMARY), glossary_ver=0, model_ver="m1")
    assert key == same  # deterministic identity (PBT-S1)
    assert key.object_path().startswith("summaries/2401.00001/v1/")
    assert key.redis_key().startswith("sum:")


def test_length_router_branches() -> None:
    router = LengthRouter(context_budget=100, input_cap=1000)
    assert router.route(50) == LengthRoute.SINGLE
    assert router.route(500) == LengthRoute.MAP_REDUCE
    assert router.route(5000) == LengthRoute.OVER_CAP
