"""SEC-15 / INV-3 — build_app registers fail-closed handlers that leak no internal detail.

A specific SearchUnavailable → generic 503, and a global catch-all (any unhandled exception)
→ generic 500 with no stack/internal info. Verified by invoking the registered handlers
directly (no network / TestClient dependency). Skipped if the optional `api` extra (FastAPI)
is not installed.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from discovery.api.router import build_app  # noqa: E402 — after importorskip
from discovery.mocks import build_mock_orchestrator  # noqa: E402
from discovery.service.orchestrator import SearchUnavailable  # noqa: E402


def _app():
    bundle = build_mock_orchestrator()
    return build_app(bundle.orchestrator, bundle.grounding_hook)


def test_search_unavailable_handler_is_generic_503() -> None:
    app = _app()
    handler = app.exception_handlers[SearchUnavailable]
    response = handler(None, SearchUnavailable("opensearch host db-1 connection timeout"))
    assert response.status_code == 503
    assert b"db-1" not in response.body  # no internal detail leaked (SEC-9)


def test_global_catch_all_handler_is_generic_500() -> None:
    app = _app()
    assert Exception in app.exception_handlers  # catch-all registered (SEC-15/INV-3)
    handler = app.exception_handlers[Exception]
    response = handler(None, RuntimeError("secret stack trace internal detail"))
    assert response.status_code == 500
    assert b"secret" not in response.body
    assert b"stack" not in response.body
