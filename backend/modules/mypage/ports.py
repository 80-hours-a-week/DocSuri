"""U10 My Page — port interface (typing.Protocol seam).

Mirrors U4's port-decoupling pattern: the in-memory adapter is the mock-first default (the
app-shell mounts U10 with no live infra), and the SQL adapter swaps in through the same
interface. ``owner_id`` is a required argument on every method, so an adapter structurally
cannot return another owner's row.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import Subscription


@runtime_checkable
class SubscriptionRepository(Protocol):
    def get(self, owner_id: str) -> Subscription | None: ...
    def upsert(self, item: Subscription) -> Subscription: ...
