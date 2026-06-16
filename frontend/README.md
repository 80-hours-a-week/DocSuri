# frontend — U5 Frontend (Track 3)

> **Owner:** @kyjness (Track 3) · **Deploy unit:** ④ frontend (independent) · **Stack:** TS / SSR likely — confirmed in U5 NFR Requirements (§5-D)
> **Status:** 🟡 lane scaffold — implementation deferred to the U5 CONSTRUCTION loop (FD → NFR → Code Generation).

SSR phone-first web UI: search, results, account, library, status. This is an
**independent deploy unit** (④), not part of the backend monolith.

## Responsibility

- **Stories owned:** US-H1 (hero: signup → query → grounded result), US-D7 (empty /
  failure / degraded UX — `StateView`).
- **Contributes UI to:** US-D1/D4 (search & result cards), US-A1/A2 (account),
  US-L1/L2/L3 (library / history).

## Talks to the backend via the gateway

User paths enter through the **U6 gateway** (single entry), which fronts U2/U3/U4
handlers — no direct module calls. The client is a thin `ApiClient` that branches on the
`SearchResponse` union (page / abstain / degraded / validation error) to surface FR-11
terminal states.

## Mock-first (parallel with U2)

U5 develops against **mock U2 responses** built from `shared/dtos/search.schema.json`,
so the frontend does not wait for the real U2 read path. Same `shared/dtos` contract on
both sides → no drift.

## Consumes (from `shared/`, do not fork or edit)

- `shared/dtos/*.schema.json` — search (U2), accounts (U3), library/history (U4) DTOs.
  TS types are generated from these schemas, **deferred to U5** (§5-D); same JSON Schema
  origin as the Python binding, so the two never drift.

## Invariants

- Render only externally-exposed DTO fields (SEC-9) — never display internal scores,
  owner ids, or debug meta.
- `password` is request-input-only; session is a secure cookie, never shown in a body
  (SEC-12 / SEC-3).
- Add stable `data-testid` to interactive elements (automation-friendly UI rule).

## Layout (TBD)

Internal structure (routes, components, ApiClient, mock) is defined and created during
the U5 functional/NFR design loop — not before approval.
