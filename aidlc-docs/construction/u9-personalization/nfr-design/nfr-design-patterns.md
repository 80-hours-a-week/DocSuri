# U9 Personalization — NFR Design Patterns

**Unit**: U9 Personalization  
**Stage**: CONSTRUCTION -> NFR Design  
**Date**: 2026-06-23

## Fail-Open Personalization

U9 is optional for the caller's core result.

| U9 Result | Caller Behavior |
| --- | --- |
| profile/defaults available | Apply bounded boost/default suggestion. |
| disabled | Use non-personalized default path. |
| no profile | Use non-personalized default path. |
| timeout/error | Treat as `degraded`; continue with non-personalized default path and emit telemetry. |

U2/U7 must not wait long enough for U9 to dominate search or generation latency. Concrete timeout values are finalized in Code Generation defaults.

## Bounded Profile Read

`PersonalizationReadPort` returns a compact `PersonalizationDecision`; it does not expose raw events. Decisions contain only bounded boosts, defaults, and a reason code.

## Read-Through Lazy Aggregation

1. Read current settings.
2. If disabled, return `disabled`.
3. Read profile.
4. If profile is missing/stale, run lightweight aggregation from active events.
5. If aggregation succeeds, store profile and return decision.
6. If aggregation fails, return previous profile if safe, otherwise default `degraded`.

No v1 aggregation worker is required.

## Active-Table Delete With Backup Isolation

Raw-log deletion follows this boundary:

1. Select owner-scoped active rows.
2. Copy or move rows to backup table for recovery/audit safety.
3. Delete rows from active `user_behavior_events`.
4. Emit operational status.

The backup table is excluded from `ProfileAggregator`, `PersonalizationReadPort`, U2 boost, and U7 defaults. This preserves user-visible deletion from personalization even when backup retention exists.

## Metadata Allowlist

`BehaviorEventRecorder` is the single validation gate. It enforces:

- event type allowlist,
- subject shape validation,
- metadata keys per event type,
- no raw paper text,
- no source-nearby quoted text,
- no credentials, tokens, or free-form click payload.

Repositories only accept validated envelopes.

## U6 Observability Without Behavior Payloads

U9 emits operational counters/status only:

- event record failure,
- aggregation failure,
- degraded decision,
- personalization disabled decision count,
- delete/reset count,
- backup copy/delete failure.

Telemetry does not include raw event metadata.

## Test Patterns

| Pattern | Coverage |
| --- | --- |
| Property tests | DTO roundtrip, dedupe, owner isolation, deterministic aggregation, delete/reset effect, fail-open default. |
| Repository integration | Active delete and backup isolation with lightweight DB test. |
| Unit tests | Metadata allowlist and decision reason cases. |

Default CI does not require external services.
