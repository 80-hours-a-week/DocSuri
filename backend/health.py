"""Liveness / readiness endpoints.

Deliberately dependency-free: ``/health`` and ``/healthz`` must succeed even when no
modules are mounted and no DB/Redis is configured (so a bare app-shell deploy and CI
smoke tests pass). ``/readyz`` reports which modules actually mounted — useful while the
track PRs are landing one at a time.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "docsuri-backend"}


@router.get("/healthz")
def healthz() -> dict:
    """Liveness alias (k8s-style)."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> dict:
    """Readiness — reflects the modules wired into this process."""
    result = getattr(request.app.state, "mount_result", None)
    return {
        "status": "ready",
        "mounted": list(result.mounted) if result else [],
        "skipped": [name for name, _ in result.skipped] if result else [],
    }
