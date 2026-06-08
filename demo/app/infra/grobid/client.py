"""GROBID HTTP adapter (AGENTS.md §4.2 — in-memory only).

Posts PDF bytes to a running GROBID service at `GROBID_URL`
(default endpoint: `/api/processFulltextDocument`) and returns the TEI XML
body as a string.

Fallback behaviour (Sprint 1 walking-skeleton):
    If `GROBID_URL` is unset OR the service is unreachable, the caller
    falls back to an abstract-only ``Paper`` construction — see
    :func:`abstract_only_sections`. This keeps the demo runnable without
    a Docker GROBID container.
"""

from __future__ import annotations

import logging
import os
import re

import httpx

from app.domain.papers.models import PaperSummary, Section

logger = logging.getLogger(__name__)

GROBID_ENV = "GROBID_URL"
GROBID_PATH = "/api/processFulltextDocument"
DEFAULT_TIMEOUT = 60.0  # GROBID full-text parse can be slow on big PDFs


class GrobidUnavailable(RuntimeError):
    """Raised when GROBID is not configured or not reachable.

    The orchestrator catches this and falls back to abstract-only
    construction. Distinguishing this from generic exceptions makes the
    fallback intent explicit in code.
    """


def grobid_url() -> str | None:
    """Return the configured GROBID base URL, or ``None`` if disabled.

    Centralised so tests can monkeypatch via env without reaching into
    multiple modules.
    """

    url = os.getenv(GROBID_ENV)
    if not url:
        return None
    return url.rstrip("/")


async def process_fulltext(pdf_bytes: bytes, *, timeout: float = DEFAULT_TIMEOUT) -> str:
    """POST ``pdf_bytes`` to GROBID and return TEI XML.

    The PDF bytes are streamed in-memory (AGENTS.md §4.2 — in-memory only);
    no temporary files are written. Raises :class:`GrobidUnavailable` if
    GROBID isn't configured or the upstream call fails.
    """

    base = grobid_url()
    if not base:
        raise GrobidUnavailable("GROBID_URL not set")

    files = {"input": ("paper.pdf", pdf_bytes, "application/pdf")}
    # AGENTS.md §4.2 — in-memory only: pdf_bytes flows from httpx response
    # to GROBID multipart upload without ever touching disk.
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{base}{GROBID_PATH}", files=files)
            response.raise_for_status()
            return response.text
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("GROBID call failed: %s", exc)
        raise GrobidUnavailable(str(exc)) from exc


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def abstract_only_sections(summary: PaperSummary) -> list[Section]:
    """Synthesise a minimal :class:`Section` list from a search-result abstract.

    Used when GROBID is unavailable. The abstract is split on sentence
    boundaries so the downstream chunker still produces multiple anchored
    paragraphs — preserving the "anchor + chunk" contract that the rest
    of the pipeline relies on, even when full-text parsing is skipped.
    """

    abstract = (summary.abstract or "").strip()
    if not abstract:
        # No abstract either — still emit a single empty section so the
        # ``Paper`` is well-formed and the FE can render an "empty" state.
        return [Section(section_id="abstract", title="Abstract", paragraphs=[])]

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(abstract) if s.strip()]
    return [
        Section(
            section_id="abstract",
            title="Abstract",
            paragraphs=sentences or [abstract],
        )
    ]
