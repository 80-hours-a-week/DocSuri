from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.modules.accounts.models import Principal, UserRole
from backend.modules.citation_graph import controller


class FixtureProvider:
    async def references(self, paper_id: str, limit: int):
        return "ok", [
            {
                "paperId": "s2-a",
                "title": "A paper",
                "year": 2021,
                "citationCount": 10,
                "externalIds": {"ArXiv": "2101.00001"},
                "url": "https://arxiv.org/abs/2101.00001",
            },
            {
                "paperId": "s2-b",
                "title": "B paper",
                "year": 2022,
                "citationCount": 2,
                "externalIds": {"DOI": "10.1/b"},
            },
            {"title": "Unresolved paper", "year": 2020},
        ]


def _client(monkeypatch):
    monkeypatch.setenv("CITATION_GRAPH_ENABLED", "true")
    app = create_app(Settings(env="test", database_url="sqlite://"))
    app.dependency_overrides[controller.get_principal] = lambda: Principal(
        user_id=str(uuid4()), role=UserRole.USER
    )
    app.dependency_overrides[controller.get_provider] = lambda: FixtureProvider()
    app.dependency_overrides[controller.get_snapshot_store] = controller.InMemorySnapshotStore
    return TestClient(app)


def test_citation_tree_bounds_and_unresolved(monkeypatch) -> None:
    resp = _client(monkeypatch).get("/api/papers/root/citation-tree")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "Partial"
    assert body["depthReturned"] <= 2
    assert len(body["nodes"]) <= 50
    assert body["nodes"][0]["nodeId"] == "2101.00001"
    assert body["nodes"][0]["saveable"] is True
    assert body["unresolved"][0]["title"] == "Unresolved paper"


def test_feature_flag_blocks_endpoint_by_default() -> None:
    app = create_app(Settings(env="test", database_url="sqlite://"))
    app.dependency_overrides[controller.get_principal] = lambda: Principal(
        user_id=str(uuid4()), role=UserRole.USER
    )
    assert TestClient(app).get("/api/papers/root/citation-tree").status_code == 404


@pytest.mark.skipif(
    not os.getenv("CITATION_GRAPH_CONTRACT_TESTS"),
    reason="opt-in real provider contract test",
)
def test_semantic_scholar_contract_test_is_opt_in() -> None:
    assert os.getenv("SEMANTIC_SCHOLAR_API_KEY")
