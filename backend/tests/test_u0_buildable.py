"""U0 §6 빌드 가능 정의 6항목과 1:1 매핑되는 검증.

출처: aidlc-docs/design-artifacts/units/unit-u0-foundation.md §6
"""

from __future__ import annotations

import re

from docsuri.u0.adapters.mock import InMemoryTtlCache
from docsuri.u0.ports import PaperHit, TelemetryEvent

KOREAN = re.compile(r"[가-힣]")


def test_u0_1_embed_returns_vector(u0):
    vec = u0.embedding.embed("transformer", lang="en")
    assert isinstance(vec, list) and len(vec) > 0
    assert all(isinstance(x, float) for x in vec)
    assert vec == u0.embedding.embed("transformer", lang="en")  # 결정적


def test_u0_2_search_returns_5_paperhits(u0):
    vec = u0.embedding.embed("transformer", lang="en")
    hits = u0.embedding.search(vec, k=5)
    assert len(hits) == 5
    assert all(isinstance(h, PaperHit) for h in hits)
    similarities = [h.similarity for h in hits]
    assert similarities == sorted(similarities, reverse=True)
    top = hits[0]
    assert top.id and top.title and top.year > 0


def test_u0_3_llm_complete_korean_200_400(u0):
    completion = u0.llm.complete("transformer 논문을 요약해줘", persona="pro", budget_tokens=2000)
    assert 200 <= len(completion.text) <= 400
    assert KOREAN.search(completion.text), "응답은 한국어여야 한다"
    assert completion.tokens_in > 0 and completion.tokens_out > 0


def test_u0_4_cache_24h_ttl_miss_after_25h(fake_clock):
    cache = InMemoryTtlCache(clock=fake_clock)
    cache.set("search:transformer", b"cached-result", ttl_s=24 * 3600)
    assert cache.get("search:transformer") == b"cached-result"
    fake_clock.advance(23 * 3600)
    assert cache.get("search:transformer") == b"cached-result"  # 23h — 적중
    fake_clock.advance(2 * 3600)
    assert cache.get("search:transformer") is None  # 25h — miss (U0 §6)


def test_u0_5_telemetry_has_required_keys(u0):
    u0.llm.complete("어텐션이란?", persona="undergrad", budget_tokens=500)
    event = u0.telemetry.events[-1]
    for key in ("latency_ms", "tokens_in", "tokens_out", "cache_hit"):
        assert key in event, f"NFR-OBS-01 키 누락: {key}"
    assert event["op"] == "llm.complete"
    assert event["persona"] == "undergrad"


def test_u0_6_cost_simulation_reference():
    """U0 §6 마지막 항목(NFR-COST-01 시뮬레이션 보고)은 ADR §13이 충족 — 월 ~$45 ≤ $50.

    런타임 측에서는 CostGuard가 상한을 강제한다 (test_cost_guard 참조).
    """
    from docsuri.u0.config import load_settings

    assert load_settings().cost_monthly_cap_usd == 50.0
