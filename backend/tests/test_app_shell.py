"""App-shell smoke + contract tests.

The shell must boot, serve health, generate OpenAPI, and never let one module sink the rest.
With the ``docsuri-discovery`` path source now declared (backend/pyproject.toml), accounts +
discovery actually MOUNT here; the graceful-skip path is still exercised via an injected
absent module (``test_absent_module_skips_gracefully``).
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
    assert mounted | skipped == {"accounts", "discovery", "library"}


def test_discovery_and_accounts_actually_mount() -> None:
    # Regression guard: discovery silently graceful-skipped on develop until it became a
    # declared dependency (pyproject path source). test_module_registry_complete_and_disjoint
    # only checks the {accounts, discovery} *set* — which stayed green even while discovery was
    # skipped. Assert both actually MOUNT, with nothing skipped.
    result = create_app(_TEST_SETTINGS).state.mount_result
    assert set(result.mounted) == {"accounts", "discovery"}, result.skipped
    assert result.skipped == []


def test_discovery_search_endpoint_is_live() -> None:
    # The mounted discovery router serves /api/search end-to-end through the mock pipeline.
    # NOTE: grounding here is still StubGroundingHook (always-pass); real INV-1 enforcement
    # lands with U6/track6 (see aidlc-docs/construction/u6-integration-proposal.md). This
    # asserts the route is LIVE, not that fabrication is blocked.
    resp = _client().post("/api/search", json={"query": "transformer attention"})
    assert resp.status_code == 200
    assert "cards" in resp.json()


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
    assert {name for name, _ in result.skipped} | set(result.mounted) == {
        "accounts",
        "discovery",
        "library",
    }


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
