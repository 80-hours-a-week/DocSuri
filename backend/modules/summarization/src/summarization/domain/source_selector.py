"""SourceSelector — task/scope→source with abstract fallback (BR-S2 / Q1).

summary → full text (S3 ``stored_full_text_ref``); absent → abstract fallback (NFR-R2)
with a reason; both absent → None (→ SourceUnavailableDTO).
translate scope=full → full text (abstract fallback); scope=abstract → abstract.
"""

from __future__ import annotations

from ..ports.ports import FullTextSourcePort
from .models import Scope, SourceKind, SourceText, SummaryRequest, Task


class SourceSelector:
    def __init__(self, full_text: FullTextSourcePort) -> None:
        self._full_text = full_text

    def fetch_full_text(self, paper_id: str, version: int) -> str | None:
        """Raw normalized full text (or None). Used by the full-text viewer (Q5=C)."""
        return self._full_text.get_full_text(paper_id, version)

    def select(self, request: SummaryRequest) -> SourceText | None:
        if request.task == Task.TRANSLATE and request.scope == Scope.ABSTRACT:
            if request.abstract:
                return SourceText(kind=SourceKind.ABSTRACT, raw=request.abstract)
            return None

        # summary, or translate scope=full → full text with abstract fallback (Q1/NFR-R2).
        raw = self._full_text.get_full_text(request.paper_id, request.version)
        if raw:
            return SourceText(kind=SourceKind.FULL_TEXT, raw=raw)
        if request.abstract:
            return SourceText(
                kind=SourceKind.ABSTRACT,
                raw=request.abstract,
                fallback_reason="full_text_unavailable",
            )
        return None
