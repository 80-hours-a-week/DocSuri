"""Gateway-seam + HTTP binding. ``run_search`` (framework-agnostic) is the seam where the
U6 grounding hook is invoked — keeping ``enforce`` out of the U2 domain core (INV-1).
The FastAPI ``router`` lives in :mod:`discovery.api.router` (optional ``api`` extra)."""

from .gateway_seam import run_search

__all__ = ["run_search"]
