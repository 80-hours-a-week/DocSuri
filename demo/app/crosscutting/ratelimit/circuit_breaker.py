"""Async-compatible Circuit Breaker for per-source resilience.

Matches the pybreaker interface (fail_max, reset_timeout) without an
external dependency. Uses asyncio.Lock for safe state transitions.

Usage (adapter level — CB and retry are independent):
    cb = CircuitBreaker(fail_max=5, reset_timeout=30)
    async with cb:                       # CB: adapter level
        return await self._client.search(...)  # retry: client level
"""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    """Raised when the circuit is OPEN and the call is immediately rejected."""


class CircuitBreaker:
    """Per-source async circuit breaker.

    States:
    - CLOSED  — normal operation; failures are counted.
    - OPEN    — fail_max reached; all calls raise CircuitBreakerOpen.
    - HALF-OPEN — reset_timeout elapsed; one probe allowed.
                  Success → CLOSED. Failure → OPEN again.

    Time: O(1) per __aenter__ / __aexit__
    Edge: asyncio.CancelledError is never counted as a failure.
    Edge: CircuitBreakerOpen itself is never double-counted.
    """

    def __init__(self, *, fail_max: int = 5, reset_timeout: float = 30.0) -> None:
        self._fail_max = fail_max
        self._reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        return time.monotonic() - self._opened_at < self._reset_timeout

    async def __aenter__(self) -> CircuitBreaker:
        async with self._lock:
            if self._opened_at is not None:
                elapsed = time.monotonic() - self._opened_at
                if elapsed < self._reset_timeout:
                    raise CircuitBreakerOpen(
                        f"circuit open ({elapsed:.0f}s/{self._reset_timeout:.0f}s elapsed)"
                    )
                # Half-open: reset tentatively and let one probe through.
                logger.debug("circuit.half_open")
                self._failures = 0
                self._opened_at = None
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool:
        if exc_type is None or exc_type is asyncio.CancelledError:
            async with self._lock:
                self._failures = 0
        elif exc_type is not CircuitBreakerOpen:
            async with self._lock:
                self._failures += 1
                if self._failures >= self._fail_max:
                    self._opened_at = time.monotonic()
                    logger.warning(
                        "circuit.opened fail_max=%d reached", self._fail_max
                    )
        return False  # never suppress exceptions
