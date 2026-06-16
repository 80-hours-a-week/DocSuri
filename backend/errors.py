"""Fail-closed, no-leak error handling at the app-shell edge (SEC-9/SEC-15).

Mirrors the discovery module's stance: unexpected failures return a generic message with
no stack/framework/internal detail. The full exception is logged server-side, keyed by the
request id, so operators can correlate without exposing internals to clients.

Note: ``fastapi.HTTPException`` is intentionally NOT handled here — FastAPI's default handler
passes through the *intended* (already-generalized) detail messages that the modules raise
(e.g. accounts' "이메일 또는 비밀번호가 올바르지 않습니다."). We only blanket the truly
unhandled path.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("docsuri.backend")

# Single generic message — never varies by cause (no oracle for attackers).
_GENERIC_ERROR_MESSAGE = "Something went wrong. Please try again."


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def _on_unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        # Full detail stays server-side only.
        log.error("unhandled error [req=%s] %s", request_id, repr(exc), exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"message": _GENERIC_ERROR_MESSAGE, "requestId": request_id},
        )
