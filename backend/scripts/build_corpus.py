"""시드 코퍼스 빌더 — CorpusIndex 1회 빌드 (A1·A5, U0 §5).

arXiv 공개 API에서 AI/ML 논문 100편 메타데이터를 수집해
data/corpus_seed.json 으로 저장한다. 인용수는 Semantic Scholar 배치 API를
시도하고, 실패하면 결정적 placeholder(해시 기반)로 채우고 출처를 표기한다.

실행: uv run python scripts/build_corpus.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

ARXIV_URL = (
    "https://export.arxiv.org/api/query"
    "?search_query=cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.CV+OR+cat:cs.AI"
    "&sortBy=submittedDate&sortOrder=descending&start=0&max_results=100"
)
SS_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch?fields=citationCount"
ATOM = "{http://www.w3.org/2005/Atom}"
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "corpus_seed.json"


def fetch_arxiv(client: httpx.Client) -> list[dict]:
    response = client.get(ARXIV_URL, timeout=30.0)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    papers = []
    for entry in root.findall(f"{ATOM}entry"):
        raw_id = entry.findtext(f"{ATOM}id", "")  # http://arxiv.org/abs/2401.12345v1
        arxiv_id = raw_id.rsplit("/", 1)[-1].rsplit("v", 1)[0]
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
        year = int((entry.findtext(f"{ATOM}published") or "0000")[:4])
        authors = [
            a.findtext(f"{ATOM}name", "") for a in entry.findall(f"{ATOM}author")
        ]
        tags = [
            c.get("term", "")
            for c in entry.findall("{http://arxiv.org/schemas/atom}primary_category")
            + entry.findall(f"{ATOM}category")
        ]
        papers.append(
            {
                "id": arxiv_id,
                "title": title,
                "authors": authors[:8],
                "year": year,
                "citations": 0,
                "field_tags": sorted(set(t for t in tags if t)),
                "abstract_len": len(summary),
            }
        )
    return papers


def enrich_citations(client: httpx.Client, papers: list[dict]) -> str:
    """Semantic Scholar 배치로 인용수 보강. 실패 시 결정적 placeholder."""
    try:
        response = client.post(
            SS_BATCH_URL,
            json={"ids": [f"arXiv:{p['id']}" for p in papers]},
            timeout=30.0,
        )
        response.raise_for_status()
        rows = response.json()
        for paper, row in zip(papers, rows):
            paper["citations"] = (row or {}).get("citationCount") or 0
        return "semantic_scholar"
    except (httpx.HTTPError, ValueError):
        for paper in papers:
            digest = hashlib.sha256(paper["id"].encode()).digest()
            paper["citations"] = int.from_bytes(digest[:2], "big") % 500
        return "placeholder(deterministic-hash)"


def main() -> int:
    with httpx.Client(headers={"User-Agent": "DocSuri-corpus-builder/0.1"}) as client:
        papers = fetch_arxiv(client)
        if len(papers) < 100:
            print(f"경고: arXiv가 {len(papers)}편만 반환 — 100편 미만", file=sys.stderr)
        citations_source = enrich_citations(client, papers)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "source": "arXiv API (cs.LG|cs.CL|cs.CV|cs.AI, submittedDate desc)",
                "citations_source": citations_source,
                "count": len(papers),
                "papers": papers,
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    print(f"OK: {len(papers)}편 저장 → {OUT_PATH} (인용수 출처: {citations_source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
