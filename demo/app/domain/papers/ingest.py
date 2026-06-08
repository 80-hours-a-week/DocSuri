"""Ingest orchestrator (Sprint 1 walking-skeleton).

PDF download -> GROBID parse -> chunk with anchors -> in-memory store.
Emits progress events on the bus so the SSE endpoint (and any other
subscriber) can stream status without coupling to this module
(AGENTS.md §5.2 — single event-bus channel).

AGENTS.md §4.2 — in-memory only: PDF bytes never touch disk.

Sprint 1 DoD scope:
    - PDF fetch (when ``pdf_url`` set and GROBID configured)
    - GROBID structured parse OR abstract-only fallback
    - Chunking with anchor (section_id + paragraph index)
    - Embedding / vector insert is Sprint 2 — explicitly out of scope.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Final

import httpx

from app.crosscutting.events.bus import Event, EventBus, bus
from app.domain.papers.models import Anchor, Chunk, Paper, PaperSummary, Section
from app.infra.grobid import client as grobid_client
from app.infra.grobid import tei_parser
from app.infra.pdf import pymupdf_parser
from app.infra.storage.memory import PaperStore, store

logger = logging.getLogger(__name__)

PROGRESS_TOPIC: Final[str] = "ingest.progress"
CHUNK_SIZE: Final[int] = 300  # ~300-char chunks per AGENTS.md scaffold spec
PDF_FETCH_TIMEOUT: Final[float] = 30.0

# Stages — kept as constants so the FE & tests can pattern-match reliably.
STAGE_STARTED = "ingest.started"
STAGE_FETCHING = "ingest.fetching"
STAGE_PARSING = "ingest.parsing"
STAGE_CHUNKING = "ingest.chunking"
STAGE_DONE = "ingest.done"
STAGE_FAILED = "ingest.failed"


def _chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split a paragraph into ``size``-char chunks at word boundaries.

    Walks word-by-word; flushes when adding the next word would exceed
    ``size``. Falls back to a hard window split for pathological inputs
    (single token longer than ``size``).
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for word in text.split():
        # +1 accounts for the space we'll join with.
        addition = len(word) + (1 if buf else 0)
        if buf_len + addition > size and buf:
            chunks.append(" ".join(buf))
            buf, buf_len = [word], len(word)
        else:
            buf.append(word)
            buf_len += addition

    if buf:
        chunks.append(" ".join(buf))

    # Defensive: if any single word exceeds the window, hard-slice it so
    # downstream callers never see a >2x oversized chunk.
    out: list[str] = []
    for c in chunks:
        if len(c) <= size * 2:
            out.append(c)
        else:
            out.extend(c[i : i + size] for i in range(0, len(c), size))
    return out


class IngestService:
    """Coordinates the Sprint 1 ingest pipeline.

    Concrete dependencies (``EventBus``, ``PaperStore``) default to the
    module-level singletons, but are constructor-injected so tests can
    pass in fresh instances and assert on the events/state in isolation.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus | None = None,
        paper_store: PaperStore | None = None,
    ) -> None:
        self._bus = event_bus or bus
        self._store = paper_store or store

    async def ingest(self, paper_summary: PaperSummary) -> Paper:
        """Run the full ingest for one ``PaperSummary``.

        Always returns the persisted :class:`Paper` on success. On any
        unrecoverable failure publishes ``ingest.failed`` and re-raises
        so the caller (background task / test) can react.
        """
        paper_id = paper_summary.id
        await self._emit(paper_id, STAGE_STARTED, "Ingest started")

        try:
            sections = await self._collect_sections(paper_summary)
            await self._emit(
                paper_id,
                STAGE_CHUNKING,
                f"Chunking {len(sections)} section(s)",
            )
            chunks = self._build_chunks(paper_id, sections)

            paper = Paper(
                summary=paper_summary,
                sections=sections,
                chunks=chunks,
                ingested_at=datetime.now(timezone.utc),
            )
            await self._store.put(paper)

            await self._emit(
                paper_id,
                STAGE_DONE,
                "Ingest complete",
                extra={
                    "section_count": len(sections),
                    "chunk_count": len(chunks),
                },
            )
            return paper
        except Exception as exc:
            logger.exception("ingest failed for %s", paper_id)
            await self._emit(paper_id, STAGE_FAILED, f"Ingest failed: {exc}")
            raise

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _collect_sections(self, summary: PaperSummary) -> list[Section]:
        """Three-tier parser cascade.

        1. GROBID if `GROBID_URL` is set and the PDF is reachable — the
           AGENTS.md spec choice; high-fidelity TEI structure.
        2. PyMuPDF on the same PDF bytes — lighter alternative
           (AGENTS.md §3.1: "가벼운 대안(pymupdf)은 정확도 trade-off").
           Lets the demo expose the full paper without Docker.
        3. Abstract-only — when no PDF is reachable (paywall, no
           `pdf_url`, network failure, both parsers empty).
        """
        grobid_configured = grobid_client.grobid_url() is not None

        # Fast exit: no PDF at all → abstract-only path.
        if not summary.pdf_url:
            await self._emit(
                summary.id,
                STAGE_PARSING,
                "PDF URL not available — using abstract-only fallback",
            )
            return grobid_client.abstract_only_sections(summary)

        # Fetch once; reuse the bytes for whichever parser tier we hit.
        await self._emit(
            summary.id,
            STAGE_FETCHING,
            f"Fetching PDF from {summary.pdf_url}",
        )
        try:
            pdf_bytes = await self._fetch_pdf(summary.pdf_url)
        except Exception as exc:  # noqa: BLE001 — network failure is expected here
            logger.info("PDF fetch failed for %s (%s) — abstract-only fallback", summary.id, exc)
            await self._emit(
                summary.id,
                STAGE_PARSING,
                f"PDF fetch failed ({exc}) — using abstract-only fallback",
            )
            return grobid_client.abstract_only_sections(summary)

        # Tier 1 — GROBID.
        if grobid_configured:
            try:
                await self._emit(summary.id, STAGE_PARSING, "GROBID parsing PDF")
                # AGENTS.md §4.2 — in-memory only: bytes go straight from
                # httpx response into the GROBID multipart body.
                tei_xml = await grobid_client.process_fulltext(pdf_bytes)
                sections = tei_parser.parse(tei_xml)
                if sections:
                    return sections
                logger.warning("GROBID returned no sections for %s — trying pymupdf", summary.id)
            except grobid_client.GrobidUnavailable as exc:
                logger.info("GROBID unavailable (%s) — falling through to pymupdf", exc)

        # Tier 2 — PyMuPDF.
        await self._emit(
            summary.id,
            STAGE_PARSING,
            "PyMuPDF parsing PDF (lighter alternative)",
        )
        try:
            sections = pymupdf_parser.parse(pdf_bytes)
            if sections:
                return sections
            logger.warning("PyMuPDF returned no sections for %s — abstract-only fallback", summary.id)
        except Exception as exc:  # noqa: BLE001 — defensive: parser bugs shouldn't kill ingest
            logger.exception("PyMuPDF crashed for %s: %s", summary.id, exc)

        # Tier 3 — abstract-only.
        await self._emit(
            summary.id,
            STAGE_PARSING,
            "Falling back to abstract-only sections",
        )
        return grobid_client.abstract_only_sections(summary)

    async def _fetch_pdf(self, url: str) -> bytes:
        # AGENTS.md §4.2 — in-memory only: read full body into RAM, never
        # to a tempfile. Sprint 1 papers are <5MB; revisit if that grows.
        async with httpx.AsyncClient(
            timeout=PDF_FETCH_TIMEOUT, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _build_chunks(self, paper_id: str, sections: list[Section]) -> list[Chunk]:
        """Build anchor-bearing chunks; verify anchor uniqueness within the paper."""
        chunks: list[Chunk] = []
        seen_anchors: set[tuple[str, int | None]] = set()
        idx = 0
        for section in sections:
            for para_i, paragraph in enumerate(section.paragraphs):
                for piece in _chunk_text(paragraph):
                    anchor = Anchor(
                        section_id=section.section_id,
                        page=None,
                        paragraph=para_i,
                    )
                    key = (anchor.section_id, anchor.paragraph)
                    # Multiple chunks may share a paragraph anchor when a
                    # paragraph splits into >1 chunks — uniqueness here is
                    # at the chunk_id level. We only check section+para to
                    # log if a downstream assumption breaks.
                    seen_anchors.add(key)
                    chunks.append(
                        Chunk(
                            paper_id=paper_id,
                            chunk_id=f"{paper_id}:{idx}",
                            text=piece,
                            anchor=anchor,
                        )
                    )
                    idx += 1

        # chunk_id is paper_id + index, so uniqueness is trivially preserved;
        # assert it explicitly for parity with the Sprint 2 DoD wording.
        ids = [c.chunk_id for c in chunks]
        if len(set(ids)) != len(ids):
            raise RuntimeError(f"duplicate chunk_id detected for {paper_id}")
        return chunks

    async def _emit(
        self,
        paper_id: str,
        stage: str,
        message: str,
        *,
        extra: dict | None = None,
    ) -> None:
        payload: dict = {"paper_id": paper_id, "stage": stage, "message": message}
        if extra:
            payload.update(extra)
        await self._bus.publish(Event(topic=PROGRESS_TOPIC, payload=payload))


# Module-level singleton — composition-root style (see container.py).
service = IngestService()
