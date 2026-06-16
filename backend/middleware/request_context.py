from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    principal_id: str | None = None
    degrade_mode: str = "NORMAL"
