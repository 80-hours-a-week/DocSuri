"""Thin FastAPI router — POST /api/summarize (SummarizationController).

Request validation (SEC-5), trust the gateway-injected principal (SEC-8), delegate to the
gateway seam, and serialize the terminal response via its SEC-9-safe ``to_dict``. The
response is the buffer-validated result (Q5/BR-S8): the client renders progressively from
already-grounded fields. A global handler keeps internals out of error responses (INV-4).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from ..api.gateway_seam import run_summarization
from ..domain.models import (
    AuthSession,
    Persona,
    RequestContext,
    Scope,
    SummaryRequest,
    TargetLang,
    Task,
)
from ..service.orchestrator import SummarizationOrchestrationService


def build_router(
    orchestrator: SummarizationOrchestrationService, *, fulltext_enabled: bool = False
) -> Any:
    router = APIRouter()

    @router.post("/api/summarize")
    def summarize(request: Request, payload: dict = Body(...)) -> Any:  # noqa: B008
        user_id = _principal_user_id(request)
        if not user_id:
            return JSONResponse({"status": "unauthorized"}, status_code=401)

        parsed = _parse_request(payload)
        if parsed is None:
            return JSONResponse({"status": "validation_error"}, status_code=400)

        ctx = RequestContext(
            auth_session=AuthSession(user_id=user_id),
            request_id=request.headers.get("x-request-id", ""),
        )
        response = run_summarization(orchestrator, parsed, ctx)
        return JSONResponse(response.to_dict())

    @router.get("/api/glossary")
    def list_glossary(request: Request) -> Any:
        """The caller's saved personal terms (개인 용어집 Phase 2a) — pre-fills the badge editor.
        Owner-scoped (SEC-8): returns only the principal's own terms. Fails closed (INV-4)."""
        user_id = _principal_user_id(request)
        if not user_id:
            return JSONResponse({"status": "unauthorized"}, status_code=401)
        try:
            terms = orchestrator.list_glossary_terms(user_id)
        except Exception:  # noqa: BLE001 — fail-closed; client degrades to no pre-fill
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ok", "terms": terms})

    @router.post("/api/glossary")
    def upsert_glossary_term(request: Request, payload: dict = Body(...)) -> Any:  # noqa: B008
        """Add/override a personal term (개인 용어집 Phase 1). Owner-scoped (SEC-8): the
        gateway-injected principal is the only id trusted — the body never carries a user id.
        A state-changing request (CSRF is the gateway's concern). Validates input (SEC-5) and
        fails closed without surfacing internals (INV-4)."""
        user_id = _principal_user_id(request)
        if not user_id:
            return JSONResponse({"status": "unauthorized"}, status_code=401)
        term = _parse_glossary_term(payload)
        if term is None:
            return JSONResponse({"status": "validation_error"}, status_code=400)
        term_from, term_to = term
        try:
            glossary_ver = orchestrator.upsert_glossary_term(user_id, term_from, term_to)
        except Exception:  # noqa: BLE001 — fail-closed: never surface internals (INV-4/SEC-15)
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ok", "glossaryVer": glossary_ver}, status_code=201)

    @router.get("/api/papers/{paper_id}/full-text")
    def full_text(request: Request, paper_id: str) -> Any:
        """In-app full-text viewer source (Q5=C). OA-license-gated: disabled by default
        (``license_unavailable`` → arXiv link-out) until a license signal is wired."""
        user_id = _principal_user_id(request)
        if not user_id:
            return JSONResponse({"status": "unauthorized"}, status_code=401)
        if not fulltext_enabled:
            return JSONResponse({"status": "license_unavailable"})
        try:
            version = int(request.query_params.get("version", "1"))
        except (TypeError, ValueError):
            version = 1
        text = orchestrator.full_text(paper_id, version)
        if text is None:
            return JSONResponse({"status": "source_unavailable"})
        return JSONResponse({"status": "ok", "text": text})

    return router


def _principal_user_id(request: Any) -> str | None:
    """Extract the gateway-injected principal's user id (SEC-8). Trusts the gateway."""
    principal = getattr(request.state, "principal", None)
    if not principal:
        return None
    uid = getattr(principal, "user_id", None)
    if uid is None and isinstance(principal, dict):
        uid = principal.get("user_id")
    return str(uid) if uid else None


# Personal-term bounds (SEC-5). term_from mirrors a kept-as-is English term; term_to is the
# user's preferred rendering (matches the frontend input maxLength).
_MAX_TERM_FROM = 80
_MAX_TERM_TO = 40


def _parse_glossary_term(payload: dict) -> tuple[str, str] | None:
    """Validate a personal-term upsert: both sides required, trimmed, length-bounded.
    Returns ``(term_from, term_to)`` or None on any violation (→ 400)."""
    if not isinstance(payload, dict):
        return None
    term_from = str(payload.get("termFrom", "")).strip()
    term_to = str(payload.get("termTo", "")).strip()
    if not term_from or not term_to:
        return None
    if len(term_from) > _MAX_TERM_FROM or len(term_to) > _MAX_TERM_TO:
        return None
    return term_from, term_to


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
    scope = _enum_or_default(Scope, payload.get("scope"), Scope.ABSTRACT)
    abstract = payload.get("abstract")
    return SummaryRequest(
        paper_id=paper_id,
        version=version,
        task=task,
        target_lang=lang,
        persona=persona,
        scope=scope,
        abstract=str(abstract) if abstract else None,
    )


def _enum_or_default(enum_cls: Any, value: Any, default: Any) -> Any:
    if value is None:
        return default
    try:
        return enum_cls(str(value))
    except ValueError:
        return default
