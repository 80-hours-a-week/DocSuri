"""SEC-8 / BR-13 — /api/search identity is derived ONLY from the gateway principal.

Defense-in-depth: a client-supplied ``X-User-Id`` header must NEVER attribute search history
to another user behind the real gateway. Anonymous requests still search but write no history;
the dev header fallback is opt-in (standalone mock-first dev) and off in the production mount.

Lives in backend/tests (not the discovery module suite) because it drives the router with
FastAPI's TestClient, whose httpx dependency only ships in the app-shell venv.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from discovery.api.router import build_router  # noqa: E402 — after importorskip
from discovery.mocks import build_mock_orchestrator  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _client(bundle, *, dev_user_fallback: bool = False, principal=None) -> TestClient:
    app = FastAPI()
    if principal is not None:

        @app.middleware("http")
        async def _inject_principal(request: Request, call_next):  # noqa: ANN202
            request.state.principal = principal
            return await call_next(request)

    app.include_router(
        build_router(
            bundle.orchestrator,
            bundle.grounding_hook,
            bundle.paper_service,
            dev_user_fallback=dev_user_fallback,
        )
    )
    return TestClient(app)


def test_anonymous_search_ignores_forged_user_header_and_writes_no_history() -> None:
    # Production mount (dev_user_fallback=False), no gateway principal: the X-User-Id header is
    # NOT trusted, the search still runs, and NO history is attributed to anyone (SEC-8/BR-13).
    bundle = build_mock_orchestrator()
    client = _client(bundle, dev_user_fallback=False)
    resp = client.post("/api/search", json={"query": "attention"}, headers={"X-User-Id": "victim"})
    assert resp.status_code == 200
    assert bundle.event_publisher.events == []  # no SearchExecuted under the forged id


def test_principal_identity_is_used_for_history_not_the_header() -> None:
    # The gateway-injected principal wins; the forged header is ignored.
    bundle = build_mock_orchestrator()
    client = _client(bundle, principal=SimpleNamespace(user_id="real-user"))
    resp = client.post("/api/search", json={"query": "attention"}, headers={"X-User-Id": "victim"})
    assert resp.status_code == 200
    assert [e.userId for e in bundle.event_publisher.events] == ["real-user"]


def test_dev_fallback_honors_user_header_for_standalone_dev() -> None:
    # Standalone mock-first dev only: with no gateway, the dev header attributes history so a
    # developer can exercise per-user behavior. Never enabled behind the real gateway.
    bundle = build_mock_orchestrator()
    client = _client(bundle, dev_user_fallback=True)
    resp = client.post("/api/search", json={"query": "attention"}, headers={"X-User-Id": "dev-42"})
    assert resp.status_code == 200
    assert [e.userId for e in bundle.event_publisher.events] == ["dev-42"]
