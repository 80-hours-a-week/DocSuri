"""Task signatures for #01b ingest / #02 summary / embedding refresh.

Domain modules call these via ``.delay(...)`` or ``.apply_async(...)``.
Bodies are intentionally minimal — full implementations land in the per-
feature Sprint backlogs.
"""

from __future__ import annotations

import logging
from typing import Any

from app.infra.celery.app import app
from app.infra.celery.policies import (
    ARXIV_POLICY,
    OPENALEX_POLICY,
    PUBMED_POLICY,
    SEMANTIC_SCHOLAR_POLICY,
)

logger = logging.getLogger(__name__)


@app.task(name="papers.ingest.arxiv", **ARXIV_POLICY)
def ingest_arxiv(arxiv_id: str) -> dict[str, Any]:
    logger.info("ingest.arxiv start", extra={"arxiv_id": arxiv_id})
    raise NotImplementedError("Implemented in Sprint-Backlog-Ingest")


@app.task(name="papers.ingest.semantic_scholar", **SEMANTIC_SCHOLAR_POLICY)
def ingest_semantic_scholar(s2_id: str) -> dict[str, Any]:
    logger.info("ingest.s2 start", extra={"s2_id": s2_id})
    raise NotImplementedError("Implemented in Sprint-Backlog-Ingest")


@app.task(name="papers.ingest.pubmed", **PUBMED_POLICY)
def ingest_pubmed(pmid: str) -> dict[str, Any]:
    logger.info("ingest.pubmed start", extra={"pmid": pmid})
    raise NotImplementedError("Implemented in Sprint-Backlog-Ingest")


@app.task(name="papers.ingest.openalex", **OPENALEX_POLICY)
def ingest_openalex(openalex_id: str) -> dict[str, Any]:
    logger.info("ingest.openalex start", extra={"openalex_id": openalex_id})
    raise NotImplementedError("Implemented in Sprint-Backlog-Ingest")
