"""Domain event topic catalog.

Single SNS topic — one per environment — carries every domain event. Fan-out
to per-domain SQS queues happens via SNS subscription filter policy on the
``domain`` and ``event`` message attributes. This keeps topic count O(1) and
moves the routing decision to infra, not app code.
"""

from __future__ import annotations

from enum import StrEnum


class DomainTopic(StrEnum):
    PAPER_INGESTED = "paper.ingested"           # #01b
    SUMMARY_REQUESTED = "summary.requested"     # #02
    TRANSLATION_REQUESTED = "translation.requested"  # #03
    MONITORING_TICK = "monitoring.tick"         # #04
    GAP_ANALYSIS_REQUESTED = "gap.requested"    # #06
    PROJECT_TREND_REQUESTED = "trend.requested"  # #07
    CITATION_GRAPH_EXPAND = "citation.expand"   # #08
    REPRODUCIBILITY_EVAL = "repro.eval"         # #09
    NOTIFICATION_DISPATCH = "notification.dispatch"  # #04 fan-out tail
