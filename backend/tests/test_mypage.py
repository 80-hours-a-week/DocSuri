from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.modules.accounts.models import Principal, UserRole
from backend.modules.mypage import controller
from backend.modules.mypage.repository.memory import InMemorySubscriptionRepository


def _client(monkeypatch, *, principal: Principal | None = None, repo=None) -> TestClient:
    app = create_app(Settings(env="test", database_url="sqlite://"))
    if principal is not None:
        app.dependency_overrides[controller.get_principal] = lambda: principal
    if repo is not None:
        app.dependency_overrides[controller.get_subscription_repo] = lambda: repo
    return TestClient(app)


def _principal() -> Principal:
    return Principal(user_id=str(uuid4()), role=UserRole.USER)


def test_get_subscription_defaults_to_none_when_never_subscribed(monkeypatch) -> None:
    resp = _client(monkeypatch, principal=_principal()).get("/mypage/subscription")
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "FREE"
    assert body["status"] == "NONE"
    assert "startedAt" not in body or body["startedAt"] is None


def test_subscribe_activates_premium_with_period_end(monkeypatch) -> None:
    client = _client(monkeypatch, principal=_principal())
    resp = client.post("/mypage/subscription")
    assert resp.status_code == 201
    body = resp.json()
    assert body["plan"] == "PREMIUM"
    assert body["status"] == "ACTIVE"
    assert body["startedAt"] is not None
    assert body["currentPeriodEnd"] is not None
    assert body["canceledAt"] is None


def test_subscribe_is_idempotent_when_already_active(monkeypatch) -> None:
    repo = InMemorySubscriptionRepository()
    client = _client(monkeypatch, principal=_principal(), repo=repo)
    first = client.post("/mypage/subscription").json()
    second = client.post("/mypage/subscription").json()
    assert first["startedAt"] == second["startedAt"]
    assert second["status"] == "ACTIVE"


def test_cancel_retains_benefit_through_current_period_end(monkeypatch) -> None:
    repo = InMemorySubscriptionRepository()
    client = _client(monkeypatch, principal=_principal(), repo=repo)
    subscribed = client.post("/mypage/subscription").json()

    resp = client.post("/mypage/subscription/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "CANCELED"
    assert body["canceledAt"] is not None
    # Q11: cancellation does not cut access immediately — period end is unchanged.
    assert body["currentPeriodEnd"] == subscribed["currentPeriodEnd"]


def test_cancel_without_active_subscription_is_a_no_op(monkeypatch) -> None:
    resp = _client(monkeypatch, principal=_principal()).post("/mypage/subscription/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "NONE"


def test_subscription_endpoints_require_authentication(monkeypatch) -> None:
    resp = _client(monkeypatch).get("/mypage/subscription")
    assert resp.status_code == 401


@pytest.mark.parametrize("owner_a, owner_b", [(str(uuid4()), str(uuid4()))])
def test_subscriptions_are_owner_scoped(monkeypatch, owner_a, owner_b) -> None:
    repo = InMemorySubscriptionRepository()
    client_a = _client(
        monkeypatch, principal=Principal(user_id=owner_a, role=UserRole.USER), repo=repo
    )
    client_b = _client(
        monkeypatch, principal=Principal(user_id=owner_b, role=UserRole.USER), repo=repo
    )

    client_a.post("/mypage/subscription")
    b_status = client_b.get("/mypage/subscription").json()
    assert b_status["status"] == "NONE"
