"""FastAPI router for U2 search (QueryIntakeController). THIN HTTP binding only.

⏳ FastAPI is a backend-shared (app-shell) decision pending @ELSAPHABA sign-off (CG-1/DS-3);
import this module only with the ``api`` extra. In production, authn/authz/rate-limit and the
grounding post-handler are the U6 gateway's job; the request identity comes ONLY from the
gateway-injected principal (``request.state.principal``), never from a client-supplied header
(SEC-8/BR-13) — so a caller cannot forge another user's id. An anonymous request (no principal)
still searches but is attributed to no user (no history). For standalone mock-first dev
(``build_app``) there is no gateway, so a dev ``X-User-Id`` header fallback can be opted in via
``dev_user_fallback`` — OFF by default, and it MUST stay off behind the real gateway. The
app-shell mounts the returned router and owns real gateway wiring (CG-5).
"""

from __future__ import annotations

import uuid

from docsuri_shared.dtos import SearchRequest, ValidationErrorDTO
from docsuri_shared.ports import GroundingEnforcementHook
from fastapi import APIRouter, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from ..domain.models import AuthSession, RequestContext
from ..service.orchestrator import SearchOrchestrationService, SearchUnavailable
from ..service.paper_metadata import PaperMetadataService
from .gateway_seam import run_search

# Generic fail-closed messages (SEC-9/SEC-15 — no internal detail / stack / framework info).
_UNAVAILABLE_MESSAGE = "Search is temporarily unavailable. Please try again shortly."
_GENERIC_ERROR_MESSAGE = "Something went wrong. Please try again."


def build_router(
    orchestrator: SearchOrchestrationService,
    grounding_hook: GroundingEnforcementHook,
    paper_service: PaperMetadataService | None = None,
    *,
    dev_user_fallback: bool = False,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/search")
    def search(
        http_request: Request,
        request: SearchRequest,
        x_user_id: str | None = Header(default=None),
    ) -> JSONResponse:
        # Identity comes ONLY from the gateway-injected principal (SEC-8/BR-13). An anonymous
        # request (no principal) still searches but is attributed to no user (history skipped).
        # The X-User-Id header is a STANDALONE-DEV-ONLY fallback (dev_user_fallback) — never
        # trusted behind the real gateway, so a client cannot forge another user's identity.
        principal = getattr(http_request.state, "principal", None)
        if principal is not None:
            user_id = principal.user_id
        elif dev_user_fallback:
            user_id = x_user_id
        else:
            user_id = None
        request_id = getattr(http_request.state, "request_id", None) or uuid.uuid4().hex
        ctx = RequestContext(
            auth_session=AuthSession(user_id=user_id), request_id=request_id
        )
        response = run_search(orchestrator, grounding_hook, request, ctx)
        status = 400 if isinstance(response.root, ValidationErrorDTO) else 200
        return JSONResponse(status_code=status, content=response.model_dump(mode="json"))

    if paper_service is not None:

        @router.get("/api/papers/{paper_id}")
        def paper_meta(paper_id: str) -> JSONResponse:
            """Paper-detail header metadata (title/authors/abstract). 404 when not indexed so
            the detail page degrades to the arXiv id + link-out. SearchUnavailable (store
            outage) is mapped to the generic 503 by the app-shell / build_app handler."""
            meta = paper_service.get_paper_meta(paper_id)
            if meta is None:
                return JSONResponse(status_code=404, content={"message": "Paper not found."})
            return JSONResponse(status_code=200, content=meta.model_dump(mode="json"))

    return router


def build_app(
    orchestrator: SearchOrchestrationService,
    grounding_hook: GroundingEnforcementHook,
    paper_service: PaperMetadataService | None = None,
) -> FastAPI:
    """Standalone dev app (mock-first). The real backend app is the app-shell's (CG-5)."""
    app = FastAPI(title="DocSuri Discovery (U2) — mock-first")
    # Standalone dev has no gateway to inject a principal, so opt into the X-User-Id dev
    # fallback here. The real app-shell mount (backend.wiring) leaves it OFF (default).
    app.include_router(
        build_router(orchestrator, grounding_hook, paper_service, dev_user_fallback=True)
    )

    @app.exception_handler(SearchUnavailable)
    def _on_unavailable(_request, _exc):  # fail-closed: generic 503 (INV-3/SEC-15)
        return JSONResponse(status_code=503, content={"message": _UNAVAILABLE_MESSAGE})

    @app.exception_handler(Exception)
    def _on_unexpected(_request, _exc):  # global catch-all: generic 500, no leak (INV-3/SEC-15)
        return JSONResponse(status_code=500, content={"message": _GENERIC_ERROR_MESSAGE})

    return app
