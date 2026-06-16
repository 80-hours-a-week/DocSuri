from __future__ import annotations

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
    production: bool = True,
) -> None:
    @app.middleware("http")
    async def _u6_gateway(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        request.state.context = RequestContext(request_id=request_id)

        if rate_limiter is not None:
            key = request.headers.get("X-Forwarded-For") or request.client.host
            if not rate_limiter.allow(str(key)):
                response = JSONResponse(
                    status_code=429,
                    content={"message": "Too many requests.", "requestId": request_id},
                )
                response.headers["X-Request-ID"] = request_id
                apply_security_headers(response)
                return response

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
