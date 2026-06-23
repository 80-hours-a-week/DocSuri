# Integration Test Instructions

## Purpose
Test interactions between U1 Ingestion, U2 Discovery, and the Ops Migration scripts to ensure data consistency and zero-downtime cutover.

## Test Scenarios

### Scenario 1: Dual-Write Ingestion Integration
- **Description**: Verify that the U1 ingestion worker writes to both `v1` and `v2` indices.
- **Setup**: Local OpenSearch running.
- **Test Steps**: Send an ingestion job message to SQS/local queue.
- **Expected Results**: Document appears in both indices.

### Scenario 2: Ops Scripts and Alias Cutover
- **Description**: Verify that the backfill script successfully embeds with v4 and writes to v2, and the cutover script successfully swaps the alias.
- **Setup**: OpenSearch and Bedrock credentials available.
- **Test Steps**:
  1. `uv run python -m discovery.scripts.seed_local_opensearch`
  2. `uv run python -m ops.migrations.v4_migration.provision_v2_index`
  3. `uv run python -m ops.migrations.v4_migration.backfill_v4`
  4. `uv run python -m ops.migrations.v4_migration.cutover_alias`
- **Expected Results**: Search queries against `docsuri-corpus` are routed to `docsuri-corpus-v2`.

## Run Integration Tests
```bash
uv run pytest tests/integration
```
