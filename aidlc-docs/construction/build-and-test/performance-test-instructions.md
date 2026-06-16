# Performance Test Instructions

## Purpose

Validate that U1 ingestion respects cost, quota, and resiliency constraints while
processing large arXiv slices.

## Applicable Requirements

- Corpus slice: `cs.LG`, `cs.AI`, `cs.CL`, `cs.CV`, `stat.ML` over five years.
- Writer role: Cohere Embed Multilingual v3 `search_document`, 1024 dimensions.
- Rate control: arXiv token bucket.
- Retry policy: maximum five attempts, base one second, exponential factor two, jitter.
- Atomicity: no `mark_ingested` unless all chunks are written and verified.

## Local Performance Checks

Local checks use fake adapters and validate CPU-bound processing behavior only.

```powershell
$env:PYTHONPATH="ingestion/src;shared/python/src"
python -m pytest ingestion/tests/test_properties.py
```

Expected result:

- PBT suite passes with deterministic chunking and idempotent upsert properties.

## AWS Load Test Setup

Run only after Infrastructure Design defines quotas and isolated test resources.

Recommended initial parameters:

- Test duration: 30 minutes
- Seed size: 100 known OA papers
- Concurrency: one worker process initially
- Ramp-up: increase worker count only after arXiv and Bedrock quotas are confirmed
- Error budget: zero silent partial indexing; retriable failures may enter retry/DLQ paths

## Load Test Execution

1. Prepare a known OA arXiv ID list.
2. Enqueue U1 `EVENT` jobs into the test SQS queue.
3. Run one or more worker containers.
4. Observe:
   - ingestion throughput
   - retry count by stage
   - DLQ count
   - OpenSearch document count
   - Bedrock throttling
   - arXiv request rate

Command shape:

```powershell
docker run --rm --env-file .env.integration docsuri-ingestion:<git-sha>
```

## Pass Criteria

- No partial paper commit.
- Duplicate replay does not increase OpenSearch record count.
- Bedrock 429/timeout recovers within retry policy or reaches DLQ with failure signal.
- `indexStats` calls use cached count behavior, not per-request expensive count loops.
- arXiv request rate remains within configured token bucket policy.

## Optimization Loop

If performance is below target:

1. Identify bottleneck by dependency stage.
2. Tune chunk bounds and worker concurrency within cost budget.
3. Confirm Bedrock and OpenSearch quotas before raising concurrency.
4. Repeat load test and compare metrics.
