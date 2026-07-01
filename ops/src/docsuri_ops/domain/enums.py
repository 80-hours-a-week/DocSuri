from __future__ import annotations

from enum import StrEnum


class IncidentClass(StrEnum):
    COST_EXPLOSION = "a"
    HALLUCINATION = "b"
    PARTIAL_RESULT = "c"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CircuitState(StrEnum):
    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


class DegradeMode(StrEnum):
    NORMAL = "NORMAL"
    RERANK_OFF = "RERANK_OFF"
    LEXICAL_ONLY = "LEXICAL_ONLY"


class SignalKind(StrEnum):
    METRIC = "metric"
    LOG = "log"
    AUDIT = "audit"
    USAGE = "usage"
    GROUNDING = "grounding"
    PARTIAL_RESULT = "partial_result"
    INGESTION_FAILURE = "ingestion_failure"
    ACCOUNT_ABUSE = "account_abuse"
    AUTH_FAILURE = "auth_failure"
    HEALTH = "health"
