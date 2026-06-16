from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(slots=True)
class InMemoryRateLimiter:
    max_requests: int = 60
    window_seconds: float = 60.0
    clock: Callable[[], float] = time.time
    _events: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, key: str) -> bool:
        now = self.clock()
        window = self._events[key]
        cutoff = now - self.window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True
