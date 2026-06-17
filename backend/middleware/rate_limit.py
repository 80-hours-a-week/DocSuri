from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(slots=True)
class InMemoryRateLimiter:
    """Process-local limiter for local/dev seams.

    Production deployments should use a shared backend such as Redis so limits are enforced
    consistently across workers.
    """

    max_requests: int = 60
    window_seconds: float = 60.0
    max_keys: int = 10000
    clock: Callable[[], float] = time.time
    _events: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _last_seen: dict[str, float] = field(default_factory=dict)

    def allow(self, key: str) -> bool:
        now = self.clock()
        self._compact(now)
        window = self._events[key]
        cutoff = now - self.window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= self.max_requests:
            self._last_seen[key] = now
            return False
        window.append(now)
        self._last_seen[key] = now
        return True

    def _compact(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for key in list(self._events):
            window = self._events[key]
            while window and window[0] <= cutoff:
                window.popleft()
            if not window:
                self._events.pop(key, None)
                self._last_seen.pop(key, None)

        overflow = len(self._events) - self.max_keys
        if overflow <= 0:
            return
        stale_keys = sorted(self._last_seen, key=self._last_seen.get)
        for key in stale_keys[:overflow]:
            self._events.pop(key, None)
            self._last_seen.pop(key, None)
