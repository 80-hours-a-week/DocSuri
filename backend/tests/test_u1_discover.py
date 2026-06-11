"""U1 Discover 검증 — unit-u1-discover.md §6 Buildable의 서버측 부분.

DISC-01(의미검색)·02(정렬·필터)·03(키워드 확장)·04(한국어 검색) AC를 mock 모드로 통과.
"""

from __future__ import annotations

from docsuri.u0.ports import SearchFilters
from docsuri.u1.difficulty import DifficultyEstimator
from docsuri.u1.filter_sort import FilterSortController

_RANK = {"입문": 0, "중급": 1, "고급": 2}


# --- US-DISC-01 자연어 의미 검색 ---------------------------------------------

def test_disc01_returns_top20_with_six_meta(u1env):
    resp = u1env.svc.orchestrator.search_for(
        "transformer-based retrieval-augmented summarization"
    )
    result = resp.result
    assert len(result.papers) == 20  # 상위 20건 (k=20, 코퍼스 100편)
    assert result.lang == "en"
    for p in result.papers:
        # 데스크톱 6메타 (NFR-UX-03): title·authors·year·citations·similarity·difficulty
        assert p.title and p.authors and p.year
        assert p.difficulty in ("입문", "중급", "고급")
    # 기본 정렬은 유사도 내림차순
    sims = [p.similarity for p in result.papers]
    assert sims == sorted(sims, reverse=True)


def test_disc01_cache_hit_on_repeat(u1env):
    u1env.svc.orchestrator.search_for("graph neural networks")
    u1env.svc.orchestrator.search_for("graph neural networks")
    events = u1env.u0.telemetry.events
    search_events = [e for e in events if e["op"] == "search"]
    assert len(search_events) == 2
    assert search_events[0]["cache_hit"] is False
    assert search_events[1]["cache_hit"] is True  # 동일 쿼리 24h 재사용


# --- US-DISC-02 결과 정렬·필터 ------------------------------------------------

def test_disc02_filter_and_citation_sort(u1env):
    filters = SearchFilters(year_min=2023, year_max=2026, field_tags=["cs.LG"])
    resp = u1env.svc.orchestrator.search_for(
        "neural network", filters=filters, sort_key="citations"
    )
    papers = resp.result.papers
    assert papers
    for p in papers:
        assert 2023 <= p.year <= 2026
    cites = [p.citations for p in papers]
    assert cites == sorted(cites, reverse=True)  # 인용수 내림차순


def test_disc02_filter_url_roundtrip(u1env):
    fs: FilterSortController = u1env.svc.filter_sort
    filters = SearchFilters(year_min=2023, year_max=2026, field_tags=["cs.LG", "cs.CL"])
    url = fs.to_url(filters, "citations")
    assert "year_min=2023" in url and "sort=citations" in url
    restored_filters, restored_sort = fs.from_url(url)
    assert restored_filters == filters  # 새로고침 시 필터 유지
    assert restored_sort == "citations"


# --- US-DISC-03 키워드 자동 확장 ---------------------------------------------

def test_disc03_expand_known_acronym(u1env):
    terms = u1env.svc.expander.expand("RAG")
    texts = [t.term for t in terms]
    assert "retrieval-augmented generation" in texts
    assert all(t.checked is False for t in terms)  # 기본 미선택


def test_disc03_selected_term_marked_and_changes_results(u1env):
    base = u1env.svc.orchestrator.search_for("transformer")
    picked = base.result.expanded_terms[0].term
    refined = u1env.svc.orchestrator.search_for("transformer", selected_terms=[picked])
    selected = [t for t in refined.result.expanded_terms if t.term == picked]
    assert selected and selected[0].checked is True  # 선택 칩 표시
    # 선택 키워드는 캐시 키를 분리한다 → 두 검색 모두 캐시 미스(별도 검색 수행)
    misses = [e for e in u1env.u0.telemetry.events if e["op"] == "search" and not e["cache_hit"]]
    assert len(misses) == 2


# --- US-DISC-04 학부생 한국어 검색 -------------------------------------------

def test_disc04_korean_detect_and_mapping(u1env):
    resp = u1env.svc.orchestrator.search_for("트랜스포머가 뭔가요")
    assert resp.result.lang == "ko"
    assert resp.query_mapping is not None
    assert "transformer" in resp.query_mapping.en_keywords
    assert "transformer" in resp.query_mapping.explanation


def test_disc04_intro_papers_float_up(u1env):
    resp = u1env.svc.orchestrator.search_for("트랜스포머가 뭔가요")
    ranks = [_RANK[p.difficulty] for p in resp.result.papers]
    # 한국어 입력은 난이도 tier 오름차순 가중 → 입문 적합 상위
    assert ranks == sorted(ranks)


def test_difficulty_estimator_labels_span_corpus(u1env):
    est = DifficultyEstimator()
    vec = u1env.u0.embedding.embed("ai", "en")
    hits = u1env.u0.embedding.search(vec, k=100)
    labels = {est.estimate(h).label for h in hits}
    assert labels & {"입문", "중급", "고급"}  # 라벨이 실제로 부여됨
