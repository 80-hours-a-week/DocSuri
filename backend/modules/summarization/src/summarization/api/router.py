"""Thin FastAPI router — POST /api/summarize (SummarizationController).

Request validation (SEC-5), trust the gateway-injected principal (SEC-8), delegate to the
gateway seam, and serialize the terminal response via its SEC-9-safe ``to_dict``. The
response is the buffer-validated result (Q5/BR-S8): the client renders progressively from
already-grounded fields. A global handler keeps internals out of error responses (INV-4).
"""

from __future__ import annotations

from typing import Any

from ..api.gateway_seam import run_summarization
from ..domain.models import (
    AuthSession,
    Persona,
    RequestContext,
    SummaryRequest,
    TargetLang,
    Task,
)
from ..service.orchestrator import SummarizationOrchestrationService


def build_router(orchestrator: SummarizationOrchestrationService) -> Any:
    from fastapi import APIRouter, Body, Request
    from fastapi.responses import JSONResponse

    router = APIRouter()

    @router.post("/api/summarize")
    def summarize(request: Request, payload: dict = Body(...)) -> Any:  # noqa: B008
        principal = getattr(request.state, "principal", None)
        user_id = getattr(principal, "user_id", None) or (principal or {}).get("user_id") \
            if principal else None
        if not user_id:
            return JSONResponse({"status": "unauthorized"}, status_code=401)

        parsed = _parse_request(payload)
        if parsed is None:
            return JSONResponse({"status": "validation_error"}, status_code=400)

        ctx = RequestContext(
            auth_session=AuthSession(user_id=str(user_id)),
            request_id=request.headers.get("x-request-id", ""),
        )
        response = run_summarization(orchestrator, parsed, ctx)
        return JSONResponse(response.to_dict())

    return router


def _parse_request(payload: dict) -> SummaryRequest | None:
    try:
        task = Task(str(payload["task"]))
        paper_id = str(payload["paperId"])
        version = int(payload.get("version", 1))
    except (KeyError, ValueError, TypeError):
        return None
    if not paper_id:
        return None
    persona = _enum_or_default(Persona, payload.get("persona"), Persona.EXPERT)
    lang = _enum_or_default(TargetLang, payload.get("targetLang"), TargetLang.KO)
    abstract = payload.get("abstract")
    return SummaryRequest(
        paper_id=paper_id,
        version=version,
        task=task,
        target_lang=lang,
        persona=persona,
        abstract=str(abstract) if abstract else None,
    )


def _enum_or_default(enum_cls: Any, value: Any, default: Any) -> Any:
    if value is None:
        return default
    try:
        return enum_cls(str(value))
    except ValueError:
        return default
