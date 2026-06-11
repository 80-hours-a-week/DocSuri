"""KeywordExpander — component-model §3.3 · US-DISC-03.

자연어를 동의어·관련 용어로 확장한 목록을 만든다. 사용자는 각 칩을 체크/해제해
즉시 재검색한다(재검색 트리거는 SearchOrchestrator가 수행 — 본 컴포넌트는 *목록만*).

두 경로 병합(KoEnQueryMapper와 동일 전략):
  1) EXPANSION_SEED — 약어·정규 표현 결정적 확장 (U1 도메인 지식)
  2) LlmGateway — 시드 밖 보강(실모델). mock canned는 파싱 실패 → 시드만.
"""

from __future__ import annotations

from ..u0.llm_gateway import LlmGateway
from .dtos import ExpandedTerm
from .query_mapper import _parse_terms

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


class KeywordExpander:
    def __init__(self, llm: LlmGateway) -> None:
        self._llm = llm

    def expand(self, query: str) -> list[ExpandedTerm]:
        terms: list[str] = []
        for token in _tokenize(query):
            for expansion in EXPANSION_SEED.get(token, []):
                if expansion not in terms:
                    terms.append(expansion)

        completion = self._llm.complete(
            prompt=(
                "다음 검색어의 동의어·관련 영문 용어를 쉼표로 나열하라(용어만): "
                f"{query}"
            ),
            persona="pro",
            budget_tokens=200,
        )
        for term in _parse_terms(completion.text):
            if term not in terms and term != query.lower():
                terms.append(term)

        return [ExpandedTerm(term=t, checked=False) for t in terms[:MAX_TERMS]]


def _tokenize(query: str) -> list[str]:
    cleaned = "".join(c if c.isalnum() else " " for c in query.lower())
    return [tok for tok in cleaned.split() if tok]
