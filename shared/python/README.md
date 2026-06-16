# docsuri-shared (Python binding)

Python binding for the DocSuri shared contracts. **The source of truth is the
language-neutral JSON Schema in [`../`](..)** (`shared/{vector-spec,dtos,events}`);
this package exposes typed **pydantic v2** models generated from those schemas, plus
the hand-authored pieces a schema cannot express (ports `Protocol`s, the `chunk_id`
helper, embedding constants). §5-A decided backend/ingestion/ops are all Python, so this
is the single shared binding all Python tracks import — not a per-track copy.

## Install / use

```bash
uv sync                 # create .venv and install (pydantic + dev tools)
```

```python
from docsuri_shared import dtos, events, ports, vector_spec
from docsuri_shared.ids import chunk_id

req = dtos.SearchRequest.model_validate({"query": "diffusion models"})
doc_id = chunk_id("2106.01234", 7)            # -> "2106.01234#7"
assert vector_spec.DIMENSIONS == 1024         # Cohere Embed Multilingual v3, cosine

# U6 implements the ports; U2/U1 depend on the abstractions (structural Protocols).
def search(hook: ports.GroundingEnforcementHook, cost: ports.CostGuardCircuitBreaker): ...
```

## What's generated vs authored

| Path | Origin | Notes |
|---|---|---|
| `src/docsuri_shared/_generated/` | **GENERATED** from `../{vector-spec,dtos,events}/*.schema.json` | Committed + drift-checked. **Never hand-edit** — change the schema and regenerate. |
| `dtos.py`, `events.py` | authored | Clean re-exports of the generated models under canonical names. |
| `vector_spec.py` | authored | `IndexRecord` (generated) + embedding constants mirroring `../vector-spec/vector-spec.yaml` (parity-tested). |
| `ports.py` | authored | `typing.Protocol` stubs from `../ports/README.md` (behavior, not a data shape). |
| `ids.py` | authored | Deterministic `chunk_id(paper_id, ordinal)` = `f"{paper_id}#{ordinal}"`. |

## Regenerate after a schema change

```bash
uv run python tools/generate.py            # rewrite _generated/ from the schemas
uv run python tools/generate.py --check    # CI: fail if _generated/ drifted (exit 1)
```

The generator feeds only `*.schema.json` to `datamodel-code-generator` (the
`vector-spec.yaml` config is mirrored to constants instead). Output is deterministic
(`--disable-timestamp`) so `--check` is a clean file diff.

## Test

```bash
uv run pytest                              # 63 tests
uv run ruff check . && uv run ruff format --check src tools tests
```

Coverage: JSON Schema 2020-12 validity + cross-file `$ref` resolution · pydantic
round-trip + union dispatch + `extra='forbid'` · `vector-spec.yaml` ↔ constants parity ·
`chunk_id` property-based tests (Hypothesis: determinism, injectivity, prefix scan) ·
SEC-9/SEC-8/SEC-12 invariants (no internal fields on cards, no owner `userId` in U4
bodies, no `password` in responses).

> Contract changes go through a `shared/` PR + cross-track sign-off (see `../README.md`).
> The schemas are the SSOT; this package follows them.
