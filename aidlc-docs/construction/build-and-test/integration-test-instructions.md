# Integration Test Instructions

## Purpose

Validate U1 interactions across generated module boundaries and, when infrastructure is
available, across AWS dependencies.

## Current Integration Status

Generated and executable now:

- U1 pipeline with fake arXiv, fake embedding, in-memory control plane, in-memory vector index
- OpenSearch partial bulk failure boundary through `InMemoryVectorIndex(fail_bulk=True)`
- DLQ boundary for permanent failures
- Rebuild lock deferral for schedule and new-arXiv event paths

Deferred until Infrastructure Design or other units exist:

- Real S3, Bedrock, OpenSearch, SQS, and Postgres integration tests
- U1 to U6 ObservabilityHub integration
- U1-produced index read by U2 HybridRetriever

## Test Scenarios

### Scenario 1: U1 Pipeline Internal Integration

- Description: metadata fetch, full-text parse, OA validation, chunking, embedding, index write,
  `mark_ingested`, and watermark advancement.
- Setup: fake adapters from `ingestion/src/docsuri_ingestion/adapters/local.py`.
- Command:

```powershell
$env:PYTHONPATH="ingestion/src;shared/python/src"
python -m pytest ingestion/tests/test_orchestration.py::test_successful_ingestion_end_to_end_with_fake_adapters
```

- Expected result: record exists in in-memory index, dedup state has fingerprint, watermark advances.

### Scenario 2: Duplicate Event Redelivery

- Description: at-least-once event redelivery short-circuits after dedup detection.
- Command:

```powershell
$env:PYTHONPATH="ingestion/src;shared/python/src"
python -m pytest ingestion/tests/test_orchestration.py::test_duplicate_redelivery_short_circuits
```

- Expected result: second ingest returns `DUPLICATE`, bulk upsert count remains one.

### Scenario 3: OpenSearch Bulk Partial Failure Boundary

- Description: app-level verify-all-then-commit prevents `mark_ingested` after partial bulk failure.
- Command:

```powershell
$env:PYTHONPATH="ingestion/src;shared/python/src"
python -m pytest ingestion/tests/test_orchestration.py::test_bulk_partial_failure_does_not_mark_ingested
```

- Expected result: raised retriable error, dedup fingerprint remains unset.

### Scenario 4: Rebuild Lock Exclusion

- Description: schedule and event paths defer while rebuild lock is active.
- Command:

```powershell
$env:PYTHONPATH="ingestion/src;shared/python/src"
python -m pytest ingestion/tests/test_orchestration.py::test_rebuild_lock_defers_incremental_and_event_paths
```

- Expected result: no incremental/event jobs enqueued while lock is active.

## AWS Integration Environment

Run only after Infrastructure Design defines concrete endpoints, IAM, KMS, and network access:

1. Provision isolated test resources for S3, Bedrock, OpenSearch, SQS, DLQ, and Postgres.
2. Apply `ingestion/migrations/postgres/001_control_plane.sql`.
3. Export production-like `DOCSURI_*` variables.
4. Run a controlled single-paper ingest.

Command shape:

```powershell
$env:DOCSURI_ENV="integration"
python -m docsuri_ingestion.cli ingest-one --arxiv-ref <known-oa-paper-vN>
```

Cleanup:

- Delete test S3 object prefix.
- Delete test OpenSearch records by `paperId`.
- Purge test SQS messages.
- Reset control-plane rows for the test `paperId`.
