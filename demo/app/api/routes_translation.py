"""#03 Translation HTTP surface + session glossary listing."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.container import glossary, llm
from app.domain.papers.models import GlossaryEntry
from app.domain.translation.service import TranslationResult, TranslationService

router = APIRouter(tags=["translation"])


class TranslateRequest(BaseModel):
    paper_id: str
    section_id: str
    char_start: int
    char_end: int
    session_id: str = "default"


@router.post("/translate", response_model=TranslationResult)
async def translate(req: TranslateRequest) -> TranslationResult:
    service = TranslationService(llm=llm(), glossary=glossary())
    try:
        return await service.translate(
            paper_id=req.paper_id,
            section_id=req.section_id,
            char_start=req.char_start,
            char_end=req.char_end,
            session_id=req.session_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"span not found: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/glossary/{session_id}", response_model=list[GlossaryEntry])
async def list_glossary(session_id: str) -> list[GlossaryEntry]:
    return await glossary().list_for_session(session_id)
