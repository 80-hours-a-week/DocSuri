from __future__ import annotations

from docsuri_shared.dtos import DocModel


def build_evidence_extraction_prompt(
    topic: str,
    doc_models: list[tuple[str, DocModel]],  # (paper_id, DocModel)
) -> tuple[str, str]:
    """DocModel 블록 → EvidenceItem 추출 LLM 프롬프트."""
    system = (
        'You are a scientific evidence extractor. '
        'Your task is to extract evidence items from the provided paper content.\n\n'
        'STRICT RULES:\n'
        '1. Extract statements ONLY from the provided paper text. '
        'Do NOT generate new statements or paraphrase beyond the source text.\n'
        '2. Each statement must be directly traceable to a specific paper and block.\n'
        '3. Return valid JSON only. No explanations outside the JSON.\n'
        '4. If no relevant evidence exists, return {"items": []}.'
    )

    papers_text = _format_papers(doc_models)

    user = (
        f'Topic: {topic}\n\n'
        f'Papers:\n{papers_text}\n\n'
        'Extract evidence items relevant to the topic. '
        'For each item, identify which papers support or conflict with the statement.\n\n'
        'Return JSON in this exact format:\n'
        '{\n'
        '  "items": [\n'
        '    {\n'
        '      "statement": "<extracted statement from paper text>",\n'
        '      "supporting": [\n'
        '        {"paperId": "<arxiv_id>", "recordRef": "<record_ref>", "quote": "<short quote>"}\n'
        '      ],\n'
        '      "conflicting": [\n'
        '        {"paperId": "<arxiv_id>", "recordRef": "<record_ref>", "quote": "<short quote>"}\n'
        '      ]\n'
        '    }\n'
        '  ]\n'
        '}'
    )

    return system, user


def _format_papers(doc_models: list[tuple[str, DocModel]]) -> str:
    parts = []
    for paper_id, doc_model in doc_models:
        title = getattr(doc_model, 'title', '') or paper_id
        blocks_text = _extract_block_text(doc_model)
        parts.append(f'[PAPER:{paper_id}] {title}\n{blocks_text}')
    return '\n\n'.join(parts)


def _extract_block_text(doc_model: DocModel) -> str:
    lines = []
    sections = getattr(doc_model, 'sections', None) or []
    for section in sections:
        heading = getattr(section, 'heading', '') or ''
        if heading:
            lines.append(f'## {heading}')
        blocks = getattr(section, 'blocks', None) or []
        for block in blocks:
            text = getattr(block, 'text', '') or ''
            if text:
                lines.append(text[:2000])
    return '\n'.join(lines)[:8000]
