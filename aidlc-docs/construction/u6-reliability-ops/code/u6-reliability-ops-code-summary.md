# U6 Reliability/Ops Code Summary

**Unit**: U6 Reliability/Ops — data and detection pipeline  
**Date**: 2026-06-16  
**Status**: Code generated for local pipeline, backend middleware seam, and tests

## Implemented Application Code

- `ops/src/docsuri_ops/observability.py`: structured metrics, logs, spans, audit append, and PII/secret redaction.
- `ops/src/docsuri_ops/cost_guard.py`: monthly cost cap state, warning threshold, hard-cap circuit state, and degradation mode.
- `ops/src/docsuri_ops/grounding.py`: `GroundingEnforcementHook` implementation for pass/block/abstain decisions.
- `ops/src/docsuri_ops/detectors.py`: RES-11 cost explosion, hallucination, and partial-result incident candidates.
- `ops/src/docsuri_ops/incidents.py`: detector suite classification and shared `ClassifiedIncident`/`OpsAlert` publication.
- `ops/src/docsuri_ops/dashboard.py`: windowed dashboard aggregation.
- `ops/src/docsuri_ops/health.py`: shallow/deep health checks and U1 `indexStats` seam.
- `ops/src/docsuri_ops/reliability_eval.py`: QT-3 reliability evaluation probe.
- `ops/src/docsuri_ops/worker.py` and `ops/src/docsuri_ops/cli.py`: local worker and command entry points.
- `backend/middleware/`: request context, rate limit, security headers, production error mapping, and middleware wiring seam.

## Tests Added

- Observability redaction, request correlation, audit append-only behavior, and duplicate event idempotency.
- Cost guard threshold transitions, hard-cap degradation, duplicate spend suppression, and spend monotonicity PBT.
- Grounding pass/block/abstain paths and exposed-reference subset PBT.
- Partial-result detection, explicit degraded/abstain non-incidents, and QT-3 evaluation.
- RES-11 incident class mapping, shared event publication, duplicate alert suppression, and dashboard aggregation.
- Health stale dependency detection and backend middleware security/error/rate-limit behavior.

## Contract Notes

- Shared events are consumed from `docsuri_shared.events`; U6 maps internal incident classes to shared enum values `a`, `b`, and `c`.
- Shared ports are consumed without modifying `shared/`; U6 implements the runtime behavior locally.
- App-shell integration is intentionally left as a wiring step through `backend.middleware.configure_u6_middleware`.

## Security and Resiliency Notes

- Logs and audit events redact sensitive keys and email-like values.
- Incident and alert payloads expose request correlation, severity, and class only.
- Duplicate event ids and duplicate incident keys are suppressed in local stores.
- Middleware maps unhandled production errors to generic responses and adds security headers.
- Deep health marks stale or mismatched index stats as degraded and dependency failures as unhealthy.
