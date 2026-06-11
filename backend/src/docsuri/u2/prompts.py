"""Prompt builders for U2 Comprehend."""

from __future__ import annotations

from docsuri.u0.ports import Persona

from .models import PaperText, VocabExplanation


def build_summary_prompt(
    paper_text: PaperText,
    mode: Persona,
    glossary_hits: list[VocabExplanation],
    compressed_text: str,
) -> str:
    glossary_block = _glossary_block(glossary_hits)
    if mode == "pro":
        policy = (
            "전문 모드: 학술 전문 어휘의 영어 원형을 보존하고 한국어 표현을 병기한다. "
            "출력은 반드시 연구 질문, 방법, 결과, 한계 네 섹션으로 나눈다."
        )
    else:
        policy = (
            "학부 모드: 학부 1~2학년이 이해할 쉬운 한국어로 쓴다. "
            "약어는 첫 등장 시 괄호로 풀고, 핵심 수식은 자연어 한 줄 해석을 붙인다. "
            "평균 문장은 22어절 이하로 유지한다."
        )
    return f"""DocSuri U2 Comprehend 요약 요청
논문 ID: {paper_text.paper_id}
제목: {paper_text.title}
모드: {mode}
정책: {policy}
용어 사전:
{glossary_block}

본문:
{compressed_text}

출력 형식:
연구 질문: ...
방법: ...
결과: ...
한계: ...
"""


def build_translation_prompt(
    source_excerpt: str, glossary_hits: list[VocabExplanation]
) -> str:
    return f"""DocSuri U2 부분 번역 요청
아래 영문 단락을 한국어로 번역하라. 용어 사전 항목은 반드시 같은 번역으로 사용한다.

용어 사전:
{_glossary_block(glossary_hits)}

단락:
{source_excerpt}
"""


def build_figure_prompt(caption: str, context: str) -> str:
    return f"""DocSuri U2 시각자료 설명 요청
캡션과 주변 문맥을 바탕으로 그림/표의 역할을 한국어 1~2문장으로 설명하라.

캡션:
{caption}

주변 문맥:
{context}
"""


def _glossary_block(hits: list[VocabExplanation]) -> str:
    if not hits:
        return "- 사전 적중 없음"
    return "\n".join(f"- {hit.term}: {hit.ko} ({hit.note})" for hit in hits)
