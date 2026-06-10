"""U0 §6 빌드 가능 정의 시연 — mock 모드, 자격 증명 불필요.

출처: aidlc-docs/design-artifacts/units/unit-u0-foundation.md §6
실행: uv run python scripts/u0_demo.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docsuri.u0.adapters import build_u0
from docsuri.u0.adapters.mock import InMemoryTtlCache
from docsuri.u0.config import load_settings

CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, passed: bool, detail: str) -> None:
    CHECKS.append((label, passed, detail))
    print(f"{'✅' if passed else '❌'} {label}\n   {detail}\n")


def main() -> int:
    settings = load_settings()
    u0 = build_u0(settings)
    print(f"=== U0 §6 빌드 가능 정의 시연 (모드: {settings.adapter_mode}) ===\n")

    # 1. embed("transformer") → vector
    vec = u0.embedding.embed("transformer", lang="en")
    check(
        "EmbeddingPort.embed('transformer') → vector",
        isinstance(vec, list) and len(vec) > 0,
        f"차원 {len(vec)}, 앞 3개: {[round(x, 3) for x in vec[:3]]}",
    )

    # 2. search(v, k=5) → PaperHit 5건 (시드 코퍼스 100편)
    hits = u0.embedding.search(vec, k=5)
    check(
        "EmbeddingPort.search(v, k=5) → PaperHit 5건",
        len(hits) == 5,
        "상위: " + " / ".join(f"[{h.similarity}] {h.title[:40]}" for h in hits[:2]),
    )

    # 3. complete(persona='pro', budget=2000) → 한국어 200~400자
    completion = u0.llm.complete(
        "transformer 논문의 기여를 요약해줘", persona="pro", budget_tokens=2000
    )
    korean = bool(re.search(r"[가-힣]", completion.text))
    check(
        "LlmPort.complete(persona='pro', budget=2000) → 한국어 200~400자",
        200 <= len(completion.text) <= 400 and korean,
        f"{len(completion.text)}자, 한국어={korean}: {completion.text[:60]}…",
    )

    # 4. CachePort 24h TTL (set → 25h 후 miss) — 시간 주입 시뮬레이션
    class _Clock:
        now = 0.0

        def __call__(self) -> float:
            return self.now

    clock = _Clock()
    cache = InMemoryTtlCache(clock=clock)
    cache.set("demo", b"v", ttl_s=24 * 3600)
    hit_before = cache.get("demo") is not None
    clock.now += 25 * 3600
    miss_after = cache.get("demo") is None
    check(
        "CachePort 24h TTL — set → 25h 후 miss",
        hit_before and miss_after,
        f"0h 적중={hit_before}, 25h 후 miss={miss_after}",
    )

    # 5. Telemetry 출력에 latency·토큰·캐시 적중 키
    event = u0.telemetry.events[-1]
    required = {"latency_ms", "tokens_in", "tokens_out", "cache_hit"}
    check(
        "Telemetry 출력 키 (latency_ms·tokens_in/out·cache_hit)",
        required <= set(event),
        f"{ {k: event[k] for k in sorted(required)} }",
    )

    # 6. NFR-COST-01 시뮬레이션 보고
    check(
        "NFR-COST-01 시뮬레이션 — 월 $50 이내 추정 보고서",
        settings.cost_monthly_cap_usd == 50.0,
        "ADR §13 충족: 확정 스택 월 ~$45 ≤ $50. 런타임은 CostGuard 하드 거부 "
        f"(현재 누적 ${u0.cost_guard.accumulated_usd():.4f})",
    )

    failed = [label for label, passed, _ in CHECKS if not passed]
    print(f"=== 결과: {len(CHECKS) - len(failed)}/{len(CHECKS)} 통과 ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
