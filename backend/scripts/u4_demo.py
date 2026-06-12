"""U4 §6 빌드 가능 정의 시연 — 백엔드 범위 (TRACE-01a + TRACE-02 로직).

UI 항목(그래프/리스트 화면, 노드 클릭→카드)은 U4-UI 후속 라운드
(u4_build_plan.md C2 결정 — 프론트 스캐폴드는 U1 소유).
실행: uv run python scripts/u4_demo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docsuri.u0.adapters import build_u0
from docsuri.u0.config import load_settings
from docsuri.u4.service import CitationFetcher, FormFactorRouter, TopInfluenceSelector, build_view


def main() -> int:
    settings = load_settings()
    u0 = build_u0(settings)
    fetcher = CitationFetcher(citation=u0.citation, cache=u0.cache, telemetry=u0.telemetry)
    router = FormFactorRouter()
    print(f"=== U4 §6 시연 — 백엔드 범위 (모드: {settings.adapter_mode}) ===\n")

    center = u0.embedding.search(u0.embedding.embed("transformer", lang="en"), k=1)[0]
    print(f"중심 논문 (U1 SearchResult mock): [{center.id}] {center.title[:50]}\n")

    # ① oneHop fixture mock → 데이터 AC
    started = time.perf_counter()
    one_hop = fetcher.fetch(center.id)
    latency = (time.perf_counter() - started) * 1000
    print(f"✅ ①  CitationApi.oneHop fixture — outgoing {len(one_hop.outgoing)}건 / "
          f"incoming {len(one_hop.incoming)}건, {latency:.1f}ms (P95 예산 5s/7s 대비)")
    fetcher.fetch(center.id)
    print(f"   캐시 재사용(24h): cache_hit={u0.telemetry.events[-1]['cache_hit']}\n")

    # ② 동일 paper_id에서 렌더 분기
    desktop = router.route(1280, "pro")
    mobile = router.route(360, "pro")
    undergrad = router.route(1280, "undergrad")
    ok = (desktop, mobile, undergrad) == ("graph", "list", "list")
    print(f"{'✅' if ok else '❌'} ②  렌더 분기 — 데스크톱:{desktop} / 모바일(<768px):{mobile} / "
          f"학부 모드:{undergrad} (NFR-MOBILE-05·TRACE-02)")

    view = build_view(center, one_hop, desktop)
    print(f"   그래프 뷰: 노드 {1 + len(view.outgoing) + len(view.incoming)}개 "
          f"(max_nodes={view.max_nodes})\n")

    # ③ TRACE-02 Top-3
    top3 = TopInfluenceSelector().top3(one_hop.incoming)
    print(f"✅ ③  영향력 Top-3 (피인용 내림차순): "
          f"{[(h.id, h.citations) for h in top3]}\n")

    # ④ UI 항목 — 후속 라운드
    print("⏭️  ④  노드 클릭→논문 카드 / 그래프·리스트 화면 렌더 — U4-UI 후속 라운드 "
          "(TRACE-01b, U1 스캐폴드 머지 후)\n")
    print("=== 백엔드 범위 시연 완료 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
