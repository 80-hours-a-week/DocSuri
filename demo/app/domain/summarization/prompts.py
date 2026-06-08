"""Prompt builder — 4 blocks (3 cached + 1 fresh) per AGENTS.md §4.1.

Cached blocks (in this order) so cache reuse maximises across the
preset matrix:

1. §6 conventions — verbatim AGENTS.md §6.1–§6.5 text. Stable across
   every summary request → highest cache value.
2. Structured paper — the full md transcript from `retriever.fetch`.
   Stable across re-summary of the same paper.
3. Glossary-so-far — current session glossary entries. Changes per
   session but stays the same across multiple summaries within it.

Fresh block:

4. user_message — the actual request (length × angle preset).
"""

from __future__ import annotations

from app.domain.papers.models import GlossaryEntry, Paper
from app.domain.summarization.presets import AnglePreset, LengthPreset
from app.infra.llm.protocol import CachedBlock, LLMRequest

# Verbatim distillation of AGENTS.md §6.1–§6.5. The LLM follows this as
# the cached system block; identical text across requests = cache hit.
# Kept ~300 words.
_CONVENTIONS_BLOCK = """SYSTEM — AGENTS.md §6 OUTPUT CONVENTIONS (verbatim).

§6.1 Anchor 강제
- 산출물의 모든 sentence에 `[§n.m]` 또는 `[p.X ¶Y]` 인용 필수.
- 적용 기능: #02 요약, #03 번역, #05 유사 설명, #06 공백 진술,
  #07 권장, #08 의도 분류, #09 평가 항목, #10 모든 서브기능,
  #11 rationale.
- 미부착 sentence는 UI에 회색 처리 + 경고 배지.

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
- #02 요약 프리셋: TL;DR(1줄) / 문단(150-200자) / 페이지(800-1200자).
- 사용자 요청 길이 초과 시 post-trimmer로 컷.
- 100자 이상 연속 직역 금지 (§1.2 표절 경계).

§6.5 구조화 출력
- LLM JSON 출력 스키마: {"sentences": [{"text", "anchor",
  "verify_label", "confidence"}], "glossary_additions": []}.
- UI 렌더링·verify·glossary 갱신이 한 응답에서 일괄 처리됨.

다음 요청 블록의 지시에 따라 위 규약을 모두 만족하는 출력을 생성한다.
모든 문장 끝에 `[§n.m]` 형식의 anchor를 부착한다."""


def _angle_clause(angle: AnglePreset) -> str:
    return {
        AnglePreset.CONTRIBUTION: "기여(contribution) 중심으로, 새로움과 비교 우위를 명시한다.",
        AnglePreset.METHOD: "방법(method) 중심으로, 모델·알고리즘·데이터 처리를 명시한다.",
        AnglePreset.RESULT: "결과·실험(result/experiment) 중심으로, 수치와 비교 베이스라인을 명시한다.",
        AnglePreset.CRITICAL: "비판적 검토(critical) 관점으로, 가정·한계·재현 가능성 의문점을 명시한다.",
    }[angle]


def _length_clause(length: LengthPreset) -> str:
    return {
        LengthPreset.TLDR: "1문장(최대 80자) TL;DR로 요약한다.",
        LengthPreset.PARAGRAPH: "한 문단(150-200자) 한국어 요약을 작성한다.",
        LengthPreset.PAGE: "한 페이지(800-1200자) 한국어 요약을 작성한다.",
    }[length]


def build(
    paper: Paper,
    length: LengthPreset,
    angle: AnglePreset,
    structured_md: str,
    glossary_entries: list[GlossaryEntry] | None = None,
) -> LLMRequest:
    glossary_entries = glossary_entries or []
    glossary_text = (
        "세션 누적 glossary (English → 한국어):\n"
        + "\n".join(f"- {e.english} → {e.korean}" for e in glossary_entries)
        if glossary_entries
        else "세션 glossary 없음."
    )

    paper_block_text = (
        f"PAPER {paper.summary.id} — {paper.summary.title}\n\n"
        + structured_md
    )

    user_message = (
        f"요청: {_length_clause(length)} 관점: {_angle_clause(angle)} "
        f"길이 캡: {length.char_cap}자.\n\n"
        "응답 형식 (NDJSON, 한 줄에 JSON 객체 하나, 코드 펜스 없음):\n"
        '  {"type":"sentence","text":"...","anchor":"[§n.m]"}\n'
        "  ...sentences as separate lines...\n"
        '  {"type":"done","glossary_additions":[{"english":"...","korean":"..."}]}\n\n'
        "규칙:\n"
        "- 마크다운 코드 블록, ```json 펜스, 설명 텍스트를 모두 금지한다.\n"
        "- 각 줄은 독립적으로 파싱 가능한 단일 JSON 객체여야 한다.\n"
        "- 각 sentence의 anchor 필드는 반드시 [§n.m] 형식이다.\n"
        "- 마지막 줄은 type:'done'이며 glossary_additions를 포함한다."
    )

    return LLMRequest(
        system_blocks=[
            CachedBlock(name="conventions_v1", text=_CONVENTIONS_BLOCK),
            CachedBlock(name=f"paper_{paper.summary.id}", text=paper_block_text),
            CachedBlock(name="glossary_session", text=glossary_text),
        ],
        user_message=user_message,
        max_tokens=length.max_tokens,
        temperature=0.2,
        purpose="summary",
    )
