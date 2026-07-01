"""ASGI entrypoint.

Run from the repo root so the ``backend`` package (and any in-tree ``backend.modules.*``)
is importable:

    uvicorn backend.main:app --reload

The default ``logging`` config is left to the runner; ``create_app`` is import-safe and
boots with zero external services (SQLite, no Redis, no modules required).
"""

from __future__ import annotations

from .app import create_app

app = create_app()
