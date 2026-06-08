"""Prompt builder for span translation (#03 Sprint 1).

Same 4-block layout as #02 summarization so the prompt-cache hits reuse
across summary↔translation when the conventions/paper/glossary blocks
are identical. AGENTS.md §4.1 — `infra/llm` owns the actual key derivation.

Layout (cached blocks listed in cache-priority order):
1. §6 conventions (incl. §6.2 glossing + §6.3 -한다 체)
2. Paper context (the ±200-char window around the span)
3. Session glossary
4. FRESH user_message — the English span to translate
"""

from __future__ import annotations

from app.domain.papers.models import GlossaryEntry
from app.domain.translation.span import ResolvedSpan
from app.infra.llm.protocol import CachedBlock, LLMRequest

_CONVENTIONS_BLOCK = """SYSTEM — AGENTS.md §6 OUTPUT CONVENTIONS (verbatim).

§6.1 Anchor 강제
- 산출물의 모든 sentence에 `[§n.m]` 또는 `[p.X ¶Y]` 인용 필수.

§6.2 Glossing Rule
- 도메인 용어 첫 등장 시 `한국어(English)` 병기. 예: `주의(attention)`.
- 두 번째 등장 이후 한국어만.
- 세션 누적: 한 번 결정된 한국어 표기는 동일 세션 내 모든 산출물에
  동일 적용 (#02 요약 ↔ #03 번역 공유).

§6.3 종결형 (학술체)
- 한국어 산출물 종결형은 `-한다` 체로 통일.
- 능동/수동: 원문 보존 우선. 한국어 자연성 vs 학술 정확성 trade-off
  시 literal-first, idiomatic-second.
- LaTeX 수식·인용 번호([12])·표 구조는 통과(pass-through), 번역 금지.

§6.4 길이 제약
- 100자 이상 연속 직역 금지 (§1.2 표절 경계).

§6.5 구조화 출력
- 응답은 한국어 번역 본문만 반환한다. 별도 메타데이터 없음.

번역 지시: 학술체 `-한다` 체로 번역한다. 도메인 용어는 첫 등장 시
한국어(English) 병기하고, 세션 glossary에 이미 결정된 표기가 있다면
그것을 강제 사용한다. LaTeX 수식과 [12] 형식 인용은 그대로 둔다."""


def build_translate_prompt(
    span: ResolvedSpan,
    glossary_entries: list[GlossaryEntry],
) -> LLMRequest:
    glossary_text = (
        "세션 누적 glossary (English → 한국어):\n"
        + "\n".join(f"- {e.english} → {e.korean}" for e in glossary_entries)
        if glossary_entries
        else "세션 glossary 없음."
    )

    paper_block_text = (
        f"PAPER {span.paper_id} §{span.section_id} "
        f"chars {span.char_start}..{span.char_end}\n\n"
        f"주변 컨텍스트 (±200자):\n{span.context}"
    )

    user_message = (
        "다음 영어 SPAN을 학술체 한국어로 번역한다. "
        "도메인 용어 첫 등장 시 `한국어(English)` 병기, "
        "이후 등장은 한국어만 사용한다. 종결형은 `-한다` 체로 통일한다.\n\n"
        f"SPAN:\n{span.span_text}"
    )

    return LLMRequest(
        system_blocks=[
            CachedBlock(name="conventions_v1", text=_CONVENTIONS_BLOCK),
            CachedBlock(name=f"paper_{span.paper_id}_ctx", text=paper_block_text),
            CachedBlock(name="glossary_session", text=glossary_text),
        ],
        user_message=user_message,
        max_tokens=512,
        temperature=0.2,
        purpose="translation",
    )
