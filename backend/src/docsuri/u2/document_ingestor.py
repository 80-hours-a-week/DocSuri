"""Document ingestion for U2.

The buildable path is raw_text so U2 can run with deterministic U0 mocks. PDF
and arXiv branches are extension points aligned with the Python/FastAPI choice
from the AWS tech stack investigation.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from docsuri.u0.http_policy import request_with_retry
from docsuri.u0.ports import Telemetry, TelemetryEvent

from .models import DocumentSource, PaperFigure, PaperSection, PaperText


class DocumentIngestor:
    def __init__(self, telemetry: Telemetry | None = None) -> None:
        self._telemetry = telemetry

    def ingest(self, source: DocumentSource) -> PaperText:
        if source.kind == "raw_text":
            return self._from_raw_text(source)
        if source.kind == "pdf_path":
            return self._from_pdf_path(source)
        if source.kind == "arxiv_url":
            return self._from_arxiv_url(source)
        if source.kind == "url":
            if "arxiv.org/" not in source.value:
                raise ValueError("현재 U2 URL 입력은 arXiv URL만 지원합니다.")
            return self._from_arxiv_url(source)
        raise ValueError(f"지원하지 않는 문서 소스입니다: {source.kind}")

    def _from_raw_text(self, source: DocumentSource) -> PaperText:
        text = source.value.strip()
        if not text:
            raise ValueError("문서 본문이 비어 있습니다.")
        paper_id = source.paper_id or _stable_id(text)
        return PaperText(
            paper_id=paper_id,
            title=source.title or "Untitled paper",
            sections=[PaperSection(id="body", title="본문", text=text)],
        )

    def _from_pdf_path(self, source: DocumentSource) -> PaperText:
        path = Path(source.value)
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            import fitz  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "PDF 추출에는 PyMuPDF(fitz)가 필요합니다. raw_text 경로로 테스트하거나 "
                "PDF 추출 의존성을 설치해 주세요."
            ) from exc
        doc = fitz.open(path)
        text = "\n\n".join(page.get_text("text") for page in doc)
        if not text.strip():
            raise ValueError("PDF에서 추출된 본문이 비어 있습니다.")
        return PaperText(
            paper_id=source.paper_id or _stable_id(str(path.resolve())),
            title=source.title or path.stem,
            sections=[PaperSection(id="body", title="본문", text=text)],
        )

    def _from_arxiv_url(self, source: DocumentSource) -> PaperText:
        arxiv_id = _extract_arxiv_id(source.value)
        if not arxiv_id:
            raise ValueError("arXiv URL에서 논문 ID를 찾을 수 없습니다.")
        api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        with httpx.Client(timeout=10.0) as client:
            response = request_with_retry(client, "GET", api_url)
        response.raise_for_status()
        paper = _parse_arxiv_response(response.text, fallback_id=arxiv_id)
        if self._telemetry:
            self._telemetry.record(
                TelemetryEvent(op="document.ingest", latency_ms=0.0, cache_hit=False)
            )
        return paper


def _stable_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _extract_arxiv_id(url: str) -> str | None:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", url)
    if not match:
        return None
    return match.group(1).removesuffix(".pdf")


def _parse_arxiv_response(xml_text: str, fallback_id: str) -> PaperText:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("arXiv 응답 XML을 해석할 수 없습니다.") from exc
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError("arXiv 응답에 entry가 없습니다.")
    title = _node_text(entry, "atom:title", ns) or fallback_id
    summary = _node_text(entry, "atom:summary", ns) or ""
    link = ""
    for node in entry.findall("atom:link", ns):
        if node.attrib.get("rel") == "alternate":
            link = node.attrib.get("href", "")
            break
    return PaperText(
        paper_id=f"arxiv:{fallback_id}",
        title=" ".join(title.split()),
        sections=[PaperSection(id="abstract", title="Abstract", text=" ".join(summary.split()))],
        figures=[
            PaperFigure(
                id="source",
                caption="arXiv abstract metadata",
                context="Full PDF figure extraction is handled by the pdf_path branch.",
            )
        ],
        source_url=link or None,
    )


def _node_text(node: ET.Element, path: str, ns: dict[str, str]) -> str:
    child = node.find(path, ns)
    return child.text if child is not None and child.text else ""
