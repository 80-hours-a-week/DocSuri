"""KoEnQueryMapper — component-model §3.2 · US-DISC-04.

입력 언어 감지 + 한국어 질문 → 영문 키워드 매핑 + 그 *1줄 설명* 생성.

매핑은 두 경로를 합친다:
  1) KO_EN_SEED — 자주 쓰는 학술어 결정적 매핑 (U1 도메인 지식, mock·실모델 공통 안전망)
  2) LlmGateway — 시드에 없는 표현 보강 (실모델). mock LLM은 canned 한국어라 구조적
     키워드를 못 주므로, 파싱 실패 시 시드만으로 동작한다.
detect는 LLM 없이 한글 코드포인트 비율로 결정한다.
"""

from __future__ import annotations

from ..u0.llm_gateway import LlmGateway
from ..u0.ports import Lang
from .dtos import QueryMapping

# 한국어 학술어 → 영문 키워드 (U1 소속 도메인 지식, 사후 확장 가능)
KO_EN_SEED: dict[str, str] = {
    "트랜스포머": "transformer",
    "어텐션": "attention",
    "주의": "attention",
    "임베딩": "embedding",
    "검색": "retrieval",
    "생성": "generation",
    "요약": "summarization",
    "번역": "translation",
    "분류": "classification",
    "강화학습": "reinforcement learning",
    "신경망": "neural network",
    "언어모델": "language model",
    "확산": "diffusion",
    "정렬": "alignment",
    "미세조정": "fine-tuning",
    "사전학습": "pretraining",
}


def _hangul_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    hangul = sum(1 for c in letters if "가" <= c <= "힣" or "ᄀ" <= c <= "ᇿ")
    return hangul / len(letters)


class KoEnQueryMapper:
    def __init__(self, llm: LlmGateway) -> None:
        self._llm = llm

    def detect(self, query: str) -> Lang:
        return "ko" if _hangul_ratio(query) >= 0.3 else "en"

    def map_explain(self, ko_query: str) -> QueryMapping:
        """한국어 쿼리를 영문 키워드로 매핑하고 1줄 설명을 만든다 (US-DISC-04 AC)."""
        en_keywords: list[str] = []
        for ko_term, en_term in KO_EN_SEED.items():
            if ko_term in ko_query and en_term not in en_keywords:
                en_keywords.append(en_term)

        # 실모델에서는 LLM이 시드 밖 표현을 보강한다. mock은 canned라 _parse가 비고,
        # 그 경우 시드 결과만 사용한다. (호출 자체로 Telemetry·CostGuard가 작동)
        completion = self._llm.complete(
            prompt=(
                "다음 한국어 연구 질문을 영문 검색 키워드로 바꿔라. "
                f"키워드만 쉼표로 나열하라: {ko_query}"
            ),
            persona="undergrad",
            budget_tokens=200,
        )
        for term in _parse_terms(completion.text):
            if term not in en_keywords:
                en_keywords.append(term)

        if not en_keywords:
            en_keywords = [ko_query.strip()]

        explanation = (
            f"입력하신 \"{ko_query.strip()}\"을(를) 영문 키워드 "
            f"{', '.join(en_keywords)}(으)로 매핑해 검색했습니다."
        )
        return QueryMapping(en_keywords=en_keywords, explanation=explanation)


def _parse_terms(text: str) -> list[str]:
    """LLM 응답에서 영문 키워드만 추출 — 긴 한국어 문장(canned mock)은 걸러진다."""
    terms: list[str] = []
    for chunk in text.replace("\n", ",").split(","):
        candidate = chunk.strip(" .·-\t")
        if not candidate or len(candidate.split()) > 6:
            continue
        ascii_letters = sum(1 for c in candidate if c.isascii() and c.isalpha())
        if ascii_letters >= 3 and ascii_letters >= len(candidate) / 2:
            terms.append(candidate.lower())
    return terms
