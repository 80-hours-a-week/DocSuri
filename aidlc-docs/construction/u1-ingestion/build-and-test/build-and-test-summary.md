# Build and Test Summary — U1 Corpus

**Stage**: CONSTRUCTION / Build and Test
**Unit**: U1 Ingestion / Corpus
**Date**: 2026-06-26
**Branch**: `feature/u1-corpus-code-generation`

## Build Status

- **Shared DTO drift check**: Pass.
- **Ingestion package**: Pass.
- **Summarization consumer**: Pass.
- **Frontend consumer**: Pass.
- **Whitespace check**: Pass.

## Test Execution Summary

### Unit Tests

- `shared/python`: `uv run python tools/generate.py --check` -> passed.
- `ingestion`: `uv run pytest` -> 121 passed, 1 skipped.
- `ingestion`: `uv run ruff check .` -> passed.
- `backend/modules/summarization`: `uv run pytest` -> 116 passed, 3 skipped.
- `frontend`: targeted `pnpm exec vitest ...` -> 5 files, 19 tests passed.
- `frontend`: `pnpm exec tsc --noEmit` -> passed.
- repo root: `git diff --check` -> passed.

### Integration Smoke

- NEW/CHANGED fake ingestion path covers FullText -> DocModel -> chunk -> embed -> index.
- Retry/DLQ path preserves source and stage metadata.
- U7 DocModel endpoint and input refiner consume required `fullText`.
- Frontend classify/useDocModel/viewer targeted tests consume required `fullText` without duplicate rendering.

### Performance

- Dedicated load harness: not added.
- Performance validation path: bounded backfill with worker telemetry, OpenSearch generation validation, and cost/throttle monitoring.

### Security And Resiliency

- Raw PDF bytes remain transient for GROBID extraction.
- GROBID is wired as an internal sidecar, not a public endpoint.
- OpenSearch alias cutover is separated from candidate writes and blocked by validation failure.
- DLQ/retry payloads preserve enough metadata for source-aware reprocess.

## Overall Status

- **Build**: Pass.
- **Tests**: Pass.
- **Ready for Operations placeholder**: Yes, pending review approval.

## Generated Instruction Files

- `build-instructions.md`
- `unit-test-instructions.md`
- `integration-test-instructions.md`
- `performance-test-instructions.md`
- `build-and-test-summary.md`
