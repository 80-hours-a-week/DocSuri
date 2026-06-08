"""FastAPI entry for the Sprint 1 walking-skeleton demo.

Modular monolith per AGENTS.md §5.1. Routes are thin — they delegate to
domain services. The composition root (`container.py`) wires LLM/glossary/
verifier implementations to their ports.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes_ingest, routes_search, routes_summary, routes_translation
from app.container import mode_label

app = FastAPI(
    title="Semantic Paper Workbench — Sprint 1 Demo",
    version="0.1.0",
    description=f"Walking-skeleton demo. LLM mode: {mode_label()}.",
)

app.include_router(routes_search.router, prefix="/api")
app.include_router(routes_ingest.router, prefix="/api")
app.include_router(routes_summary.router, prefix="/api")
app.include_router(routes_translation.router, prefix="/api")

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    """Serve the demo SPA.

    Demo iterations get hot edits to `web/app.js` / `styles.css`; we don't
    want Safari/Chrome to serve a cached index that still references the
    previous bundle hash. `no-store` forces a fresh fetch every navigation,
    and the inner static assets carry a `?v=` cache-buster.
    """
    return FileResponse(
        WEB_DIR / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "llm_mode": mode_label()}
