"""App-shell smoke + contract tests.

These run with NO modules installed (the state of ``develop``): the shell must boot, serve
health, generate OpenAPI, and gracefully report accounts/discovery as skipped. The graceful
mount is what lets this PR land before the track PRs.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.wiring import MountResult, mount_modules

# In-memory SQLite so the accounts seam (if ever present) needs no DB file on disk.
_TEST_SETTINGS = Settings(env="test", database_url="sqlite://")


def _client() -> TestClient:
    return TestClient(create_app(_TEST_SETTINGS))


def test_app_boots_and_is_fastapi() -> None:
    app = create_app(_TEST_SETTINGS)
    assert isinstance(app, FastAPI)


def test_health_and_liveness() -> None:
    client = _client()
    assert client.get("/health").json() == {"status": "ok", "service": "docsuri-backend"}
    assert client.get("/healthz").json() == {"status": "ok"}


def test_openapi_generates() -> None:
    schema = _client().get("/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["info"]["title"] == "DocSuri Backend (modular monolith)"


def test_module_registry_complete_and_disjoint() -> None:
    # Env-independent: which modules are installed in this checkout varies, but every
    # registered module must land in exactly one bucket (never dropped, never both).
    readyz = _client().get("/readyz").json()
    assert readyz["status"] == "ready"
    mounted, skipped = set(readyz["mounted"]), set(readyz["skipped"])
    assert mounted.isdisjoint(skipped)
    assert mounted | skipped == {"accounts", "discovery"}


def test_absent_module_skips_gracefully_not_fatal() -> None:
    # Inject a guaranteed-absent integration so the skip path is tested regardless of what
    # is installed (the old version assumed the real modules were absent — broke on merge).
    def _mount_ghost(app: FastAPI, settings: Settings, result) -> None:
        raise ModuleNotFoundError("No module named 'ghost'", name="ghost")

    app = create_app(_TEST_SETTINGS)
    result = mount_modules(app, _TEST_SETTINGS, integrations=[_mount_ghost])
    assert result.mounted == []
    assert [name for name, _ in result.skipped] == ["ghost"]


def test_mount_modules_never_raises_and_records_reasons() -> None:
    app = create_app(_TEST_SETTINGS)
    result: MountResult = mount_modules(app, _TEST_SETTINGS)
    assert isinstance(result, MountResult)
    # Every attempted module is accounted for as either mounted or skipped (no silent drop).
    assert {name for name, _ in result.skipped} | set(result.mounted) == {"accounts", "discovery"}


def test_request_id_is_echoed() -> None:
    resp = _client().get("/health", headers={"X-Request-ID": "req-abc-123"})
    assert resp.headers["X-Request-ID"] == "req-abc-123"


def test_unhandled_error_is_generic_and_leak_free() -> None:
    app = create_app(_TEST_SETTINGS)

    @app.get("/_boom")
    def _boom() -> None:
        raise RuntimeError("INTERNAL stack detail that must never reach the client")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/_boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["message"] == "Something went wrong. Please try again."
    assert "requestId" in body
    assert "INTERNAL" not in resp.text  # no internal/stack leak (SEC-15)
