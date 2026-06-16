from __future__ import annotations

from fastapi import FastAPI

from .gateway import install_gateway_middleware
from .rate_limit import InMemoryRateLimiter


def configure_u6_middleware(
    app: FastAPI,
    *,
    observability=None,
    rate_limiter: InMemoryRateLimiter | None = None,
    production: bool = True,
) -> None:
    install_gateway_middleware(
        app,
        observability=observability,
        rate_limiter=rate_limiter,
        production=production,
    )
