# DO NOT EDIT. Generated from the JSON Schema SSOT in shared/ by tools/generate.py.
# Change the schema and regenerate (§5-B); never hand-edit.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, RootModel


class NewArxivEvent(BaseModel):
    """
    New-arXiv notification event (Q12=B). 🟡 CONSUMED shape {eventId, arxivRef} is FROZEN-adjacent (locked by completed U1 FD, domain-entities.md §5); only the upstream PRODUCER wire contract stays PROVISIONAL (external notifier undecided). Producer: external/upstream notifier → Event Bus (shared capability; outside U1). Consumer: U1.NewArxivEventHandler.onNewArxivEvent(event: NewArxivEvent) -> IngestionJob → RefreshOrchestrationService dispatches to IngestionPipelineService. Delivery: ⚠️ at-least-once. Idempotency: duplicate-consume prevention via DeduplicationGuard DUPLICATE verdict (component-methods.md isNew -> DedupDecision{NEW|CHANGED|DUPLICATE}); on DUPLICATE the pipeline short-circuits (BR-12). Completion acked via U1.NewArxivEventHandler.ackEvent(eventId) -> void. Trace: FR-6, US-I2, BR-12, DQ3, DQ6.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    eventId: str = Field(
        ...,
        description='Event identifier (processing-completion ack key + idempotency boundary). Trace: events.md §4.1, BR-12.',
    )
    arxivRef: str = Field(
        ...,
        description='arXiv reference of the new paper (ingestion target identifier — resolved to vector-spec.md paperId/arxivId). Trace: events.md §4.1, FR-6.',
    )


class IngestError(BaseModel):
    """
    Generalized ingestion error descriptor (PROVISIONAL — U1 FD refines). Carries the failing pipeline stage and a non-sensitive error indication only; no PII/secrets (SEC-3), no internal stack traces/debug (SEC-9).
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    stage: str = Field(
        ...,
        description='Pipeline stage at which the failure occurred (e.g. fetch/parse/chunk/embed/index — generalized label). Trace: events.md §4.2, RES-7.',
    )
    error: str = Field(
        ...,
        description='Generalized, non-sensitive failure reason/code (no PII/secrets/stack trace — SEC-3/SEC-9). Trace: events.md §4.2.',
    )


class IngestionFailureSignal(BaseModel):
    """
    Ingestion-stage failure signaled as an observability/alerting signal. Producer: U1.IngestFailureHandler.emitFailureSignal(jobId: JobId, error: IngestError) -> void (after classify/retry/DLQ, orchestrated by IngestionResilienceService). Consumer: U6.ObservabilityHub (structured logs + alert routing; component-dependency.md U1-Ingestion → U6.ObservabilityHub event). Delivery: at-least-once → U6 aggregates idempotently. Payload MUST NOT carry PII/secrets (SEC-3); MUST NOT carry internal stack traces/debug detail (SEC-9). Trace: RES-7, US-I2, US-I3, NFR-O1.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    jobId: str = Field(
        ...,
        description='Ingestion job identifier (JobId) the failure pertains to. Trace: events.md §4.2, RES-7.',
    )
    error: IngestError = Field(
        ...,
        description='Generalized failure descriptor (IngestError). No PII/secrets/stack traces (SEC-3/SEC-9). Trace: events.md §4.2.',
    )


class U1IngestionBackboneEvents(RootModel[NewArxivEvent | IngestionFailureSignal]):
    root: NewArxivEvent | IngestionFailureSignal = Field(
        ...,
        description='🟡 PROVISIONAL (events.md §4 — refined in U1 FD). U1 ingestion backbone events. NOT on the user synchronous path (services.md U1, component-dependency.md §1). Contains: NewArxivEvent (consumed by U1) and IngestionFailureSignal (emitted by U1 → U6). Use $defs root selection to validate a specific shape.',
        title='U1 Ingestion Backbone Events',
    )
