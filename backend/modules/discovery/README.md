# backend/modules/discovery — U2 Discovery (Track 3)

> **Owner:** @kyjness (Track 3) · **Deploy unit:** ① backend API (modular monolith) · **Runtime:** Python (§5-A)
> **Status:** 🟡 lane scaffold — implementation deferred to the U2 CONSTRUCTION loop (FD → NFR → Code Generation).

This is the **U2 Discovery** module of the backend modular monolith (deploy unit ①).
It is **not a standalone app**: it is mounted into the shared app-shell owned by
@ELSAPHABA (`backend/` bootstrap·router·DI). Touch only this directory; app-shell /
middleware wiring goes through the coordination-zone owner.

## Responsibility

The synchronous search **read path**: query intake → query understanding → hybrid
search → ranking → grounding adapting → result assembly. See
`aidlc-docs/inception/application-design/` and the U2 functional design (authored
during this track's loop).

- **Stories owned:** US-D1 (NL query), US-D2 (semantic search), US-D3 (top-N ranking),
  US-D4 (phone card assembly), US-D6 (abstain).
- **Contributes to:** US-D5/D7 (grounding/state UX), US-R1/R2 (grounding/degradation),
  US-H1 (hero backing).
- **Produces:** `SearchExecutedEvent` (→ U4 history).

## Mock-first

U2 ships a **mock** first so Track 3's U5 frontend can develop in parallel before the
real search engine exists. The mock returns responses shaped by the **frozen
`SearchResponse` contract** in `shared/dtos/search.schema.json` (union: result page /
abstain / degraded / validation error). Swap the mock for the real read path during the
U2 code-generation loop without changing the contract.

## Consumes (from `shared/`, do not fork or edit)

| Contract | Role | Notes |
|---|---|---|
| `shared/dtos/search.schema.json` | **producer** (U5 consumes) | `SearchRequest` / `SearchResponse`; card fields are FROZEN-adjacent. |
| `shared/vector-spec/` | **reader** | Query embedding shares U1 writer's space (Cohere 1024 · cosine). 🔒 FROZEN. |
| `shared/events/search-executed.schema.json` | **producer** | → U4 history. 🔒 FROZEN. |
| `shared/ports/` (Grounding · Cost hooks) | **dependant** | Depends on the interface; U6 implements (breaks U2↔U6 cycle). |

## Invariants

- **SEC-9:** DTOs expose no internal fields (owner `userId`, raw scores, debug,
  `vector`/`chunkId`/`section`). Cards carry only the 7 projected fields.
- **SEC-5 / FR-1:** validate `query` (non-empty · ≤500 chars · sanitized) before processing.
- Grounding (FR-5): every exposed card maps to a real IndexRecord (real arXiv id/link) —
  zero fabrication; enforced at the response edge by U6's `GroundingEnforcementHook`.

## Layout

```
src/discovery/
├── domain/         # framework-agnostic core: models, validator, expander, retriever
│   │               #   (RRF + PaperId dedup), ranker (baseline top-20), grounding_adapter
│   │               #   (INV-1: shape/map only), assembler (7-field cards, SEC-9)
├── ports/          # U2-owned ports: EmbeddingAdapter/VectorStoreAdapter/LexicalIndexAdapter
│                   #   + EventPublisher; dependency-isolation exceptions
├── cache/          # read-through embedding cache (TTL) — NFR-P1/C1
├── service/        # SearchOrchestrationService — pipeline split at the grounding seam
│                   #   (plan_and_retrieve / finalize) so the domain never calls enforce
├── api/            # gateway_seam.run_search (the single enforce invocation, INV-1) +
│                   #   router.py (thin FastAPI binding — `api` extra, app-shell-pending)
└── mocks/          # deterministic fixtures (KO↔EN cross-lingual + QT-2), mock adapters,
                    #   U6 port stubs, build_mock_orchestrator()
tests/              # PBT-02/03/07/09 + terminal states + degrade matrix + RES-12 fault injection
```

## Run / test (mock-first, standalone)

```sh
cd backend/modules/discovery
uv run pytest                 # PBT + unit + fault-injection (no network)
uv run ruff check src tests   # lint
uv run --extra api uvicorn --factory discovery.api.router:... # (router is mounted by app-shell)
```

`uv` resolves `docsuri-shared` from the in-repo path dep (`../../../shared/python`). The
backend web framework (FastAPI) and integration packaging are app-shell decisions pending
@ELSAPHABA sign-off (CG-1); the domain core runs without FastAPI. Real OpenSearch/Bedrock
adapters replace the mocks after Infra/U1 corpus without changing the contract (MR-4).
