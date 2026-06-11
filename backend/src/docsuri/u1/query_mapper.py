"""KoEnQueryMapper — component-model §3.2 · US-DISC-04.

입력 언어 감지 + 한국어 질문 → 영문 키워드 매핑 + 그 *1줄 설명* 생성.

매핑은 두 경로를 합친다:
  1) KO_EN_SEED — 자주 쓰는 학술어 결정적 매핑 (U1 도메인 지식, mock·실모델 공통 안전망)
  2) LlmGateway — 시드에 없는 표현 보강 (실모델). mock LLM은 canned 한국어라 구조적
     키워드를 못 주므로, 파싱 실패 시 시드만으로 동작한다.
detect는 LLM 없이 한글 코드포인트 비율로 결정한다.

CLAUDE.md 준수:
  - #2 동일 입력 중복 호출 방지 — query 단위로 결과를 CachePort에 캐시(TTL 명시).
  - #1 Prompt Injection — 사용자 입력을 무해화 후 <user_query> 델리미터로 분리.
  - #4 실패 격리 — LLM 보강 실패가 시드 매핑을 죽이지 않도록 호출을 try로 감싼다.
"""

from __future__ import annotations

from ..u0.llm_gateway import LlmGateway
from ..u0.ports import CachePort, Lang
from .dtos import QueryMapping
from .safety import (
    INJECTION_GUARD,
    QUERY_CACHE_TTL_S,
    normalize_query,
    sanitize_query,
    wrap_user_data,
)

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
    def __init__(self, llm: LlmGateway, cache: CachePort) -> None:
        self._llm = llm
        self._cache = cache

    def detect(self, query: str) -> Lang:
        return "ko" if _hangul_ratio(query) >= 0.3 else "en"

    def map_explain(self, ko_query: str) -> QueryMapping:
        """한국어 쿼리를 영문 키워드로 매핑하고 1줄 설명을 만든다 (US-DISC-04 AC)."""
        safe = sanitize_query(ko_query)
        cache_key = f"koen:{normalize_query(ko_query)}"
        cached = self._cache.get(cache_key)
        if cached is not None:  # #2 동일 입력 재호출 차단
            return QueryMapping.model_validate_json(cached)

        en_keywords: list[str] = []
        for ko_term, en_term in KO_EN_SEED.items():
            if ko_term in safe and en_term not in en_keywords:
                en_keywords.append(en_term)

        for term in self._llm_keywords(safe):  # #4 실패해도 시드는 유지
            if term not in en_keywords:
                en_keywords.append(term)

        if not en_keywords:
            en_keywords = [safe]

        mapping = QueryMapping(
            en_keywords=en_keywords,
            explanation=(
                f"입력하신 \"{safe}\"을(를) 영문 키워드 "
                f"{', '.join(en_keywords)}(으)로 매핑해 검색했습니다."
            ),
        )
        self._cache.set(cache_key, mapping.model_dump_json().encode(), QUERY_CACHE_TTL_S)
        return mapping

    def _llm_keywords(self, safe_query: str) -> list[str]:
        """시드 밖 표현을 LLM으로 보강 — 실패 시 빈 목록(검색은 시드로 진행)."""
        try:
            completion = self._llm.complete(
                prompt=(
                    INJECTION_GUARD
                    + "이 검색어를 영문 검색 키워드로 바꿔 쉼표로만 나열하라:\n"
                    + wrap_user_data(safe_query)
                ),
                persona="undergrad",
                budget_tokens=200,
            )
            return _parse_terms(completion.text)
        except Exception:  # noqa: BLE001 — 보강 실패는 검색을 막지 않는다 (#4)
            return []


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
