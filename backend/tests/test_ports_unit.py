"""포트별 단위 검증 — 빌드 가능 정의 외의 계약 동작."""

from __future__ import annotations

import pytest

from docsuri.u0.cost_guard import CostGuard, CostLimitExceeded, InMemoryCostStore
from docsuri.u0.http_policy import NetworkRetryExceeded, request_with_retry
from docsuri.u0.ports import SearchFilters


def test_search_filters_year_and_tags(u0):
    vec = u0.embedding.embed("neural network", lang="en")
    all_hits = u0.embedding.search(vec, k=20)
    year_cut = max(h.year for h in all_hits) - 1
    filtered = u0.embedding.search(
        vec, k=20, filters=SearchFilters(year_min=year_cut)
    )
    assert filtered, "필터 결과가 비면 안 됨 (코퍼스가 최신 논문 위주)"
    assert all(h.year >= year_cut for h in filtered)  # US-DISC-02 연도 필터

    tag = all_hits[0].field_tags[0]
    tagged = u0.embedding.search(vec, k=20, filters=SearchFilters(field_tags=[tag]))
    assert tagged and all(tag in h.field_tags for h in tagged)  # 분야 필터


def test_persona_tone_differs(u0):
    pro = u0.llm.complete("같은 질문", persona="pro", budget_tokens=500)
    undergrad = u0.llm.complete("같은 질문", persona="undergrad", budget_tokens=500)
    assert pro.text != undergrad.text  # U2 §6 '다른 톤' 전제의 U0 수준 보장


def test_session_filters_url_roundtrip(u0):
    original = SearchFilters(year_min=2023, year_max=2026, field_tags=["cs.LG", "cs.CL"])
    query = u0.session.serialize_filters(original)
    assert query and "year_min=2023" in query
    restored = u0.session.restore_filters(query)
    assert restored == original  # US-DISC-02 새로고침 유지
    assert u0.session.session().filters_url == query
    assert u0.session.session().anon_id  # NFR-SEC-01 익명


def test_glossary_lookup_hit_and_miss(u0):
    hit = u0.glossary.lookup("Transformer")  # 대소문자 무관
    assert hit is not None and hit.ko.startswith("트랜스포머")
    assert u0.glossary.lookup("nonexistent-term-xyz") is None


def test_citation_one_hop_shape(u0):
    paper_id = u0.embedding.search(u0.embedding.embed("ai", lang="en"), k=1)[0].id
    result = u0.citation.one_hop(paper_id)
    assert result.outgoing and result.incoming
    assert all(h.id != paper_id for h in result.outgoing + result.incoming)
    repeat = u0.citation.one_hop(paper_id)
    assert repeat == result  # 결정적


def test_cost_guard_hard_reject():
    guard = CostGuard(
        store=InMemoryCostStore(),
        monthly_cap_usd=0.001,  # 사실상 즉시 상한
        price_in_per_mtok=1.0,
        price_out_per_mtok=5.0,
    )
    with pytest.raises(CostLimitExceeded) as exc:
        guard.check_budget(estimated_tokens_in=10_000, estimated_tokens_out=10_000)
    assert "상한" in str(exc.value)  # 사용자 노출용 한국어 메시지


def test_cost_guard_accumulates():
    guard = CostGuard(
        store=InMemoryCostStore(),
        monthly_cap_usd=50.0,
        price_in_per_mtok=1.0,
        price_out_per_mtok=5.0,
    )
    guard.record_cost(tokens_in=1_000_000, tokens_out=1_000_000)  # $1 + $5
    assert guard.accumulated_usd() == pytest.approx(6.0)


def test_http_policy_retries_then_korean_error():
    import httpx

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleeps: list[float] = []
    with pytest.raises(NetworkRetryExceeded) as exc:
        request_with_retry(client, "GET", "https://example.test", sleep=sleeps.append)
    assert calls["n"] == 4  # 최초 1회 + 재시도 3회 (NFR-NET-02)
    assert sleeps == [1.0, 2.0, 4.0]  # 지수 백오프
    assert "네트워크" in str(exc.value)  # 4회차 사용자 알림
