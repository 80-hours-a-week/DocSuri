# Unit Test Execution

## Run Unit Tests

### 1. Execute All Unit Tests
```bash
uv run pytest
```

### 2. Review Test Results
- **Expected**: All tests pass. Existing Ingestion tests should verify the updated dual-write logic (if mocked appropriately).
- **Test Coverage**: Focus on dual-write fail-open logic and alias setting.

### 3. Fix Failing Tests
If tests fail:
1. Review pytest output.
2. Verify that mock Bedrock endpoints accept the v4 model ID.
3. Rerun tests until all pass.
