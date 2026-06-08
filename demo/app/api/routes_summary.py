"""#02 Summarization HTTP surface.

Thin route layer — delegates to `SummaryService` (composed via the
container so the LLM/verifier/glossary ports stay swappable).

Two endpoints:

- ``POST /api/summary`` — one-shot JSON. Kept for tests and clients that
  prefer a single response. Still backed by the §6.5-parsing path.
- ``GET  /api/summary/stream`` — SSE; emits ``event: sentence`` per Sentence
  the moment it's verified, then ``event: done`` with glossary additions.
  Used by the FE for progressive rendering.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.container import glossary, llm, verifier
from app.domain.summarization.presets import AnglePreset, LengthPreset
from app.domain.summarization.service import (
    SummaryResult,
    SummaryService,
    SummaryStreamDone,
    SummaryStreamFailure,
    SummaryStreamSentence,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["summary"])


class SummaryRequest(BaseModel):
    paper_id: str
    length: LengthPreset = LengthPreset.PARAGRAPH
    angle: AnglePreset = AnglePreset.CONTRIBUTION
    session_id: str = "default"


@router.post("/summary", response_model=SummaryResult)
async def summarize(req: SummaryRequest) -> SummaryResult:
    service = SummaryService(llm=llm(), verifier=verifier(), glossary=glossary())
    try:
        return await service.summarize(
            paper_id=req.paper_id,
            length=req.length,
            angle=req.angle,
            session_id=req.session_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"paper not ingested: {exc}") from exc


@router.get("/summary/stream")
async def summarize_stream(
    paper_id: str = Query(..., min_length=1),
    length: LengthPreset = Query(LengthPreset.PARAGRAPH),
    angle: AnglePreset = Query(AnglePreset.CONTRIBUTION),
    session_id: str = Query("default"),
    section_id: str | None = Query(None),
) -> StreamingResponse:
    """SSE: progressive sentence emission for the demo UI.

    Using GET + query params so `EventSource` can subscribe directly —
    the EventSource API does not support POST bodies. The arguments are
    small and non-sensitive (no payload data leaks via URL).
    """

    service = SummaryService(llm=llm(), verifier=verifier(), glossary=glossary())

    async def event_source() -> AsyncIterator[str]:
        try:
            async for evt in service.summarize_stream(
                paper_id=paper_id,
                length=length,
                angle=angle,
                session_id=session_id,
                section_id=section_id,
            ):
                if isinstance(evt, SummaryStreamSentence):
                    payload = {
                        "index": evt.index,
                        "sentence": evt.sentence.model_dump(),
                    }
                    yield f"event: sentence\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif isinstance(evt, SummaryStreamDone):
                    payload = {
                        "model": evt.model,
                        "latency_ms": evt.latency_ms,
                        "glossary_additions": [g.model_dump() for g in evt.glossary_additions],
                    }
                    yield f"event: done\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break
                elif isinstance(evt, SummaryStreamFailure):
                    yield (
                        "event: failed\n"
                        f"data: {json.dumps({'message': evt.message}, ensure_ascii=False)}\n\n"
                    )
                    break
        except KeyError as exc:
            logger.warning("summary stream KeyError: %s", exc)
            yield (
                "event: failed\n"
                f"data: {json.dumps({'message': f'paper not ingested: {exc}'}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
