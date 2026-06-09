"""Celery execution engine (AGENTS.md §5.3).

The ``app`` Celery instance is the single bus for both:
  • single-shot tasks (#01b ingest, #02 summary, embedding refresh, etc.)
  • SQS-dispatched workers — the SQS consumer translates an inbound message
    into a Celery ``.apply_async`` call so retry / backoff / dead-letter
    policies are uniform across both paths.

Retry policy is consolidated in ``policies.py``. Domain modules MUST import
those policies and never roll their own — otherwise per-DB SLA differences
silently diverge.
"""

from app.infra.celery.app import app

__all__ = ["app"]
