"""Ingest API routes (Sprint 1 walking-skeleton).

Three endpoints:

* ``POST /api/ingest`` — body is a full :class:`PaperSummary`; kicks
  off a background ingest and returns the ``stream_url`` the FE polls.
* ``GET /api/ingest/{paper_id}/events`` — Server-Sent Events stream of
  progress for one paper, filtered from the shared
  ``ingest.progress`` bus topic.
* ``GET /api/papers/{paper_id}`` — returns the persisted :class:`Paper`
  once ingest is complete (404 until then).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.crosscutting.events.bus import bus
from app.domain.papers.ingest import (
    PROGRESS_TOPIC,
    STAGE_DONE,
    STAGE_FAILED,
)
from app.domain.papers.ingest import (
    service as ingest_service,
)
from app.domain.papers.models import Paper, PaperSummary
from app.infra.storage.memory import store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def start_ingest(summary: PaperSummary) -> dict:
    """Kick off ingest in the background and return the stream URL.

    We don't await the ingest — the FE consumes progress via SSE. Errors
    inside the background task are surfaced through the bus as
    ``ingest.failed`` events, not via this HTTP response (which only
    confirms scheduling).
    """
    logger.info("scheduling ingest for %s", summary.id)
    asyncio.create_task(_run_ingest_safely(summary))
    return {
        "paper_id": summary.id,
        "stream_url": f"/api/ingest/{summary.id}/events",
    }


async def _run_ingest_safely(summary: PaperSummary) -> None:
    """Background-task wrapper that swallows exceptions after logging.

    The ingest service has already published an ``ingest.failed`` event
    by the time it re-raises, so logging here is enough — we don't want
    asyncio to surface an unhandled task exception during shutdown.
    """
    try:
        await ingest_service.ingest(summary)
    except Exception:
        logger.exception("background ingest crashed for %s", summary.id)


@router.get("/ingest/{paper_id}/events")
async def stream_events(paper_id: str) -> StreamingResponse:
    """SSE endpoint — filters the global progress topic to this paper."""
    return StreamingResponse(
        _sse_iter(paper_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable buffering on common proxies
        },
    )


async def _sse_iter(paper_id: str) -> AsyncIterator[str]:
    """Yield SSE-formatted lines for events matching ``paper_id``.

    Emits two named events:
    * ``event: progress`` for all stages
    * ``event: done`` for terminal stages (``ingest.done`` /
      ``ingest.failed``) — also closes the stream so the FE can release
      the EventSource cleanly.
    """
    async for event in bus.stream(PROGRESS_TOPIC):
        if event.payload.get("paper_id") != paper_id:
            continue

        stage = event.payload.get("stage")
        data = json.dumps(event.payload)

        if stage in (STAGE_DONE, STAGE_FAILED):
            yield f"event: done\ndata: {data}\n\n"
            break

        yield f"event: progress\ndata: {data}\n\n"


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str) -> Paper:
    """Return the persisted :class:`Paper`; 404 if ingest hasn't finished yet."""
    paper = await store.get(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"paper {paper_id} not yet ingested")
    return paper
