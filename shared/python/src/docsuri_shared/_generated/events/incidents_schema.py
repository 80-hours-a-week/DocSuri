# DO NOT EDIT. Generated from the JSON Schema SSOT in shared/ by tools/generate.py.
# Change the schema and regenerate (§5-B); never hand-edit.

from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, RootModel


class Class(StrEnum):
    """
    RES-11 incident class — a=cost explosion / b=hallucination / c=half-baked result. Trace: events.md §5.1, RES-11.
    """

    a = 'a'
    b = 'b'
    c = 'c'


class Severity(StrEnum):
    """
    Incident/alert severity level (enum/level — PROVISIONAL, U6 FD finalizes the level set). Trace: events.md §5.
    """

    info = 'info'
    warning = 'warning'
    critical = 'critical'


class ClassifiedIncident(BaseModel):
    """
    Producer: U6.IncidentEventPublisher.publishIncident(incident: ClassifiedIncident) -> void — publishes AiIncidentDetectorSuite.classify results to a standard schema + audit record. Per-class detectors: CostExplosionDetector(a) / HallucinationDetector(b) / PartialResultDetector(c). Consumer: Event Backbone → IR/COE routing + OpsDashboardService (status consume, listIncidents). Delivery: at-least-once → idempotent dedup correlated by requestId (prevents duplicate page/COE for the same incident). No secrets/PII (SEC-3). Trace: RES-11(a/b/c), NFR-O1, US-R1/R2/R3/R4.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    class_: Class = Field(
        ...,
        alias='class',
        description='RES-11 incident class — a=cost explosion / b=hallucination / c=half-baked result. Trace: events.md §5.1, RES-11.',
    )
    severity: Severity = Field(
        ..., description='Incident severity level. Trace: events.md §5.1.'
    )
    requestId: str = Field(
        ...,
        description='Request correlation identifier (correlation key — links trace/audit; idempotency dedup boundary). Trace: events.md §5.1.',
    )


class OpsAlert(BaseModel):
    """
    Producer: U6.IncidentEventPublisher.publishAlert(alert: OpsAlert) -> void — operational alert for threshold violations/incidents. Consumer: Event Backbone → IR/COE routing. Delivery: at-least-once → consumer idempotently suppresses duplicate alerts. NO secrets/PII exposed (SEC-3). Shape PROVISIONAL — U6 FD refines. Trace: RES-7, RES-11, US-R4.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    severity: Severity = Field(
        ..., description='Alert severity level. Trace: events.md §5.2.'
    )
    requestId: str | None = Field(
        None,
        description='Request correlation identifier (correlation/idempotency key; no PII/secrets — SEC-3). Trace: events.md §5.2.',
    )


class U6AiIncidentEvents(RootModel[ClassifiedIncident | OpsAlert]):
    root: ClassifiedIncident | OpsAlert = Field(
        ...,
        description='🟡 PROVISIONAL (events.md §5 — refined in U6 FD). RES-11 three incident classes (a=cost explosion / b=hallucination / c=half-baked result) detected, classified, and published. Entirely asynchronous (services.md AiIncidentResponseService, separate worker DQ1). Contains: ClassifiedIncident (via publishIncident) and OpsAlert (via publishAlert). Use $defs root selection to validate a specific shape.',
        title='U6 AI Incident Events',
    )
