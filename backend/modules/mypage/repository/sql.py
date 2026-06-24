"""U10 My Page — SQLAlchemy subscription repository (production adapter, mirrors U4 D10).

Swaps in behind the same port as the in-memory default (tests/app-shell run on in-memory;
production injects this against the U3-inherited RDS PostgreSQL). Table maps 1:1 to
``migrations/001_create_mypage_subscriptions.sql``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ..models import Subscription
from ..schemas import SubscriptionPlan, SubscriptionStatusValue


class Base(DeclarativeBase):
    pass


class SubscriptionTable(Base):
    __tablename__ = "mypage_subscriptions"

    owner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _to_domain(row: SubscriptionTable) -> Subscription:
    return Subscription(
        owner_id=row.owner_id,
        plan=SubscriptionPlan(row.plan),
        status=SubscriptionStatusValue(row.status),
        started_at=row.started_at,
        current_period_end=row.current_period_end,
        canceled_at=row.canceled_at,
    )


class SqlSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def get(self, owner_id: str) -> Subscription | None:
        row = (
            self._s.query(SubscriptionTable)
            .filter(SubscriptionTable.owner_id == owner_id)
            .first()
        )
        return _to_domain(row) if row else None

    def upsert(self, item: Subscription) -> Subscription:
        row = (
            self._s.query(SubscriptionTable)
            .filter(SubscriptionTable.owner_id == item.owner_id)
            .first()
        )
        if row is None:
            row = SubscriptionTable(owner_id=item.owner_id)
            self._s.add(row)
        row.plan = item.plan.value
        row.status = item.status.value
        row.started_at = item.started_at
        row.current_period_end = item.current_period_end
        row.canceled_at = item.canceled_at
        self._s.flush()
        return item
