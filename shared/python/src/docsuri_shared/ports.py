"""Cross-cutting hook interfaces (ports.md) — the dependency-inversion seam.

These are method interfaces, not data schemas, so they cannot be generated from JSON
Schema; they are authored here from ``ports.md`` (the SSOT for *these*). §5-A is now
decided (backend = Python), which unblocks these ``typing.Protocol`` stubs (§5-B).

Direction: **U6 implements; U2/U1 depend by injection.** Both sides depend on these
abstractions — not on a concrete U6 module — which is what breaks the U2↔U6 sync cycle
(ports.md §1). Single authority: U2 must NOT re-implement grounding/cost (ports.md §5).

State: ``enforce`` and ``get_budget_state`` are 🔒 FROZEN (locked by
``component-methods.md``); everything else is 🟡 PROVISIONAL and syncs when U6 FD lands.
Method names are pythonic ``snake_case``; each docstring cites the spec's camelCase name.
Provisional payload shapes are intentionally loose aliases (``Any``) until U6 FD fixes them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol, runtime_checkable

from .vector_spec import IndexRecord

__all__ = [
    "Verdict",
    "GroundingDecision",
    "BudgetState",
    "CandidateResponse",
    "RetrievedRecordSet",
    "GroundingEvalSet",
    "GroundingEvalReport",
    "StructuredLogEntry",
    "AuditEvent",
    "Span",
    "TraceContext",
    "MetricName",
    "MetricValue",
    "TagSet",
    "SpanName",
    "GroundingEnforcementHook",
    "CostGuardCircuitBreaker",
    "ObservabilityHub",
]

# --- Grounding (ports.md §2) -------------------------------------------------
Verdict = Literal["pass", "block", "abstain"]

# PROVISIONAL opaque shapes — refined in U6/U2 FD (ports.md §2 type cards).
CandidateResponse = Any  # U2 ranked candidate (RankedResults), shaped by GroundingAdapter
RetrievedRecordSet = Sequence[IndexRecord]  # real records grounding is verified against
GroundingEvalSet = Any  # QT-1 evaluation case set
GroundingEvalReport = Any  # per-case results + fabrication/abstain summary


class GroundingDecision(Protocol):
    """enforce result (ports.md §2): a verdict plus the list of grounding violations.

    Not ``@runtime_checkable`` — it is a data shape; an ``isinstance`` check would only
    test attribute *presence*, not types, which is misleading. Use it for static typing.
    """

    verdict: Verdict
    violations: Sequence[Any]


@runtime_checkable
class GroundingEnforcementHook(Protocol):
    """Grounding single-authority gate. Implemented by U6 (GroundingGuardService);
    the sole invocation site is the U6 gateway post-handler. U2 only shapes input and
    maps the verdict — it MUST NOT re-implement ``enforce``."""

    def enforce(
        self, candidate: CandidateResponse, retrieved: RetrievedRecordSet
    ) -> GroundingDecision:
        """🔒 FROZEN — spec: ``enforce(candidate, retrieved) -> GroundingDecision``.

        FR-5/QT-1 single runtime gate: map a candidate response to real retrieved
        records, verify AI-text provenance, decide pass/block/abstain.
        Trace: FR-5, QT-1, US-D5/D6/R1.
        """
        ...

    def run_eval_set(self, eval_set: GroundingEvalSet) -> GroundingEvalReport:
        """🟡 PROVISIONAL — spec: ``runEvalSet(evalSet) -> GroundingEvalReport``.

        Run the QT-1 eval set through the *same* hook (zero-fabrication / abstain report).
        """
        ...


# --- Cost guard (ports.md §3) ------------------------------------------------
class BudgetState(Protocol):
    """Cost-guard branching signal (ports.md §3): budget tier + advisory degrade mode
    + circuit state. ``degrade_mode`` tells U2 to drop embedding/LLM rerank and fall
    back to lexical-only (the embedding space itself is unchanged).
    Not ``@runtime_checkable`` (data shape — see GroundingDecision).

    Field name mapping to the spec (camelCase): ``tier`` ↔ ``tier``,
    ``degrade_mode`` ↔ ``degradeMode``, ``circuit_state`` ↔ ``circuitState``.
    """

    tier: Any
    degrade_mode: Any  # spec: degradeMode
    circuit_state: Any  # spec: circuitState


@runtime_checkable
class CostGuardCircuitBreaker(Protocol):
    """Cost-degrade state query. Implemented by U6 (CostGuardService). U2 reads the
    advisory state and branches — it MUST NOT judge cost/budget itself; accumulation /
    threshold / circuit transition (``recordSpend`` / ``evaluateCircuit``) are
    U6-internal and intentionally absent from this port."""

    def get_budget_state(self) -> BudgetState:
        """🔒 FROZEN — spec: ``getBudgetState() -> BudgetState``.

        Near-real-time threshold state + advisory degrade mode for sync fallback branching.
        """
        ...


# --- Observability (ports.md §4) ---------------------------------------------
# PROVISIONAL primitive/opaque types — refined in U6 FD (ports.md §4 type cards).
MetricName = str
MetricValue = float
TagSet = Mapping[str, str]
SpanName = str
TraceContext = Any
Span = Any
StructuredLogEntry = Any  # requestId-correlated structured fields (no PII/secrets)
AuditEvent = Any  # core change / authorization decision (append-only)


@runtime_checkable
class ObservabilityHub(Protocol):
    """Single observability collector (all units depend, NFR-O1). Implemented by U6
    (ObservabilityService). Entries carry no PII/secrets (SEC-3) and no internal
    scores/owner/debug fields (SEC-9)."""

    def emit_metric(self, name: MetricName, value: MetricValue, tags: TagSet) -> None:
        """🟡 PROVISIONAL — spec: ``emitMetric(name, value, tags) -> void``.

        Trace: NFR-O1, RES-5.
        """
        ...

    def emit_log(self, entry: StructuredLogEntry) -> None:
        """🟡 PROVISIONAL — spec: ``emitLog(entry) -> void`` (PII/secrets blocked).

        Trace: NFR-O1, SEC-3.
        """
        ...

    def start_span(self, name: SpanName, context: TraceContext) -> Span:
        """🟡 PROVISIONAL — spec: ``startSpan(name, context) -> Span``. Trace: NFR-O1."""
        ...

    def audit_append(self, event: AuditEvent) -> None:
        """🟡 PROVISIONAL — spec: ``auditAppend(event) -> void`` (append-only, 90 days+).

        Trace: SEC-13, SEC-14.
        """
        ...
