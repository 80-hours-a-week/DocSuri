"""DocSuri backend — modular monolith (deploy unit ①).

This package is the **app-shell**: bootstrap, router, DI, and common-middleware wiring
that hosts the backend modules (U2 discovery, U3 accounts, U4 library) and the U6
gateway middleware in a single FastAPI runtime (§5-A: backend = Python).

Owner: @revenantonthemission (Track 2, app-shell — CODEOWNERS `/backend/`).
Modules live under `backend/modules/*` (each owned by its track); the shell mounts
them through `backend.wiring` and must never reach into a module's internals beyond
the documented integration seam.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
