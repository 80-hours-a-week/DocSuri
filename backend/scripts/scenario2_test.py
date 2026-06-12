"""시나리오 2 테스트: 연구 공백 제안.

Given: 시나리오 1의 차별성 분석 결과가 존재
When:  "연구 공백 제안" 요청
Then:  후보 3개 (짧은 제목 + 한 문단 설명 + 근거 논문 ID)

실행: cd backend && pyenv exec python3 scripts/scenario2_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scenario1_test import (
    NoveltyReport,
    run_scenario1,
    run_scenario2,
)

from docsuri.u0.ports import Persona


def print_scenario2(report: NoveltyReport) -> None:
    print("\n" + "=" * 60)
    print("시나리오 2: 연구 공백 제안")
    print("=" * 60)
    print(f"[Persona] {report.persona_mode}")
    print(f"\n[입력] 시나리오 1 차별성 분석 결과 (유사 논문 {len(report.similar_papers)}편)\n")

    if not report.gap_proposals:
        print("연구 공백 제안 생성 실패")
        return

    print(f"[연구 공백 제안 {len(report.gap_proposals)}개]")
    for i, g in enumerate(report.gap_proposals, 1):
        evidence_links = " / ".join(
            f"https://arxiv.org/abs/{eid}" for eid in g.evidence_ids
        )
        print(f"\n  {i}. {g.title}")
        print(f"     {g.body}")
        print(f"     근거 논문 ID: {', '.join(g.evidence_ids)}")
        print(f"     출처: {evidence_links}")

    print("=" * 60)


if __name__ == "__main__":
    USER_TOPIC = """
본 연구는 대규모 언어 모델(LLM)을 활용한 자동화된 논문 novelty 평가 시스템을 제안한다.
기존 연구자들은 새로운 연구 아이디어의 차별성을 파악하기 위해 수동으로 관련 논문을 검색하고
비교해야 하는 번거로움이 있었다. 본 시스템은 연구 주제 초안을 입력받아 벡터 유사도 검색을
통해 관련 논문을 자동으로 찾고, LLM이 각 논문과의 공통점·차이점을 분석하여 연구 공백을
제안하는 end-to-end 파이프라인을 구축한다.
""".strip()

    # 시나리오 1 결과를 기반으로 시나리오 2 실행
    report = run_scenario1(USER_TOPIC, persona="pro")
    report = run_scenario2(report)
    print_scenario2(report)
