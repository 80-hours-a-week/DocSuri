"""SourceSelector — task→source with abstract fallback (BR-S2 / Q1).

summary → full text (S3 ``stored_full_text_ref``); absent/license-disallowed → abstract
fallback (NFR-R2) with a reason; both absent → None (→ SourceUnavailableDTO).
translate → abstract.
"""

from __future__ import annotations

from ..ports.ports import FullTextSourcePort
from .models import SourceKind, SourceText, SummaryRequest, Task


class SourceSelector:
    def __init__(self, full_text: FullTextSourcePort) -> None:
        self._full_text = full_text

    def select(self, request: SummaryRequest) -> SourceText | None:
        if request.task == Task.TRANSLATE:
            if request.abstract:
                return SourceText(kind=SourceKind.ABSTRACT, raw=request.abstract)
            return None

        # summary → full text, with abstract fallback (Q1).
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
