"""U4 Trace 컴포넌트 — component-model §6 (CitationFetcher · FormFactorRouter ·
TopInfluenceSelector · 뷰 조립).

범위: 백엔드 (TRACE-01a — 데이터 확보·캐시·폴백·분기 로직).
그래프/리스트 렌더(TRACE-01b)는 U4-UI 후속 라운드 (u4_build_plan.md C2·C3).
금지: 다단계 인용 트리 (U4 §8) — oneHop 단일 호출만.
"""

from __future__ import annotations

import time
from typing import Callable

from ..u0.ports import (
    CachePort,
    CitationApi,
    OneHopResult,
    PaperHit,
    Persona,
    Telemetry,
    TelemetryEvent,
)
from .views import MAX_NODES, CitationView, RenderMode

API_VERSION = "v1"
TTL_S = 24 * 3600  # NFR-DATA-03: 인용 캐시 24h


class CitationFetcher:
    """1-hop 인용 데이터 확보 — 캐시 우선(키: cite:{id}:{api_ver}:{window}, U4 §5)."""

    def __init__(
        self,
        citation: CitationApi,
        cache: CachePort,
        telemetry: Telemetry,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._citation = citation
        self._cache = cache
        self._telemetry = telemetry
        self._clock = clock

    def _cache_key(self, paper_id: str) -> str:
        # 일 단위 시간 윈도우 (U4 §5) — 트레이드오프(U4-L1): UTC 자정에 키가
        # 회전하므로 자정 직전 캐시 항목의 실효 수명은 TTL(24h)보다 짧을 수
        # 있다. 설계 의도(버전·윈도우 단위 회전)와 단순성을 우선한 선택.
        window = int(self._clock() // 86_400)
        return f"cite:{paper_id}:{API_VERSION}:{window}"

    def fetch(self, paper_id: str) -> OneHopResult:
        started = self._clock()
        key = self._cache_key(paper_id)
        cached = self._cache.get(key)
        if cached is not None:
            result = OneHopResult.model_validate_json(cached)
            self._record(started, cache_hit=True)
            return result
        result = self._citation.one_hop(paper_id)
        self._cache.set(key, result.model_dump_json().encode(), TTL_S)
        self._record(started, cache_hit=False)
        return result

    def _record(self, started: float, cache_hit: bool) -> None:
        self._telemetry.record(
            TelemetryEvent(
                op="citation_fetch",
                latency_ms=round((self._clock() - started) * 1000, 3),
                cache_hit=cache_hit,
            )
        )


class FormFactorRouter:
    """렌더 모드 분기의 단일 결정 — NFR-MOBILE-05(<768px 리스트) + TRACE-02(학부 모드 그래프 미표시)."""

    BREAKPOINT_PX = 768  # NFR-MOBILE-01 태블릿 경계

    def route(self, viewport_width: int, persona_mode: Persona) -> RenderMode:
        if viewport_width < self.BREAKPOINT_PX or persona_mode == "undergrad":
            return "list"
        return "graph"


class TopInfluenceSelector:
    """피인용 가중 Top-3 — TRACE-02 (그래프 대신 카드 리스트)."""

    TOP_N = 3

    def top3(self, incoming: list[PaperHit]) -> list[PaperHit]:
        return sorted(incoming, key=lambda hit: hit.citations, reverse=True)[: self.TOP_N]


def build_view(center: PaperHit, one_hop: OneHopResult, render: RenderMode) -> CitationView:
    """CitationView 조립 — 그래프 모드는 center 포함 ≤30 노드로 인용수 가중 절단.

    중심 논문 메타는 호출자(U1 SearchResult 카드)가 전달한다 — unit 경계 존중
    (U4 입력 계약은 `SearchResult.papers[i].id`, U4 §3).
    리스트 모드는 절단하지 않는다 — 모바일 분기는 노드 검색창으로 필터(TRACE-01 AC).
    """
    outgoing, incoming = one_hop.outgoing, one_hop.incoming
    if render == "graph":
        budget = MAX_NODES - 1  # 중심 노드 1 제외
        ranked = sorted(
            [("out", hit) for hit in outgoing] + [("in", hit) for hit in incoming],
            key=lambda pair: pair[1].citations,
            reverse=True,
        )[:budget]
        outgoing = [hit for direction, hit in ranked if direction == "out"]
        incoming = [hit for direction, hit in ranked if direction == "in"]
    return CitationView(
        center=center, outgoing=outgoing, incoming=incoming, render=render
    )
