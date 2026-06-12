"""U4 Trace 검증 — TRACE-01a(데이터·캐시·폴백·분기 로직) + TRACE-02.

출처: unit-u4-trace.md §6 (백엔드 범위 — UI 항목은 U4-UI 후속 라운드,
u4_build_plan.md C2·C3 결정).
"""

from __future__ import annotations

from docsuri.u0.adapters.mock import FixtureCitation, InMemoryTtlCache, ListTelemetry
from docsuri.u0.config import load_settings
from docsuri.u0.ports import OneHopResult, PaperHit
from docsuri.u4.service import CitationFetcher, FormFactorRouter, TopInfluenceSelector, build_view
from docsuri.u4.views import MAX_NODES


def _make_fetcher(fake_clock, citation=None):
    settings = load_settings()
    return CitationFetcher(
        citation=citation or FixtureCitation(settings.corpus_path),
        cache=InMemoryTtlCache(clock=fake_clock),
        telemetry=ListTelemetry(),
        clock=fake_clock,
    )


def _paper(i: int, citations: int) -> PaperHit:
    return PaperHit(
        id=f"p{i}", title=f"paper {i}", authors=["a"], year=2025, citations=citations
    )


def test_trace01a_one_hop_structure(u0, fake_clock):
    center = u0.embedding.search(u0.embedding.embed("ai", lang="en"), k=1)[0]
    result = _make_fetcher(fake_clock).fetch(center.id)
    assert result.outgoing and result.incoming  # 인용·피인용 양방향
    assert all(h.id != center.id for h in result.outgoing + result.incoming)


def test_trace01a_cache_hit_then_expiry(fake_clock):
    fetcher = _make_fetcher(fake_clock)
    telemetry = fetcher._telemetry
    fetcher.fetch("2401.00001")
    fetcher.fetch("2401.00001")
    assert [e["cache_hit"] for e in telemetry.events] == [False, True]  # 24h 재사용
    fake_clock.advance(25 * 3600)  # TTL 만료 + 시간 윈도우 회전 (U4 §5)
    fetcher.fetch("2401.00001")
    assert telemetry.events[-1]["cache_hit"] is False


def test_trace01a_fallback_passthrough(fake_clock):
    class EmptyCitation:  # U0 폴백 의미론(R4) — 빈 상태는 UI가 안내(NFR-NET-03)
        def one_hop(self, paper_id: str) -> OneHopResult:
            return OneHopResult(outgoing=[], incoming=[])

    result = _make_fetcher(fake_clock, citation=EmptyCitation()).fetch("any")
    assert result.outgoing == [] and result.incoming == []
    view = build_view(_paper(0, 1), result, render="list")
    assert view.outgoing == []  # 빈 상태로도 뷰 조립은 성립


def test_render_branch_form_factor():
    router = FormFactorRouter()
    assert router.route(1280, "pro") == "graph"  # 데스크톱 전문
    assert router.route(360, "pro") == "list"  # <768px — NFR-MOBILE-05
    assert router.route(1280, "undergrad") == "list"  # TRACE-02 그래프 미표시
    assert router.route(768, "pro") == "graph"  # 경계값: 768은 태블릿(그래프)


def test_trace02_top3_by_citations():
    incoming = [_paper(1, 10), _paper(2, 500), _paper(3, 50), _paper(4, 300)]
    top = TopInfluenceSelector().top3(incoming)
    assert [h.citations for h in top] == [500, 300, 50]  # 피인용 내림차순, 정확히 3건


def test_graph_view_caps_at_30_nodes():
    one_hop = OneHopResult(
        outgoing=[_paper(i, i) for i in range(40)],
        incoming=[_paper(100 + i, 1000 + i) for i in range(40)],
    )
    view = build_view(_paper(999, 1), one_hop, render="graph")
    assert 1 + len(view.outgoing) + len(view.incoming) <= MAX_NODES  # TRACE-01 AC
    assert len(view.incoming) > len(view.outgoing)  # 인용수 가중 절단 (incoming이 高인용)

    listed = build_view(_paper(999, 1), one_hop, render="list")
    assert len(listed.outgoing) == 40  # 리스트 모드는 절단 없음 — 검색창 필터 몫
