"""KeywordExpander — component-model §3.3 · US-DISC-03.

자연어를 동의어·관련 용어로 확장한 목록을 만든다. 사용자는 각 칩을 체크/해제해
즉시 재검색한다(재검색 트리거는 SearchOrchestrator가 수행 — 본 컴포넌트는 *목록만*).

두 경로 병합(KoEnQueryMapper와 동일 전략):
  1) EXPANSION_SEED — 약어·정규 표현 결정적 확장 (U1 도메인 지식)
  2) LlmGateway — 시드 밖 보강(실모델). mock canned는 파싱 실패 → 시드만.

보안·비용·견고성: query 단위 캐시 · 입력 무해화+델리미터 · LLM 실패 격리.
"""

from __future__ import annotations

from pydantic import TypeAdapter

from ..u0.llm_gateway import LlmGateway
from ..u0.ports import CachePort
from .dtos import ExpandedTerm
from .query_mapper import _parse_terms
from .safety import (
    INJECTION_GUARD,
    QUERY_CACHE_TTL_S,
    normalize_query,
    sanitize_query,
    wrap_user_data,
)

# 약어/표현 → 확장 (US-DISC-03 AC: "RAG" → retrieval-augmented generation 등)
EXPANSION_SEED: dict[str, list[str]] = {
    "rag": ["retrieval-augmented generation", "retrieval augmented"],
    "llm": ["large language model"],
    "nlp": ["natural language processing"],
    "cv": ["computer vision"],
    "rl": ["reinforcement learning"],
    "vit": ["vision transformer"],
    "gan": ["generative adversarial network"],
    "transformer": ["self-attention", "attention mechanism"],
    "attention": ["self-attention"],
    "summarization": ["abstractive summarization", "text summarization"],
}

MAX_TERMS = 8
_TERMS = TypeAdapter(list[ExpandedTerm])


class KeywordExpander:
    def __init__(self, llm: LlmGateway, cache: CachePort) -> None:
        self._llm = llm
        self._cache = cache

    def expand(self, query: str) -> list[ExpandedTerm]:
        safe = sanitize_query(query)
        cache_key = f"expand:{normalize_query(query)}"
        cached = self._cache.get(cache_key)
        if cached is not None:  # #2 동일 입력 재호출 차단
            return list(_TERMS.validate_json(cached))

        terms: list[str] = []
        for token in _tokenize(safe):
            for expansion in EXPANSION_SEED.get(token, []):
                if expansion not in terms:
                    terms.append(expansion)

        for term in self._llm_terms(safe):  # #4 실패해도 시드는 유지
            if term not in terms and term != safe.lower():
                terms.append(term)

        result = [ExpandedTerm(term=t, checked=False) for t in terms[:MAX_TERMS]]
        self._cache.set(cache_key, _TERMS.dump_json(result), QUERY_CACHE_TTL_S)
        return result

    def _llm_terms(self, safe_query: str) -> list[str]:
        try:
            completion = self._llm.complete(
                prompt=(
                    INJECTION_GUARD
                    + "이 검색어의 동의어·관련 영문 용어를 쉼표로만 나열하라:\n"
                    + wrap_user_data(safe_query)
                ),
                persona="pro",
                budget_tokens=200,
            )
            return _parse_terms(completion.text)
        except Exception:  # noqa: BLE001 — 확장 실패는 검색을 막지 않는다 (#4)
            return []


def _tokenize(query: str) -> list[str]:
    cleaned = "".join(c if c.isalnum() else " " for c in query.lower())
    return [tok for tok in cleaned.split() if tok]
