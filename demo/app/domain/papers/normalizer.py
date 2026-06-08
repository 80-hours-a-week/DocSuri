"""Query Normalizer (AGENTS.md §3.2 #01, feature-specs/01 §3 Query Normalizer).

Sprint 1 walking-skeleton scope:
- Strip / lowercase the raw user query.
- Rule-based field detection ("nlp" → `cs.CL`, "vision" → `cs.CV`, ...).
- When `expand=True`, ask the LLM port (`app.container.llm()`) for a
  short synonym/field-filter expansion. The mock LLM returns a passthrough,
  so behaviour is deterministic in tests.

Returns a `NormalizedQuery` whose `for_arxiv()` string is what
`ArxivAdapter` sends to the arXiv API.
"""

from __future__ import annotations

import logging
import re
import string
from dataclasses import dataclass, field

from app.container import llm as get_llm
from app.infra.llm.protocol import CachedBlock, LLMRequest

logger = logging.getLogger(__name__)


# Coarse keyword → arXiv primary category map. Intentionally small — the LLM
# (or future RAG, Sprint 2) handles the long tail.
_FIELD_KEYWORDS: dict[str, str] = {
    "nlp": "cs.CL",
    "natural language": "cs.CL",
    "language model": "cs.CL",
    "transformer": "cs.CL",
    "vision": "cs.CV",
    "image": "cs.CV",
    "robot": "cs.RO",
    "reinforcement": "cs.LG",
    "machine learning": "cs.LG",
    "deep learning": "cs.LG",
    "graph neural": "cs.LG",
    "security": "cs.CR",
    "cryptograph": "cs.CR",
}

_PUNCT_TABLE = str.maketrans({c: " " for c in string.punctuation if c not in "._-"})


@dataclass
class NormalizedQuery:
    """Output of the normalizer — what `ArxivAdapter` actually sends."""

    raw: str
    canonical: str  # lowercased + de-punctuated user terms
    fields: list[str] = field(default_factory=list)  # e.g. ["cs.CL"]
    synonyms: list[str] = field(default_factory=list)
    expanded: bool = False

    def for_arxiv(self) -> str:
        """Build an arXiv `search_query` expression.

        Joins user terms + synonyms with OR for recall, optionally AND-ed
        with category filters. arXiv tolerates plain text in `search_query`
        so we keep this readable rather than perfectly escaped.
        """
        terms = [self.canonical, *self.synonyms]
        term_clause = " OR ".join(f"all:{t}" for t in terms if t)
        if not term_clause:
            term_clause = f"all:{self.raw}"
        if not self.fields:
            return term_clause
        cat_clause = " OR ".join(f"cat:{c}" for c in self.fields)
        return f"({term_clause}) AND ({cat_clause})"


def _strip_punct(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(_PUNCT_TABLE)).strip()


def _detect_fields(text: str) -> list[str]:
    found: list[str] = []
    for needle, cat in _FIELD_KEYWORDS.items():
        if needle in text and cat not in found:
            found.append(cat)
    return found


async def normalize(query: str, *, expand: bool = False) -> NormalizedQuery:
    """Normalize a user query; optionally LLM-expand synonyms.

    Mock LLM passes through, so unit tests can assert deterministic output
    without needing `ANTHROPIC_API_KEY`. Live LLM gets a tightly-scoped
    prompt; if it fails or returns an unparseable shape, we fall back to
    the rule-based result rather than raising.
    """
    canonical = _strip_punct(query.lower())
    fields = _detect_fields(canonical)
    nq = NormalizedQuery(raw=query, canonical=canonical, fields=fields)

    if not expand:
        return nq

    try:
        resp = await get_llm().complete(
            LLMRequest(
                system_blocks=[
                    CachedBlock(
                        name="normalizer.system",
                        text=(
                            "You expand academic-search queries. Given a user query, "
                            "return up to 5 synonyms or related search terms, one per "
                            "line, plain text, no commentary."
                        ),
                    )
                ],
                user_message=f"Query: {query}\nReturn synonyms:",
                max_tokens=120,
                temperature=0.1,
                purpose="normalize",
            )
        )
        nq.synonyms = _parse_synonyms(resp.text, exclude=canonical)
        nq.expanded = True
    except Exception:  # noqa: BLE001 — normalizer is best-effort
        logger.warning("normalizer LLM expansion failed, falling back", exc_info=True)
    return nq


def _parse_synonyms(text: str, *, exclude: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        s = _strip_punct(line.lower())
        if not s or s == exclude or s in out:
            continue
        out.append(s)
        if len(out) >= 5:
            break
    return out
