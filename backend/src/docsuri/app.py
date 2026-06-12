"""FastAPI 진입점 — create_app() 팩토리.

설정 로딩 → U0 포트 조립(build_u0) → U1 서비스 와이어링(build_u1) → 라우터 등록.
mock 모드는 자격 증명 불필요(로컬 시연·테스트), aws 모드는 ADR §12 실구현.

실행: uv run uvicorn docsuri.app:create_app --factory
"""

from __future__ import annotations

from fastapi import FastAPI

from .u0.adapters import build_u0
from .u0.config import load_settings
from .u1.api import build_router
from .u1.service import build_u1
from .u4.api import build_router as build_u4_router


def create_app() -> FastAPI:
    app = FastAPI(title="DocSuri API", version="0.1.0")

    # 헬스체크는 도메인 와이어링보다 먼저 등록 — 라우터 조립과 분리.
    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    settings = load_settings()
    u0 = build_u0(settings)
    u1 = build_u1(u0)
    app.include_router(build_router(u1))
    app.include_router(build_u4_router(u0))
    return app
