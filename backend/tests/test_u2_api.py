"""U2 HTTP 표면 검증 — /api/summaries · /api/translations (u2_ui_build_plan A3).

DocumentIngestor는 실 arXiv API를 호출하므로 stub ingestor를 주입한
라우터로 테스트한다 — 외부 네트워크 0 (mock 모드 원칙).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from docsuri.u0.adapters import build_u0
from docsuri.u0.config import load_settings
from docsuri.u2.api import build_router
from docsuri.u2.models import DocumentSource, PaperSection, PaperText
from docsuri.u2.service import U2Services, build_u2


class StubIngestor:
    """실 arXiv 호출 대체 — 결정적 PaperText."""

    def ingest(self, source: DocumentSource) -> PaperText:
        if source.value.endswith("/0000.00000"):
            raise ValueError("존재하지 않는 논문")
        return PaperText(
            paper_id=source.paper_id or "2606.13443",
            title="Stub Paper on Transformer Attention",
            sections=[
                PaperSection(
                    id="abstract",
                    title="Abstract",
                    text=(
                        "We study transformer attention with RAG. "
                        "Our method improves retrieval. E = mc^2 holds."
                    ),
                )
            ],
        )


@pytest.fixture(scope="module")
def client() -> TestClient:
    settings = load_settings()
    assert settings.adapter_mode == "mock"
    u0 = build_u0(settings)
    real = build_u2(u0)
    services = U2Services(
        ingestor=StubIngestor(),  # type: ignore[arg-type]
        summary_engine=real.summary_engine,
        translator=real.translator,
    )
    app = FastAPI()
    app.include_router(build_router(services))
    return TestClient(app)


def test_summary_pro_sections_and_envelope(client):
    resp = client.post("/api/summaries", json={"paper_id": "2606.13443", "mode": "pro"})
    assert resp.status_code == 200
    body = resp.json()
    sections = body["summary"]["sections"]
    assert set(sections) == {"question", "method", "result", "limit"}  # COMP-01 4섹션
    assert all(sections[k] for k in sections)
    assert body["summary"]["mode"] == "pro"
    assert body["summary"]["cost"]["tokens_in"] > 0
    assert "readability" in body  # 엔벨로프 보조 필드
    assert body["paper"]["abstract"].startswith("We study")  # COMP-04 원문 패널용


def test_summary_modes_differ_and_vocab(client):
    pro = client.post("/api/summaries", json={"paper_id": "2606.13443", "mode": "pro"}).json()
    undergrad = client.post(
        "/api/summaries", json={"paper_id": "2606.13443", "mode": "undergrad"}
    ).json()
    assert pro["summary"]["sections"] != undergrad["summary"]["sections"]  # 톤 분기
    terms = [v["term"].lower() for v in pro["summary"]["vocab_explanations"]]
    assert "transformer" in terms  # 용어 사전 적중 (NFR-LANG-03)


def test_summary_cache_second_call(client):
    first = client.post("/api/summaries", json={"paper_id": "2606.13443", "mode": "pro"}).json()
    second = client.post("/api/summaries", json={"paper_id": "2606.13443", "mode": "pro"}).json()
    assert second["summary"] == first["summary"]  # 7d 캐시 적중 — 동일 결과


def test_summary_validation_and_not_found(client):
    assert client.post("/api/summaries", json={"mode": "pro"}).status_code == 422
    assert (
        client.post(
            "/api/summaries", json={"paper_id": "2606.13443", "arxiv_url": "https://arxiv.org/abs/2606.13443"}
        ).status_code
        == 422
    )  # 둘 다 보내면 거부
    assert client.post("/api/summaries", json={"arxiv_url": "https://evil.test/abs/1"}).status_code == 422
    assert client.post("/api/summaries", json={"paper_id": "0000.00000"}).status_code == 404


def test_translation_glossary_hits(client):
    resp = client.post(
        "/api/translations",
        json={"source_excerpt": "The transformer uses attention.", "input_mode": "desktop"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source_excerpt"] == "The transformer uses attention."
    assert body["target_text"]
    hit_terms = [h["term"].lower() for h in body["glossary_hits"]]
    assert "transformer" in hit_terms  # 일관 번역 (COMP-04 AC)


def test_translation_rejects_blank_and_oversize(client):
    assert client.post("/api/translations", json={"source_excerpt": "  "}).status_code == 422
    assert (
        client.post("/api/translations", json={"source_excerpt": "x" * 2001}).status_code == 422
    )
