# Performance Test Instructions

## Purpose
Validate the backfill migration script's throughput and rate-limiting to ensure it does not overwhelm Bedrock or arXiv APIs.

## Performance Requirements
- **Throughput**: Process historical arXiv records efficiently.
- **Error Rate**: < 1% 429 Too Many Requests errors. Retries must back off exponentially.

## Setup Performance Test Environment

### 1. Configure Test Parameters
- Target a specific date range or category in `CategoryFilter` for a small batch test.

## Run Performance Tests

### 1. Execute Backfill Script locally
```bash
uv run python -m ops.migrations.v4_migration.backfill_v4
```

### 2. Analyze Performance Results
- **Bottlenecks**: Monitor Bedrock `InvokeModel` latency.
- **Results Location**: Standard output logs. If rate limits are hit, consider tuning down the chunk parallelization.
