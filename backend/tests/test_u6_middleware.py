from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware import InMemoryRateLimiter, configure_u6_middleware


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
