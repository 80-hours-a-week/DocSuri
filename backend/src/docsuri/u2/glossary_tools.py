"""Glossary helpers for U2 prompt grounding."""

from __future__ import annotations

import re

from docsuri.u0.ports import Glossary

from .models import VocabExplanation


def glossary_hits(text: str, glossary: Glossary) -> list[VocabExplanation]:
    seen: set[str] = set()
    hits: list[VocabExplanation] = []
    for candidate in _candidate_terms(text):
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        translation = glossary.lookup(candidate)
        if translation is not None:
            hits.append(VocabExplanation.from_translation(translation))
    return hits


def _candidate_terms(text: str) -> list[str]:
    ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z][A-Za-z0-9-]*){0,4}", text)
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", text)
    candidates = ascii_terms + words
    # Common abbreviations are useful in prompts even when the seed glossary misses them.
    candidates.extend(re.findall(r"\b[A-Z]{2,}\b", text))
    candidates.sort(key=len, reverse=True)
    return candidates
