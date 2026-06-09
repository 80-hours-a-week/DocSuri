"""Centralised retry policies for Celery tasks (AGENTS.md §4.5, §5.3).

Each paper source has a distinct error profile:

  • **arXiv** — OAI-PMH window can stall for minutes; 503s are common; retry
    cost is tiny but a burst of retries triggers IP blocks.
  • **Semantic Scholar (S2)** — 100 rpm cap unauth, 429s frequent. Backoff
    must respect Retry-After if present.
  • **PubMed E-utilities** — 3 rps hard cap; 5xx storms during outages. NCBI
    explicitly asks third-party clients to back off aggressively.
  • **OpenAlex** — fairly generous (~100 rps polite pool), but 429s arrive
    when the polite-pool email is missing. Long tail of 5xx during their
    nightly snapshots.

Per-source policies live here so a domain task picks the right one with
``@app.task(**ARXIV_POLICY)``. Centralisation also lets §4.6 ops alerts
diff per-source retry rates without grepping the codebase.
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Owner contribution slot — implement the four source policies below.
#
# Each ``*_POLICY`` is a dict suitable for ``@app.task(**POLICY)``. The
# four keys that matter:
#
#   ``autoretry_for``    — tuple of exception classes to retry on.
#   ``retry_backoff``    — True (exponential) or a numeric base.
#   ``retry_backoff_max``— ceiling for the backoff in seconds.
#   ``retry_jitter``     — True to add randomised jitter (recommended).
#   ``max_retries``      — total attempts before pushing to DLQ.
#
# Suggested 5–10 lines of code total. Use the source notes above to set
# values that reflect each provider's SLA. Hints:
#   - PubMed 3 rps + aggressive provider expectations  → small max_retries,
#     long backoff_max so we yield politely.
#   - S2 100 rpm + Retry-After                          → medium retries,
#     honour Retry-After if surfaced via a custom exception.
#   - arXiv soft 503                                    → many retries, but
#     bounded backoff so the worker doesn't hold a slot forever.
#   - OpenAlex generous quota                           → standard policy.
# ----------------------------------------------------------------------

ARXIV_POLICY: dict[str, Any] = {
    # TODO(owner): see header for retry-tuning guidance per AGENTS.md §4.5.
}

SEMANTIC_SCHOLAR_POLICY: dict[str, Any] = {
    # TODO(owner)
}

PUBMED_POLICY: dict[str, Any] = {
    # TODO(owner)
}

OPENALEX_POLICY: dict[str, Any] = {
    # TODO(owner)
}
