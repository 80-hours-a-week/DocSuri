"""App-shell ↔ module wiring (the coordination-zone seam).

Modules are mounted **optionally**: each integration imports its module lazily and is
skipped (logged, not fatal) when the module is not present on the branch yet. This is what
lets the app-shell land on ``develop`` *before* the track PRs and have them auto-wire as
they merge — instead of a deadlock where the shell can't merge until the modules it mounts
already exist.

Per-module integration idioms differ (see each ``_mount_*``):
  • accounts (U3) exposes a ready ``router`` + a ``get_db_session`` seam to override, and a
    Redis ``SessionRepository`` singleton to close on shutdown.
  • discovery (U2) exposes *factories* (``build_mock_orchestrator`` + ``build_router``) that
    need dependency injection — the mock orchestrator is wired with the REAL U6 grounding hook
    (docsuri-ops); only the OpenSearch/Bedrock data adapters remain mock-first.

The shell owns this file (CODEOWNERS ``/backend/``); module owners change only their lane.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import FastAPI

from .config import Settings

log = logging.getLogger("docsuri.backend.wiring")

# A coroutine the shell runs once on shutdown (reverse order) to release a module's resources.
Cleanup = Callable[[], Awaitable[None]]


@dataclass
class MountResult:
    mounted: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (module, reason)
    cleanups: list[Cleanup] = field(default_factory=list)


def mount_modules(app: FastAPI, settings: Settings, integrations=None) -> MountResult:
    """Mount every available module. Never raises — a missing or broken module degrades to
    a skip so the rest of the backend still serves.

    ``integrations`` defaults to the real registry; tests inject a guaranteed-absent
    integration to exercise the skip path without depending on what's installed.
    """
    result = MountResult()
    for integration in (_INTEGRATIONS if integrations is None else integrations):
        name = integration.__name__.removeprefix("_mount_")
        try:
            integration(app, settings, result)
        except ModuleNotFoundError as exc:
            result.skipped.append((name, f"not present ({exc.name})"))
            log.info("app-shell: %s module not present yet — skipping mount", name)
        except Exception as exc:  # defensive: one broken module must not sink the shell
            result.skipped.append((name, f"mount error: {exc!r}"))
            log.warning("app-shell: failed to mount %s: %r", name, exc)
    app.state.mounted_modules = list(result.mounted)
    return result


def _mount_accounts(app: FastAPI, settings: Settings, result: MountResult) -> None:
    # ModuleNotFoundError here (accounts not on this branch) bubbles to mount_modules → skip.
    from backend.modules.accounts import controller as accounts

    from .db import make_engine, make_session_factory

    # Fill the DI seam the module declares (its get_db_session raises by contract).
    engine = make_engine(settings.database_url)
    app.state.db_engine = engine
    session_factory = make_session_factory(engine)

    def get_db_session():
        # commit/rollback are the controller's job (verify-all-then-commit); we own open/close.
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[accounts.get_db_session] = get_db_session
    app.include_router(accounts.router)
    result.mounted.append("accounts")

    async def _close_accounts_session_store() -> None:
        # Close the Redis pool ONLY if the lru_cached singleton was actually built — calling
        # get_session_repo() unconditionally would *create* a pool just to close it.
        if accounts.get_session_repo.cache_info().currsize:
            await accounts.get_session_repo().close()

    result.cleanups.append(_close_accounts_session_store)


def _mount_discovery(app: FastAPI, settings: Settings, result: MountResult) -> None:
    # discovery is the top-level ``discovery`` package (docsuri-discovery); the real U6
    # grounding hook lives in docsuri-ops. EITHER absent → ModuleNotFoundError → skip
    # (fail-closed: serve no /api/search rather than ungrounded results). The same applies to
    # the real read path: if it is configured but its `real` extra (opensearch-py/boto3) is not
    # installed, the import raises ModuleNotFoundError → skip (no silent mock fallback).
    from discovery.adapters.settings import DiscoverySettings
    from discovery.api.router import build_router
    from docsuri_ops.grounding import GroundingEnforcementHook

    # Read path selection (U2 real adapters, critical path ⑥): when the shared OpenSearch
    # cluster + Bedrock model are configured (DOCSURI_OPENSEARCH_ENDPOINT + _BEDROCK_MODEL_ID),
    # wire the REAL OpenSearch/Bedrock read path; otherwise stay mock-first. The cluster itself
    # is provisioned by the shared infra track (U1 infra + system event bus) — U2 only reads it.
    discovery_settings = DiscoverySettings.from_env()
    if discovery_settings.search_enabled:
        from discovery.real_wiring import build_real_orchestrator

        bundle = build_real_orchestrator(discovery_settings)
        read_path = "real(opensearch+bedrock)"
    else:
        from discovery.mocks.wiring import build_mock_orchestrator

        bundle = build_mock_orchestrator()
        read_path = "mock"

    # The grounding gate is the REAL U6 single authority (INV-1) in BOTH modes — replacing the
    # always-pass StubGroundingHook: enforce() blocks any exposed arXiv id/url absent from the
    # retrieved records and abstains when there is nothing to ground against. With the real
    # OpenSearch adapter the retrieved set is independent of the ranked candidates, so the hook
    # is now load-bearing (not trivially passing as it did against the mock adapter).
    grounding_hook = GroundingEnforcementHook()
    app.state.discovery_bundle = bundle
    app.state.grounding_hook = grounding_hook
    app.include_router(build_router(bundle.orchestrator, grounding_hook))
    result.mounted.append("discovery")
    log.info("app-shell: discovery mounted (read path = %s)", read_path)


def _mount_library(app: FastAPI, settings: Settings, result: MountResult) -> None:
    # library (U4) is `backend.modules.library`. Absent → ModuleNotFoundError → skip.
    from backend.modules.library import controller as library
    from backend.modules.library.audit import InMemoryAuditSink
    from backend.modules.library.gateway import StubSearchGateway
    from backend.modules.library.history_consumer import SearchHistoryEventConsumer
    from backend.modules.library.repository.memory import InMemoryUserDataRepository
    from backend.modules.library.services.history import SearchHistoryService

    # Mock-first (D10): default to the in-memory adapters so U4 mounts + serves with NO live DB.
    # Production overrides get_user_data_repo with a SqlUserDataRepository (per-request session).
    repo = InMemoryUserDataRepository()
    gateway = StubSearchGateway()
    audit = InMemoryAuditSink()

    app.dependency_overrides[library.get_user_data_repo] = lambda: repo
    app.dependency_overrides[library.get_search_gateway] = lambda: gateway
    app.dependency_overrides[library.get_audit_sink] = lambda: audit

    for router in library.routers:
        app.include_router(router)

    # History write path: the SearchExecuted consumer shares the SAME repo as the read routers,
    # so an event recorded asynchronously is visible to GET /library/history.
    app.state.library_repo = repo
    app.state.library_history_consumer = SearchHistoryEventConsumer(
        SearchHistoryService(repo, gateway, audit)
    )
    result.mounted.append("library")


# The real registry. Each entry is a `(app, settings, result) -> None` mounter whose name
# (minus the `_mount_` prefix) labels it in MountResult / `/readyz`.
_INTEGRATIONS = (_mount_accounts, _mount_discovery, _mount_library)
