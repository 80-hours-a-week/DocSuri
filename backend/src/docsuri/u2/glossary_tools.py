"""Glossary helpers for U2 prompt grounding."""

from __future__ import annotations

import re

from docsuri.u0.ports import Glossary

from .models import VocabExplanation


DEFAULT_MAX_CANDIDATES = 256


def glossary_hits(
    text: str,
    glossary: Glossary,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> list[VocabExplanation]:
    seen: set[str] = set()
    hits: list[VocabExplanation] = []
    for candidate in _candidate_terms(text)[:max_candidates]:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        translation = glossary.lookup(candidate)
        if translation is not None:
            hits.append(VocabExplanation.from_translation(translation))
    return hits


def _candidate_terms(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", text)
    candidates: list[str] = []
    # Common abbreviations are useful in prompts even when the seed glossary misses them.
    candidates.extend(re.findall(r"\b[A-Z]{2,}\b", text))
    candidates.extend(_edge_ordered(words))
    for size in range(5, 1, -1):
        ngrams = [
            " ".join(words[idx : idx + size])
            for idx in range(0, max(0, len(words) - size + 1))
        ]
        for candidate in _edge_ordered(ngrams):
            candidates.append(candidate)
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _edge_ordered(items: list[str]) -> list[str]:
    """Prioritize both document head and tail before middle content.

    U2 compresses long papers by preserving the beginning and end. If we only
    scan candidates in natural order, the lookup limit can be exhausted by head
    filler terms before glossary terms in the preserved tail are checked.
    """

    ordered: list[str] = []
    left = 0
    right = len(items) - 1
    while left <= right:
        ordered.append(items[left])
        if left != right:
            ordered.append(items[right])
        left += 1
        right -= 1
    return ordered
