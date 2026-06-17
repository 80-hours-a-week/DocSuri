"""App-shell configuration — environment-driven, no external service required to boot.

Defaults are chosen so the shell starts in CI / a bare checkout with zero infrastructure
(SQLite, no Redis). Production overrides every value via env (see `.env.example` and
`docker-compose.yml` for the full-local Postgres + Redis profile).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Sensible dev defaults for the SSR phone frontend (U5) origins. CORS must be an explicit
# allow-list (not "*") because accounts/auth uses credentialed cookies (SEC-12) and the
# CORS spec forbids wildcard origin together with allow_credentials.
_DEFAULT_CORS_ORIGINS = ("http://localhost:3000", "http://localhost:5173")


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable, fully-resolved settings. Build via :meth:`from_env`."""

    env: str = "local"
    # SQLite default keeps the shell bootable with no DB server. accounts (U3) runs against
    # Postgres in prod — set DATABASE_URL to the Postgres DSN there.
    database_url: str = "sqlite:///./docsuri-dev.db"
    cors_origins: tuple[str, ...] = _DEFAULT_CORS_ORIGINS
    # U6 gateway rate-limit keying: trust X-Forwarded-For only behind a controlled proxy.
    # Default off → key on the direct client (request.client.host). See
    # backend/middleware/gateway.py::_rate_limit_key. Set TRUST_PROXY_HEADERS=1 in deployments
    # that sit behind a trusted reverse proxy / load balancer.
    trust_proxy_headers: bool = False

    @property
    def is_local(self) -> bool:
        return self.env.lower() in {"local", "test", "dev", "development"}

    @classmethod
    def from_env(cls) -> Settings:
        raw_origins = os.getenv("CORS_ORIGINS")
        origins = (
            tuple(o.strip() for o in raw_origins.split(",") if o.strip())
            if raw_origins
            else _DEFAULT_CORS_ORIGINS
        )
        return cls(
            env=os.getenv("ENV", "local"),
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            cors_origins=origins,
            trust_proxy_headers=os.getenv("TRUST_PROXY_HEADERS", "").strip().lower()
            in {"1", "true", "yes", "on"},
        )
