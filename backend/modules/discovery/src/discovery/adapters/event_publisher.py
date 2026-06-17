"""EventBridgeEventPublisher — real ``EventPublisher`` (FR-10 / BR-14).

Publishes ``SearchExecutedEvent`` to the shared event bus (→ U4 history). The contract is
non-blocking and fire-and-forget: a history write MUST NOT add latency to or fail the search
response (off the P50<3s path). The actual ``put_events`` call therefore runs on a small
daemon executor and the response path returns immediately; any failure is logged, never
raised.

The event bus itself is provisioned by the shared infrastructure track (system/U6
EventBridge). Until it exists, the app-shell wires the in-memory publisher instead (see
``DiscoverySettings.search_event_bus`` / ``real_wiring``).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from docsuri_shared.events import SearchExecutedEvent

log = logging.getLogger("docsuri.discovery.events")


class EventBridgeEventPublisher:
    """Fire-and-forget SearchExecuted publisher over Amazon EventBridge."""

    def __init__(
        self,
        *,
        event_bus_name: str,
        source: str = "docsuri.discovery",
        region_name: str | None = None,
        client: Any | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        if client is None:
            import boto3  # lazy: only the `real` extra needs boto3

            client = boto3.client("events", region_name=region_name)
        self._client = client
        self._bus = event_bus_name
        self._source = source
        # Single daemon worker: keeps publishing off the request thread (non-blocking, BR-14).
        self._executor = executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="discovery-events"
        )

    def publish_search_executed(self, event: SearchExecutedEvent) -> None:
        # Return immediately; the send happens on the executor. submit() failures (e.g. on
        # shutdown) are swallowed so history NEVER affects the response (BR-14).
        try:
            self._executor.submit(self._send, event)
        except RuntimeError:
            log.warning("discovery: event executor unavailable; dropped SearchExecuted")

    def _send(self, event: SearchExecutedEvent) -> None:
        try:
            self._client.put_events(
                Entries=[
                    {
                        "Source": self._source,
                        "DetailType": "SearchExecuted",
                        "Detail": event.model_dump_json(),
                        "EventBusName": self._bus,
                    }
                ]
            )
        except Exception:  # noqa: BLE001 — history is best-effort; never surface (BR-14)
            log.warning("discovery: failed to publish SearchExecuted", exc_info=True)

    def close(self) -> None:
        self._executor.shutdown(wait=False)
