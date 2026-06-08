from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import create_pool
from app.models import (
    GlossaryTerm,
    SummaryRequest,
    SummaryResponse,
    TranslateRequest,
    TranslateResponse,
)
from app.repositories import DemoPaperRepository, PaperRepository, PostgresPaperRepository
from app.services.glossary import GlossaryStore
from app.services.llm import build_llm_client
from app.services.processing import (
    build_summary_sentences,
    mask_math,
    merge_glossary,
    resolve_source_span,
    restore_math,
    split_translation_units,
)

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with create_pool(settings) as pool:
        if pool is None:
            repository: PaperRepository = DemoPaperRepository()
        else:
            repository = PostgresPaperRepository(pool, settings)
        app.state.settings = settings
        app.state.repository = repository
        app.state.llm = build_llm_client(settings)
        app.state.glossary = GlossaryStore()
        yield


app = FastAPI(title="DocSuri Summary & Translation API", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def repository(request: Request) -> PaperRepository:
    return request.app.state.repository


def glossary(request: Request) -> GlossaryStore:
    return request.app.state.glossary


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    repo_type = type(request.app.state.repository).__name__
    provider = "anthropic" if settings.use_anthropic else "mock"
    return {"status": "ok", "repository": repo_type, "llm_provider": provider}


@app.get("/api/papers")
async def list_papers(request: Request):
    try:
        return await repository(request).list_papers()
    except Exception as exc:
        logger.exception("Failed to list papers")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/papers/{paper_id}")
async def get_paper(paper_id: str, request: Request):
    try:
        paper = await repository(request).get_paper(paper_id)
        preview = paper.text[:12000]
        return {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "text": preview,
            "text_length": len(paper.text),
            "chunks": paper.chunks[:50],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch paper")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/summarize", response_model=SummaryResponse)
async def summarize(payload: SummaryRequest, request: Request) -> SummaryResponse:
    try:
        paper = await repository(request).get_paper(payload.paper_id)
        session_glossary = glossary(request).lookup(payload.session_id, paper.text)
        raw_sentences = await request.app.state.llm.summarize(
            paper=paper,
            length_preset=payload.length_preset,
            angle_preset=payload.angle_preset,
            glossary=session_glossary,
        )
        summary_sentences = build_summary_sentences(raw_sentences, paper)
        all_terms = merge_glossary(glossary(request).list_terms(payload.session_id), session_glossary)
        return SummaryResponse(
            paper_id=paper.id,
            title=paper.title,
            length_preset=payload.length_preset,
            angle_preset=payload.angle_preset,
            sentences=summary_sentences,
            glossary=all_terms,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Summary failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest, request: Request) -> TranslateResponse:
    try:
        paper = await repository(request).get_paper(payload.paper_id)
        source_text = resolve_source_span(paper, payload.selected_text, payload.char_start, payload.char_end)
        masked_text, math_replacements = mask_math(source_text)
        found_terms = glossary(request).lookup(payload.session_id, source_text)
        session_terms = merge_glossary(glossary(request).list_terms(payload.session_id), found_terms)
        translated = await request.app.state.llm.translate(paper=paper, source_text=masked_text, glossary=session_terms)
        translated = restore_math(translated, math_replacements)
        units = split_translation_units(source_text, translated, paper)
        return TranslateResponse(
            paper_id=paper.id,
            title=paper.title,
            units=units,
            glossary=session_terms,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/glossary/{session_id}", response_model=list[GlossaryTerm])
async def get_glossary(session_id: str, request: Request) -> list[GlossaryTerm]:
    return glossary(request).list_terms(session_id)
