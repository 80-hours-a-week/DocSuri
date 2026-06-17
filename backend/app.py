"""App-shell factory — assembles the modular-monolith FastAPI app (deploy unit ①).

Order of assembly: middleware (U6 gateway + CORS) → fail-closed error handlers → health
router → optional module mount. Modules are mounted at construction (so routes + DI exist
for OpenAPI and routing); the lifespan only releases resources on shutdown.

The U6 gateway (backend/middleware/) is now installed here (critical path ④): per-request
context + id, security headers, in-process rate limiting, and production error mapping. The
real grounding hook is injected at the discovery seam (see backend/wiring._mount_discovery).

⚙️ CG-1 RESOLVED: the backend web framework is **FastAPI**, decided by the app-shell owner
(@revenantonthemission) now that app-shell ownership moved to Track 2 (PR #42). The
modules' "pending @ELSAPHABA sign-off" notes are superseded by this.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import Settings
from .errors import register_error_handlers
from .health import router as health_router
from .middleware import InMemoryRateLimiter, configure_u6_middleware
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

    # U6 observability + rate limiter (process-local seams; a real telemetry sink / Redis swap
    # in for production). Held on app.state so the gateway and tests can reach them.
    observability, telemetry_store = _build_observability()
    app.state.observability = observability
    app.state.telemetry_store = telemetry_store
    app.state.rate_limiter = InMemoryRateLimiter()

    _add_middleware(app, settings)
    register_error_handlers(app)
    app.include_router(health_router)

    app.state.mount_result = mount_modules(app, settings)
    return app


def _build_observability():
    """Build ObservabilityHub with the appropriate event store.

    Production (CLOUDWATCH_NAMESPACE set): CloudWatch Logs + Metrics.
    Dev/test (default): in-memory store (visible via app.state.telemetry_store).
    Degrades to (None, None) if docsuri-ops is absent.
    """
    import os

    try:
        from docsuri_ops.observability import ObservabilityHub
    except ModuleNotFoundError:
        log.info("app-shell: docsuri-ops absent — U6 gateway runs without observability")
        return None, None

    namespace = os.getenv("CLOUDWATCH_NAMESPACE")
    if namespace:
        from docsuri_ops.adapters.cloudwatch import CloudWatchEventStore

        store = CloudWatchEventStore(
            namespace=namespace,
            log_group=os.getenv("CLOUDWATCH_LOG_GROUP", "/docsuri/ops"),
            region_name=os.getenv("AWS_REGION", "ap-northeast-2"),
        )
        log.info("app-shell: observability → CloudWatch (namespace=%s)", namespace)
    else:
        from docsuri_ops.adapters.local import InMemoryEventStore

        store = InMemoryEventStore()

    return ObservabilityHub(store), store


def _add_middleware(app: FastAPI, settings: Settings) -> None:
    # U6 gateway (backend/middleware/): per-request context + id, security headers, in-process
    # rate limiting, auth injection, and production error mapping.
    session_manager = _build_session_manager(settings)
    app.state.session_manager = session_manager
    configure_u6_middleware(
        app,
        observability=app.state.observability,
        rate_limiter=app.state.rate_limiter,
        session_manager=session_manager,
        production=not settings.is_local,
        trust_proxy_headers=settings.trust_proxy_headers,
        trusted_proxy_count=settings.trusted_proxy_count,
    )

    # CORS added LAST → outermost, so preflight and the gateway's 429/500 responses still carry
    # CORS headers. Explicit origin allow-list + credentials (cookie sessions; SEC-12) — the
    # CORS spec forbids wildcard origin together with allow_credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _build_session_manager(settings: Settings):
    """Build SessionManager for gateway auth injection.

    Returns None when Redis is unavailable (local dev without Redis) — the gateway
    then skips auth injection and downstream handlers use their own fallbacks.
    Requires REDIS_URL env var to be set; absent → auth injection off (safe dev default).
    """
    import os

    if not os.getenv("REDIS_URL"):
        log.info("app-shell: REDIS_URL unset — gateway auth injection disabled (mock mode)")
        return None
    try:
        from backend.modules.accounts.repository.session import SessionRepository
        from backend.modules.accounts.services.session_manager import SessionManager

        repo = SessionRepository()
        return SessionManager(repo)
    except Exception:
        log.info("app-shell: session manager unavailable — gateway auth injection disabled")
        return None
