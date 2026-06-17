"""U4 — SearchExecutedEvent consumer (the event-bus subscriber seam).

This thin adapter is where a real subscriber (EventBridge/SQS in the assembled system) delivers
``SearchExecutedEvent`` payloads. It parses/validates the payload against the FROZEN shared event
schema and hands it to ``SearchHistoryService.record_search`` for idempotent recording (INV-L3).
Delivery is OUTSIDE the synchronous search path (NFR-P1) — recording never blocks a search.
"""

from __future__ import annotations

from docsuri_shared.events import SearchExecutedEvent

from .models import HistoryEntry
from .services.history import SearchHistoryService


class SearchHistoryEventConsumer:
    def __init__(self, service: SearchHistoryService) -> None:
        self._service = service

    def consume(self, payload: SearchExecutedEvent | dict) -> HistoryEntry | None:
        event = (
            payload
            if isinstance(payload, SearchExecutedEvent)
            else SearchExecutedEvent.model_validate(payload)
        )
        return self._service.record_search(event)
