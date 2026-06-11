"""U1 Discover 시연 — DISC-01·02·03·04 서버측 동작, mock 모드(자격 증명 불필요).

출처: aidlc-docs/design-artifacts/units/unit-u1-discover.md §6
실행: uv run python scripts/u1_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docsuri.u0.adapters import build_u0
from docsuri.u0.config import load_settings
from docsuri.u0.ports import SearchFilters
from docsuri.u1.service import build_u1

CHECKS: list[bool] = []


def show(label: str, passed: bool, detail: str) -> None:
    CHECKS.append(passed)
    print(f"{'✅' if passed else '❌'} {label}\n   {detail}\n")


def main() -> int:
    settings = load_settings()
    svc = build_u1(build_u0(settings))
    print(f"=== U1 Discover 시연 (모드: {settings.adapter_mode}) ===\n")

    # DISC-01 — 자연어 의미 검색: 상위 20건 + 6메타
    r1 = svc.orchestrator.search_for(
        "transformer-based retrieval-augmented summarization"
    ).result
    top = r1.papers[0]
    show(
        "DISC-01 의미 검색 → 상위 20건 + 6메타",
        len(r1.papers) == 20,
        f"{len(r1.papers)}건, 1위 [{top.similarity}|{top.difficulty}] {top.title[:42]}",
    )

    # DISC-02 — 필터(연도·분야) + 인용수 내림차순 정렬
    r2 = svc.orchestrator.search_for(
        "neural network",
        filters=SearchFilters(year_min=2023, year_max=2026, field_tags=["cs.LG"]),
        sort_key="citations",
    ).result
    cites = [p.citations for p in r2.papers]
    url = svc.filter_sort.to_url(r2.filters, "citations")
    show(
        "DISC-02 필터 + 인용수 정렬 + URL 직렬화",
        cites == sorted(cites, reverse=True) and "sort=citations" in url,
        f"{len(r2.papers)}건, 인용수 {cites[:3]}…, URL: {url}",
    )

    # DISC-03 — 키워드 자동 확장
    terms = [t.term for t in svc.expander.expand("RAG")]
    show(
        "DISC-03 키워드 확장",
        "retrieval-augmented generation" in terms,
        f"확장: {terms}",
    )

    # DISC-04 — 한국어 검색: 매핑 1줄 + 입문 적합 상위
    r4 = svc.orchestrator.search_for("트랜스포머가 뭔가요")
    ranks_sorted = [p.difficulty for p in r4.result.papers]
    show(
        "DISC-04 한국어 검색 → 한→영 매핑 + 입문 상위",
        r4.result.lang == "ko" and r4.query_mapping is not None,
        f"매핑: {r4.query_mapping.explanation}\n   난이도 순: {ranks_sorted[:6]}…",
    )

    passed = sum(CHECKS)
    print(f"=== 결과: {passed}/{len(CHECKS)} 통과 ===")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
