from __future__ import annotations

import ipaddress
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .request_context import RequestContext
from .security_headers import apply_security_headers


def install_gateway_middleware(
    app: FastAPI,
    *,
    observability=None,
    rate_limiter=None,
    session_manager=None,
    production: bool = True,
    trust_proxy_headers: bool = False,
    trusted_proxy_count: int = 1,
) -> None:
    from .auth import inject_principal

    @app.middleware("http")
    async def _u6_gateway(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        request.state.context = RequestContext(request_id=request_id)

        if rate_limiter is not None:
            key = _rate_limit_key(
                request,
                trust_proxy_headers=trust_proxy_headers,
                trusted_proxy_count=trusted_proxy_count,
            )
            if not rate_limiter.allow(str(key)):
                response = JSONResponse(
                    status_code=429,
                    content={"message": "Too many requests.", "requestId": request_id},
                )
                response.headers["X-Request-ID"] = request_id
                apply_security_headers(response)
                return response

        # Auth injection: resolve session cookie → Principal on request.state.
        # When session_manager is None (dev/test without Redis), skip auth injection
        # and let downstream handlers use their own fallback (e.g. X-User-Id header).
        if session_manager is not None:
            auth_response = await inject_principal(
                request, call_next, session_manager=session_manager
            )
            auth_response.headers["X-Request-ID"] = request_id
            apply_security_headers(auth_response)
            return auth_response

        try:
            response = await call_next(request)
        except Exception as exc:
            _emit_error(observability, request_id, exc)
            if not production:
                raise
            response = JSONResponse(
                status_code=500,
                content={
                    "message": "Something went wrong. Please try again.",
                    "requestId": request_id,
                },
            )

        response.headers["X-Request-ID"] = request_id
        apply_security_headers(response)
        return response


def _rate_limit_key(
    request: Request,
    *,
    trust_proxy_headers: bool = False,
    trusted_proxy_count: int = 1,
) -> str:
    if trust_proxy_headers:
        forwarded = _forwarded_client(request, trusted_proxy_count)
        if forwarded is not None:
            return forwarded

    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return str(host or "unknown-client")


def _forwarded_client(request: Request, trusted_proxy_count: int) -> str | None:
    raw = request.headers.get("X-Forwarded-For")
    if not raw:
        return None
    hops = [hop.strip() for hop in raw.split(",") if hop.strip()]
    # The LEFTMOST entry is fully client-controlled (spoofable) — keying on it lets an attacker
    # rotate it to evade per-IP limits. Trust only what our own proxies stamped: count
    # `trusted_proxy_count` from the right and take the hop our outermost trusted proxy recorded.
    # Require a valid IP so a spoofed/garbage value can't mint unlimited rate-limit buckets.
    idx = len(hops) - max(trusted_proxy_count, 1)
    if idx < 0:
        return None  # fewer hops than trusted proxies → header is not trustworthy
    candidate = hops[idx]
    return candidate if _is_ip(candidate) else None


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _emit_error(observability, request_id: str, exc: Exception) -> None:
    if observability is None:
        return
    emit_log = getattr(observability, "emit_log", None)
    if emit_log is None:
        return
    emit_log(
        {
            "eventId": f"gateway-error:{request_id}",
            "requestId": request_id,
            "level": "error",
            "errorType": type(exc).__name__,
        }
    )
