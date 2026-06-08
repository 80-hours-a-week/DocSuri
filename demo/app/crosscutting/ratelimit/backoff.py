"""Rate-limit + retry primitives (AGENTS.md §4.5).

Two pieces:

* `TokenBucket` — in-memory async token bucket. One instance per external
  host (arXiv, Semantic Scholar, PubMed, ...). Refills continuously at
  `rate_per_sec`. `acquire()` waits if the bucket is empty.
* `RateLimitedRetry` — a thin wrapper over `tenacity.AsyncRetrying` that
  retries on 5xx / 429 / `httpx.TransportError`. Plays well with
  `TokenBucket` — the bucket throttles, this handles transient failures.

Both are concurrency-safe (use `asyncio.Lock`) and intentionally tiny —
Sprint 1 walking skeleton. Prometheus counters and per-user quotas land in
Sprint 3 (`crosscutting/audit`).
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class TokenBucket:
    """Async-safe token bucket. Refills `rate_per_sec` tokens continuously."""

    def __init__(self, *, rate_per_sec: float, capacity: int) -> None:
        if rate_per_sec <= 0 or capacity <= 0:
            raise ValueError("rate_per_sec and capacity must be positive")
        self._rate = rate_per_sec
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, n: float = 1.0) -> None:
        """Block until `n` tokens are available, then consume them."""
        if n > self._capacity:
            raise ValueError(f"requested {n} > capacity {self._capacity}")
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return
                deficit = n - self._tokens
                wait_s = deficit / self._rate
            # Release lock while sleeping so other callers can proceed/refill.
            await asyncio.sleep(wait_s)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated
        if elapsed <= 0:
            return
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._updated = now


def _is_retryable(exc: BaseException) -> bool:
    """Retry on transport errors and HTTP 429 / 5xx."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or 500 <= code < 600
    return False


class RateLimitedRetry:
    """Decorator factory wrapping an async function in tenacity retries.

    Usage:

        @RateLimitedRetry(max_attempts=3)
        async def call(...): ...

    A fresh `AsyncRetrying` is built per invocation so per-call statistics
    don't leak between concurrent callers.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        initial_wait: float = 0.5,
        max_wait: float = 8.0,
    ) -> None:
        self._max_attempts = max_attempts
        self._initial_wait = initial_wait
        self._max_wait = max_wait

    def _build_policy(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=self._initial_wait, max=self._max_wait),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )

    def __call__(self, fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                async for attempt in self._build_policy():
                    with attempt:
                        return await fn(*args, **kwargs)
            except RetryError as e:  # pragma: no cover — reraise=True bypasses
                exc = e.last_attempt.exception()
                if exc is not None:
                    raise exc from e
                raise
            raise RuntimeError("unreachable")  # for type checker

        return wrapper


# Re-export for callers that want to construct their own policies.
__all__ = ["RateLimitedRetry", "RetryError", "TokenBucket"]


def _annotate(_fn: Callable[..., Any]) -> None:  # pragma: no cover
    """No-op placeholder — kept for symmetry with future audit hooks."""
