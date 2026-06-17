from __future__ import annotations

import time
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(slots=True)
class InMemoryRateLimiter:
    """Process-local sliding-window limiter for local/dev seams.

    Production deployments should use a shared backend such as Redis so limits are enforced
    consistently across workers.

    Per-request cost is O(1): the served key's window is trimmed lazily and over-cap keys are
    evicted in LRU order via ``OrderedDict.popitem`` — no per-request scan of every key (which
    would let a high-cardinality flood degrade admission to O(K)). A full sweep of expired-but-idle
    keys is amortised to roughly once per ``compact_every`` admissions. Under key pressure eviction
    is LRU and may reset a quiescent key's window — a best-effort limit acceptable for this
    in-memory seam (the shared backend is the real fix).
    """

    max_requests: int = 60
    window_seconds: float = 60.0
    max_keys: int = 10000
    compact_every: int = 1024
    clock: Callable[[], float] = time.time
    _events: OrderedDict[str, deque[float]] = field(default_factory=OrderedDict)
    _since_sweep: int = 0

    def allow(self, key: str) -> bool:
        now = self.clock()
        window = self._events.get(key)
        if window is None:
            window = deque()
            self._events[key] = window
        self._events.move_to_end(key)  # mark most-recently-used (LRU recency tracking)
        cutoff = now - self.window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        allowed = len(window) < self.max_requests
        if allowed:
            window.append(now)
        self._evict_over_cap()
        self._maybe_sweep(now)
        return allowed

    def _evict_over_cap(self) -> None:
        # O(1) LRU eviction bounds the key set under a flood without an O(K) scan. Runs AFTER the
        # current key is inserted/touched, so the cap is exact (not max_keys + 1) and the current
        # key (most-recently-used) is never the one evicted.
        while len(self._events) > self.max_keys:
            self._events.popitem(last=False)

    def _maybe_sweep(self, now: float) -> None:
        # Amortised full sweep: reclaim expired-but-idle keys ~once per `compact_every` admissions
        # rather than on every request (an every-request sweep would be O(K) per admission).
        self._since_sweep += 1
        if self._since_sweep < max(self.compact_every, 1):
            return
        self._since_sweep = 0
        cutoff = now - self.window_seconds
        for key in list(self._events):
            window = self._events[key]
            while window and window[0] <= cutoff:
                window.popleft()
            if not window:
                del self._events[key]
