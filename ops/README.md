# DocSuri Ops

U6 Reliability/Ops implements the data and detection pipeline for observability, cost
guarding, grounding incidents, partial-result incidents, health checks, and reliability
evaluation.

## Local Development

Create an isolated virtual environment before installing dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ..\shared\python -e . hypothesis pytest ruff fastapi httpx
.\.venv\Scripts\python -m pytest tests ..\backend\tests\test_u6_middleware.py
.\.venv\Scripts\python -m ruff check . ..\backend\middleware
```

No dependencies should be installed into the global or user Python environment.

## CLI

```powershell
.\.venv\Scripts\python -m docsuri_ops.cli run-detectors
.\.venv\Scripts\python -m docsuri_ops.cli run-grounding-eval
.\.venv\Scripts\python -m docsuri_ops.cli run-reliability-eval
.\.venv\Scripts\python -m docsuri_ops.cli dashboard-summary
```

## Boundaries

- Application code lives under `ops/` and `backend/middleware/`.
- Shared contracts are consumed from `docsuri_shared`; they are not forked here.
- Cloud EventBridge/SQS/SNS/PagerDuty/CloudWatch integrations are adapter seams for later
  infrastructure work.
