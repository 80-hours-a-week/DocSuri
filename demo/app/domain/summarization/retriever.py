"""Retriever — paper_id → (Paper, structured-md transcript).

Sprint 1 simply concatenates sections from the in-memory store. Sprint 2
will add Qdrant ANN chunk fetch for papers whose full text overflows
the context budget.
"""

from __future__ import annotations

from app.domain.papers.models import Paper
from app.infra.storage.memory import store


async def fetch(paper_id: str, *, section_id: str | None = None) -> tuple[Paper, str]:
    """Return the paper and its flattened structured-md transcript.

    Raises `KeyError` if the paper has not been ingested (#01b owns the
    write path; this read path simply surfaces the absence to the caller
    so the API can return 404).

    When ``section_id`` is provided, the transcript is restricted to that
    single section (and the title). Useful for the FE's "이 섹션만 요약"
    button — the LLM still sees the paper title for context but only
    that section's paragraphs as evidence.
    """

    paper = await store.get(paper_id)
    if paper is None:
        raise KeyError(paper_id)

    lines: list[str] = [f"# {paper.summary.title}"]

    if section_id is not None:
        target = next((s for s in paper.sections if s.section_id == section_id), None)
        if target is None:
            raise KeyError(f"section {section_id!r} not in paper {paper_id!r}")
        lines.append(f"\n## §{target.section_id} {target.title}\n")
        for para in target.paragraphs:
            lines.append(para)
            lines.append("")
        return paper, "\n".join(lines)

    if paper.summary.abstract:
        lines.append("\n## §abstract\n")
        lines.append(paper.summary.abstract)

    for section in paper.sections:
        lines.append(f"\n## §{section.section_id} {section.title}\n")
        for para in section.paragraphs:
            lines.append(para)
            lines.append("")

    return paper, "\n".join(lines)
