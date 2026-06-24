"""U10 My Page — in-memory subscription repository (mock-first default, mirrors U4 D10).

The default adapter: the app-shell mounts U10 with it so the module serves with NO live
database, and the test suite runs green without infra. The production ``SqlSubscriptionRepository``
(``sql.py``) swaps in behind the same port.
"""

from __future__ import annotations

from ..models import Subscription


class InMemorySubscriptionRepository:
    def __init__(self) -> None:
        self._by_owner: dict[str, Subscription] = {}

    def get(self, owner_id: str) -> Subscription | None:
        return self._by_owner.get(owner_id)

    def upsert(self, item: Subscription) -> Subscription:
        self._by_owner[item.owner_id] = item
        return item
