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
from app.repositories import PostgresPaperRepository
from app.services.embedding import build_embedding_client
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
        app.state.settings = settings
        app.state.repository = PostgresPaperRepository(pool, settings)
        app.state.embedding = build_embedding_client(settings)
        app.state.llm = build_llm_client(settings)
        app.state.glossary = GlossaryStore()
        yield


app = FastAPI(title="DocSuri Summary & Translation API", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def repository(request: Request) -> PostgresPaperRepository:
    return request.app.state.repository


def glossary(request: Request) -> GlossaryStore:
    return request.app.state.glossary


async def retrieve_context(request: Request, paper_id: str, query_text: str):
    settings = request.app.state.settings
    query_embedding = await request.app.state.embedding.embed_query(query_text)
    return await repository(request).retrieve_relevant_chunks(
        paper_id=paper_id,
        query_embedding=query_embedding,
        top_k=settings.retrieval_top_k,
    )


def summary_retrieval_query(paper_title: str, length_preset: str, angle_preset: str) -> str:
    angle_terms = {
        "contribution": "core contribution novelty motivation problem statement proposed approach",
        "method": "method architecture pipeline implementation training model algorithm",
        "results": "experiments results evaluation benchmark comparison ablation findings",
        "critical": "limitations assumptions risks failure cases reproducibility discussion future work",
    }
    return f"{paper_title}\nsummary length={length_preset}\nfocus={angle_preset}\n{angle_terms.get(angle_preset, '')}"


def translation_retrieval_query(paper, source_text: str) -> str:
    index = paper.text.find(source_text)
    if index < 0:
        return source_text
    start = max(0, index - 1200)
    end = min(len(paper.text), index + len(source_text) + 1200)
    return paper.text[start:end]


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    repo_type = type(request.app.state.repository).__name__
    return {
        "status": "ok",
        "repository": repo_type,
        "llm_provider": "aws-bedrock",
        "llm_model": settings.anthropic_model,
        "embedding_provider": "aws-bedrock",
        "embedding_model": settings.embedding_model,
    }


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


@app.get("/api/papers/{paper_id}/full")
async def get_full_paper(paper_id: str, request: Request):
    try:
        paper = await repository(request).get_paper(paper_id)
        return {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "text": paper.text,
            "text_length": len(paper.text),
            "chunks": paper.chunks,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch full paper")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/summarize", response_model=SummaryResponse)
async def summarize(payload: SummaryRequest, request: Request) -> SummaryResponse:
    try:
        paper = await repository(request).get_paper(payload.paper_id)
        context_chunks = await retrieve_context(
            request,
            paper_id=paper.id,
            query_text=summary_retrieval_query(paper.title, payload.length_preset, payload.angle_preset),
        )
        session_glossary = glossary(request).lookup(payload.session_id, paper.text)
        raw_sentences = await request.app.state.llm.summarize(
            paper=paper,
            length_preset=payload.length_preset,
            angle_preset=payload.angle_preset,
            glossary=session_glossary,
            context_chunks=context_chunks,
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
        context_chunks = await retrieve_context(
            request,
            paper_id=paper.id,
            query_text=translation_retrieval_query(paper, source_text),
        )
        masked_text, math_replacements = mask_math(source_text)
        found_terms = glossary(request).lookup(payload.session_id, source_text)
        session_terms = merge_glossary(glossary(request).list_terms(payload.session_id), found_terms)
        translated = await request.app.state.llm.translate(
            paper=paper,
            source_text=masked_text,
            glossary=session_terms,
            context_chunks=context_chunks,
        )
        translated = restore_math(translated, math_replacements)
        units = split_translation_units(source_text, translated, paper, context_chunks=context_chunks)
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
