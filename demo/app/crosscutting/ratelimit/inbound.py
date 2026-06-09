"""Inbound endpoint rate limit (SlowAPI + Redis storage).

This is the *inbound* counterpart to `backoff.py` (which throttles *outbound*
DB API calls). Implements AGENTS.md §4.5:

* per-user quota (so "검색 컨텍스트 다양화"가 50개 DB 호출로 증폭하지 않음).
* per-feature quota (비싼 #06 / #07은 일간 cap + 비용 경고 UI 트리거).

The Limiter instance is a process singleton; FastAPI routes attach the
``@limiter.limit("...")`` decorator to enforce per-endpoint policy. Redis is
the shared storage so multi-replica deploys agree on the counter.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logger = logging.getLogger(__name__)


# Per-feature quota targets per §4.5 — independent buckets from the per-user quota.
_COST_HEAVY_ROUTES = {"/api/gap-analysis", "/api/project-trend"}  # #06, #07


def _rate_limit_key(request: Request) -> str:
    """Return the rate-limit bucket key for ``request`` (AGENTS.md §4.5).

    Strategy:
      1. Authenticated → ``user:{user_id}``. ``request.state.user_id`` must be
         populated by an auth middleware that runs before SlowAPIMiddleware.
      2. Anonymous → ``ip:{first hop of X-Forwarded-For}`` so requests behind
         ALB/Cloudflare bucket by the originating client, not the proxy.
      3. Cost-heavy routes (#06, #07) prefix the principal with the route
         path so per-feature quota is tracked independently of per-user.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        principal = f"user:{user_id}"
    else:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        principal = f"ip:{ip}"
    if any(request.url.path.startswith(p) for p in _COST_HEAVY_ROUTES):
        return f"{principal}|{request.url.path}"
    return principal


def _build_limiter() -> Limiter:
    storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")
    default = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    return Limiter(
        key_func=_rate_limit_key,
        storage_uri=storage_uri,
        default_limits=[default],
        headers_enabled=True,            # surface X-RateLimit-* to the client
    )


limiter = _build_limiter()


def install_rate_limit(app: FastAPI, **state: Any) -> None:
    """Attach SlowAPI middleware + 429 handler to ``app``.

    Routes opt in with ``@limiter.limit("10/minute")``. ``default_limits``
    apply everywhere unless a route declares otherwise.
    """
    app.state.limiter = limiter
    for key, value in state.items():
        setattr(app.state, key, value)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
