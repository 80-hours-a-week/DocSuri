"""DifficultyEstimator — component-model §3.4 · A7 휴리스틱.

논문 1편의 난이도 점수·라벨(입문/중급/고급)을 *LLM 없이* PaperHit 메타만으로
결정적으로 추정한다. 신호:
  - abstract_len ↑ → 난이도 ↑ (길고 밀도 높은 초록)
  - field_tags 폭 ↑ → 난이도 ↑ (교차분야)
  - citations ↑ → 난이도 ↓ (널리 인용 = 기초·접근성)

⚠️ 초기 휴리스틱이다. 정밀도 평가·튜닝은 U1 책임(unit-u1-discover.md §7).
기준 범위(REF)는 시드 코퍼스 분포(abstract 742~1917, citations 1~497, tags 1~5)에서
잡되, estimate는 *단일 PaperHit*만 보도록 코퍼스 전역 의존을 두지 않는다.
"""

from __future__ import annotations

from ..u0.ports import PaperHit
from .dtos import Difficulty, DifficultyLabel

ABSTRACT_REF = (700.0, 1900.0)
CITATIONS_REF = (0.0, 500.0)
TAGS_REF = (1.0, 5.0)

# 가중치 (합 1.0)
W_ABSTRACT = 0.55
W_TAGS = 0.15
W_CITATIONS = 0.30

# 라벨 임계값 (score 오름차순)
INTRO_MAX = 0.40   # < 0.40 → 입문
MID_MAX = 0.62     # < 0.62 → 중급, 이상 → 고급


def _norm(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _label_for(score: float) -> DifficultyLabel:
    if score < INTRO_MAX:
        return "입문"
    if score < MID_MAX:
        return "중급"
    return "고급"


class DifficultyEstimator:
    """A7 휴리스틱의 단일 구현 (component-model §3.4)."""

    def estimate(self, paper: PaperHit) -> Difficulty:
        norm_abstract = _norm(paper.abstract_len, *ABSTRACT_REF)
        norm_tags = _norm(len(paper.field_tags), *TAGS_REF)
        norm_citations = _norm(paper.citations, *CITATIONS_REF)
        score = (
            W_ABSTRACT * norm_abstract
            + W_TAGS * norm_tags
            + W_CITATIONS * (1.0 - norm_citations)
        )
        return Difficulty(score=round(score, 4), label=_label_for(score))
