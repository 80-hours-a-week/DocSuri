"""App-shell factory — assembles the modular-monolith FastAPI app (deploy unit ①).

Order of assembly: middleware (CORS + request id) → fail-closed error handlers → health
router → optional module mount. Modules are mounted at construction (so routes + DI exist
for OpenAPI and routing); the lifespan only releases resources on shutdown.

⚙️ CG-1 RESOLVED: the backend web framework is **FastAPI**, decided by the app-shell owner
(@revenantonthemission) now that app-shell ownership moved to Track 2 (PR #42). The
modules' "pending @ELSAPHABA sign-off" notes are superseded by this.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import Settings
from .errors import register_error_handlers
from .health import router as health_router
from .wiring import mount_modules

log = logging.getLogger("docsuri.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    result = getattr(app.state, "mount_result", None)
    log.info(
        "app-shell up — mounted=%s skipped=%s",
        result.mounted if result else [],
        [name for name, _ in result.skipped] if result else [],
    )
    yield
    # Shutdown: run module cleanups (reverse mount order), then dispose the DB engine.
    if result:
        for cleanup in reversed(result.cleanups):
            try:
                await cleanup()
            except Exception as exc:  # shutdown must not raise
                log.warning("app-shell: cleanup error: %r", exc)
    engine = getattr(app.state, "db_engine", None)
    if engine is not None:
        engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    app = FastAPI(
        title="DocSuri Backend (modular monolith)",
        version=__version__,
        summary="App-shell for deploy unit ① — hosts U2/U3/U4 modules + U6 middleware.",
        lifespan=lifespan,
    )
    app.state.settings = settings

    _add_middleware(app, settings)
    register_error_handlers(app)
    app.include_router(health_router)

    app.state.mount_result = mount_modules(app, settings)
    return app


def _add_middleware(app: FastAPI, settings: Settings) -> None:
    # Explicit origin allow-list + credentials (cookie sessions). U6's authn/authz/rate-limit
    # and the grounding post-handler are layered in later via backend/middleware/ (Track 1).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
