# Unit Test Execution

## Scope

Unit tests cover U1 domain rules, processing components, local adapters, and orchestration
boundaries implemented during Code Generation.

## Run Unit Tests

### 1. Execute All U1 Tests

PowerShell from the repository root:

```powershell
$env:PYTHONPATH="ingestion/src;shared/python/src"
python -m pytest ingestion/tests
```

With `uv`:

```powershell
cd ingestion
uv run pytest
```

### 2. Expected Results

- Total tests: 21
- Expected result: 21 passed, 0 failures
- Property-based tests: included in `ingestion/tests/test_properties.py`
- Report location: terminal output unless CI config writes JUnit XML

### 3. Test Groups

- Domain unit tests: `ingestion/tests/test_domain_units.py`
- Property-based tests: `ingestion/tests/test_properties.py`
- Orchestration and fault-injection tests: `ingestion/tests/test_orchestration.py`

### 4. Fix Failing Tests

If tests fail:

1. Inspect the first failing test and traceback.
2. Fix the smallest affected code path.
3. Re-run the same test module.
4. Re-run `python -m pytest ingestion/tests`.
5. Re-run `python -m ruff check ingestion`.

## Current Known Result

Last local execution during Code Generation:

```text
21 passed
```
