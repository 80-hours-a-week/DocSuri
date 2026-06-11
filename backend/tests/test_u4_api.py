"""U4 HTTP 표면 검증 — POST /api/citations (TRACE-01b 백엔드 절반)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docsuri.app import create_app

CENTER = {
    "id": "2401.00001",
    "title": "Center Paper",
    "authors": ["Kim"],
    "year": 2024,
    "citations": 10,
    "similarity": 0.9,
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_citations_desktop_graph(client):
    resp = client.post(
        "/api/citations", json={"paper": CENTER, "viewport_width": 1280}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"]["render"] == "graph"
    assert body["view"]["center"]["id"] == CENTER["id"]
    assert body["view"]["outgoing"] and body["view"]["incoming"]
    assert body["view"]["max_nodes"] == 30


def test_citations_mobile_and_undergrad_list(client):
    mobile = client.post(
        "/api/citations", json={"paper": CENTER, "viewport_width": 360}
    ).json()
    assert mobile["view"]["render"] == "list"  # NFR-MOBILE-05

    undergrad = client.post(
        "/api/citations",
        json={"paper": CENTER, "viewport_width": 1280, "persona": "undergrad"},
    ).json()
    assert undergrad["view"]["render"] == "list"  # TRACE-02 그래프 미표시


def test_citations_top_influence_sorted(client):
    body = client.post(
        "/api/citations", json={"paper": CENTER, "viewport_width": 1280}
    ).json()
    top = body["top_influence"]
    assert 1 <= len(top) <= 3
    citations = [p["citations"] for p in top]
    assert citations == sorted(citations, reverse=True)  # 피인용 내림차순


def test_citations_rejects_blank_paper_id(client):
    resp = client.post(
        "/api/citations",
        json={"paper": {**CENTER, "id": ""}, "viewport_width": 1280},
    )
    assert resp.status_code == 422
