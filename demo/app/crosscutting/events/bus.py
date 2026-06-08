"""Single inter-domain communication channel (AGENTS.md §5.2).

domain/A NEVER imports domain/B. They publish/subscribe through this bus
only. Implementation here is an in-memory asyncio.Queue per topic — Sprint 1
walking-skeleton; production would use Redis Streams or Temporal signals.

Replay buffer
-------------
The browser SSE flow is POST → receive stream_url → open EventSource. The
ingest task starts publishing *immediately* after the POST returns, but the
EventSource doesn't connect until the next round-trip. Without buffering,
the FE never sees the events that fired during that gap.

We keep a small ring buffer of the most recent events per topic and replay
them to every new `stream()` subscriber. Production would scope buffers by
correlation id (paper_id) and rely on a real broker; here a topic-level
deque (default 64 entries) is enough for Sprint 1.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

# How many recent events to keep per topic for replay-on-subscribe. Large
# enough to cover several ingest runs (~4 events each) without unbounded
# growth.
REPLAY_BUFFER_SIZE = 64


@dataclass
class Event:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], Awaitable[None]]]] = defaultdict(list)
        self._queues: dict[str, list[asyncio.Queue[Event]]] = defaultdict(list)
        self._recent: dict[str, deque[Event]] = defaultdict(
            lambda: deque(maxlen=REPLAY_BUFFER_SIZE)
        )

    async def publish(self, event: Event) -> None:
        # Append to replay buffer first so late subscribers can backfill.
        self._recent[event.topic].append(event)
        for cb in self._subscribers.get(event.topic, []):
            await cb(event)
        for q in self._queues.get(event.topic, []):
            await q.put(event)

    def subscribe(self, topic: str, cb: Callable[[Event], Awaitable[None]]) -> None:
        self._subscribers[topic].append(cb)

    async def stream(self, topic: str) -> AsyncIterator[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue()
        # Drain any buffered events FIRST so new subscribers see history.
        # Consumers (e.g. the SSE route) already filter by paper_id so
        # cross-paper noise from the replay is benign.
        for past in list(self._recent[topic]):
            await q.put(past)
        self._queues[topic].append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._queues[topic].remove(q)


bus = EventBus()
