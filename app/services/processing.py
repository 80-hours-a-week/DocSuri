from __future__ import annotations

import re

from app.models import (
    GlossaryTerm,
    PaperChunk,
    PaperDocument,
    SummarySentence,
    TranslationUnit,
)
from app.services.anchors import anchors_in_text, evidence_for_anchor, split_sentences, verify_sentence

MATH_RE = re.compile(r"(\$\$.*?\$\$|\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\))", flags=re.DOTALL)


def build_summary_sentences(sentences: list[str], paper: PaperDocument) -> list[SummarySentence]:
    result: list[SummarySentence] = []
    for sentence in sentences:
        anchors = anchors_in_text(sentence)
        result.append(
            SummarySentence(
                text=sentence,
                anchors=anchors,
                verification=verify_sentence(sentence, paper),
            )
        )
    return result


def resolve_source_span(paper: PaperDocument, selected_text: str | None, char_start: int | None, char_end: int | None) -> str:
    if selected_text and selected_text.strip():
        return selected_text.strip()
    if char_start is None or char_end is None:
        raise ValueError("selected_text or both char_start/char_end are required.")
    if char_start < 0 or char_end <= char_start or char_end > len(paper.text):
        raise ValueError("Invalid character span.")
    return paper.text[char_start:char_end].strip()


def source_anchor_for_span(
    paper: PaperDocument,
    source_text: str,
    fallback: str = "§0.0",
    context_chunks: list[PaperChunk] | None = None,
) -> str:
    normalized_source = _normalize_for_match(source_text)
    for chunk in [*(context_chunks or []), *paper.chunks]:
        normalized_chunk = _normalize_for_match(chunk.text)
        if source_text in chunk.text or chunk.text in source_text:
            return chunk.anchor
        if normalized_source and (
            normalized_source in normalized_chunk
            or normalized_chunk in normalized_source
            or _token_overlap_score(normalized_source, normalized_chunk) >= 3
        ):
            return chunk.anchor
    index = paper.text.find(source_text)
    if index >= 0:
        prefix = paper.text[:index]
        anchors = anchors_in_text(prefix)
        if anchors:
            return anchors[-1]
    for anchor in anchors_in_text(source_text):
        return anchor
    return fallback


def mask_math(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        key = f"__MATH_{len(replacements)}__"
        replacements[key] = match.group(0)
        return key

    return MATH_RE.sub(replace, text), replacements


def restore_math(text: str, replacements: dict[str, str]) -> str:
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def split_translation_units(
    source_text: str,
    translated_text: str,
    paper: PaperDocument,
    context_chunks: list[PaperChunk] | None = None,
) -> list[TranslationUnit]:
    source_sentences = split_sentences(source_text) or [source_text]
    translated_sentences = split_sentences(translated_text) or [translated_text]
    if len(translated_sentences) != len(source_sentences):
        translated_sentences = [translated_text]
        source_sentences = [source_text]

    units: list[TranslationUnit] = []
    for idx, source in enumerate(source_sentences):
        translated = translated_sentences[idx] if idx < len(translated_sentences) else translated_text
        anchor = source_anchor_for_span(paper, source, context_chunks=context_chunks)
        verification = verify_sentence(f"{source} [{anchor}]", paper)
        units.append(
            TranslationUnit(
                anchor=anchor,
                source_text=source,
                translated_text=translated,
                verification=verification,
            )
        )
    return units


def merge_glossary(existing: list[GlossaryTerm], new_terms: list[GlossaryTerm]) -> list[GlossaryTerm]:
    merged: dict[str, GlossaryTerm] = {term.source: term for term in existing}
    for term in new_terms:
        merged[term.source] = term
    return sorted(merged.values(), key=lambda term: term.source)


def _normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _token_overlap_score(left: str, right: str) -> int:
    left_terms = set(re.findall(r"[a-z][a-z0-9-]{3,}", left))
    right_terms = set(re.findall(r"[a-z][a-z0-9-]{3,}", right))
    return len(left_terms & right_terms)
