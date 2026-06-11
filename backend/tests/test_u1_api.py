"""U1 HTTP 표면 검증 — FastAPI TestClient (자격 증명 불필요, mock)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from docsuri.app import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_search_envelope_shape(client):
    resp = client.post(
        "/api/search",
        json={
            "query": "retrieval augmented generation",
            "filters": {"year_min": 2023, "year_max": 2026, "field_tags": []},
            "sort_key": "citations",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"result", "query_mapping"}
    result = body["result"]
    assert set(result) == {"query", "expanded_terms", "papers", "filters", "lang"}
    assert len(result["papers"]) == 20
    cites = [p["citations"] for p in result["papers"]]
    assert cites == sorted(cites, reverse=True)


def test_search_korean_returns_mapping(client):
    resp = client.post("/api/search", json={"query": "트랜스포머가 뭔가요"})
    body = resp.json()
    assert body["result"]["lang"] == "ko"
    assert body["query_mapping"] is not None
    assert "transformer" in body["query_mapping"]["en_keywords"]


def test_blank_and_missing_query_rejected(client):
    # #3 입력 검증 — 비용 발생 경로 진입 전 422로 차단
    assert client.post("/api/search", json={"query": "   "}).status_code == 422
    assert client.post("/api/search", json={"query": ""}).status_code == 422
    assert client.post("/api/search", json={}).status_code == 422
