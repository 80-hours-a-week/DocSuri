from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware import InMemoryRateLimiter, configure_u6_middleware
from backend.middleware.gateway import _rate_limit_key


def test_u6_middleware_adds_security_headers_and_request_id() -> None:
    app = FastAPI()
    configure_u6_middleware(app, production=True)

    @app.get("/ok")
    def ok() -> dict:
        return {"ok": True}

    response = TestClient(app).get("/ok", headers={"X-Request-ID": "req-u6"})

    assert response.headers["X-Request-ID"] == "req-u6"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'self'" in response.headers["Content-Security-Policy"]


def test_u6_middleware_maps_unhandled_errors_to_generic_response() -> None:
    app = FastAPI()
    configure_u6_middleware(app, production=True)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("internal detail must not leak")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json()["message"] == "Something went wrong. Please try again."
    assert "internal detail" not in response.text


def test_u6_middleware_rate_limit_seam_fails_closed() -> None:
    app = FastAPI()
    configure_u6_middleware(app, rate_limiter=InMemoryRateLimiter(max_requests=1), production=True)

    @app.get("/limited")
    def limited() -> dict:
        return {"ok": True}

    client = TestClient(app)

    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 429


def test_u6_middleware_does_not_trust_forwarded_for_by_default() -> None:
    app = FastAPI()
    configure_u6_middleware(app, rate_limiter=InMemoryRateLimiter(max_requests=1), production=True)

    @app.get("/limited")
    def limited() -> dict:
        return {"ok": True}

    client = TestClient(app)

    assert client.get("/limited", headers={"X-Forwarded-For": "203.0.113.1"}).status_code == 200
    assert client.get("/limited", headers={"X-Forwarded-For": "203.0.113.2"}).status_code == 429


def test_u6_middleware_can_trust_first_forwarded_for_hop_when_configured() -> None:
    app = FastAPI()
    configure_u6_middleware(
        app,
        rate_limiter=InMemoryRateLimiter(max_requests=1),
        production=True,
        trust_proxy_headers=True,
    )

    @app.get("/limited")
    def limited() -> dict:
        return {"ok": True}

    client = TestClient(app)

    first = client.get("/limited", headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"})
    duplicate_first = client.get(
        "/limited",
        headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.2"},
    )
    second = client.get("/limited", headers={"X-Forwarded-For": "203.0.113.2, 10.0.0.1"})

    assert first.status_code == 200
    assert duplicate_first.status_code == 429
    assert second.status_code == 200


def test_rate_limit_key_handles_missing_client() -> None:
    class RequestWithoutClient:
        headers: dict[str, str] = {}
        client = None

    assert _rate_limit_key(RequestWithoutClient()) == "unknown-client"


def test_in_memory_rate_limiter_compacts_expired_keys() -> None:
    now = 0.0

    def clock() -> float:
        return now

    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=1.0, clock=clock)

    assert limiter.allow("old-a")
    assert limiter.allow("old-b")
    now = 2.0
    assert limiter.allow("new")

    assert set(limiter._events) == {"new"}
