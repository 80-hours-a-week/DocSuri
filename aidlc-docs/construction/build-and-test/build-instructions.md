# Build Instructions

## Scope

This build instruction set covers the generated U1 Ingestion worker and its dependency on
`shared/python`. U2-U6 application code is not generated yet, so repository-wide build
commands currently target U1 plus shared contracts only.

## Prerequisites

- Build tool: Python 3.11 or newer, `uv` 0.11 or newer
- Runtime package manager: `pip` or `uv`
- Development tools: `pytest`, `hypothesis`, `ruff`
- Local packages:
  - `shared/python`
  - `ingestion`
- System requirements:
  - Windows PowerShell or POSIX shell
  - Network access for first dependency sync
  - Docker only when building the container image

## Environment Variables

Local fake-adapter validation does not require AWS credentials. Production runtime requires:

- `DOCSURI_ENV`
- `DOCSURI_AWS_REGION`
- `DOCSURI_S3_BUCKET`
- `DOCSURI_BEDROCK_MODEL_ID`
- `DOCSURI_OPENSEARCH_ENDPOINT`
- `DOCSURI_OPENSEARCH_INDEX`
- `DOCSURI_CONTROL_PLANE_DSN`
- `DOCSURI_SQS_QUEUE_URL`
- `DOCSURI_SQS_DLQ_URL`

## Build Steps

### 1. Install Dependencies

PowerShell from the repository root:

```powershell
python -m pip install uv
cd ingestion
uv sync --all-groups
```

Fallback without `uv`:

```powershell
python -m pip install -e shared/python
python -m pip install -e ingestion
python -m pip install pytest hypothesis ruff
```

### 2. Configure Local Environment

PowerShell from the repository root:

```powershell
$env:PYTHONPATH="ingestion/src;shared/python/src"
```

### 3. Build U1 Package

```powershell
cd ingestion
uv build
```

Fallback:

```powershell
python -m pip install build
python -m build ingestion
```

### 4. Build Container Image

Run from the repository root because the Dockerfile copies both `shared/python` and
`ingestion`:

```powershell
docker build -f ingestion/Dockerfile -t docsuri-ingestion:<git-sha> .
```

Do not publish `latest` tags. Use immutable git SHA or release tags.

### 5. Verify Build Success

Expected artifacts:

- Python package artifacts under `ingestion/dist/`
- Container image tagged `docsuri-ingestion:<git-sha>`
- Lockfile at `ingestion/uv.lock`

Acceptable warnings:

- Local editable path warnings for `docsuri-shared` during development.
- Missing AWS environment variables only when running local fake-adapter tests.

## Troubleshooting

### Dependency Sync Fails

Cause: `uv` is missing or cannot resolve the local path dependency.

Solution:

1. Run commands from the repository root or `ingestion/` as shown above.
2. Confirm `shared/python/pyproject.toml` exists.
3. Re-run `uv lock` inside `ingestion/`.

### Runtime Fails with Missing Settings

Cause: production mode is fail-closed when required `DOCSURI_*` settings are absent.

Solution:

1. Use `--local` for fake-adapter checks.
2. Provide all production settings before running `python -m docsuri_ingestion.worker`.

### Docker Build Fails

Cause: build context is not the repository root.

Solution:

1. Run `docker build -f ingestion/Dockerfile -t docsuri-ingestion:<git-sha> .` from repo root.
2. Confirm both `shared/python` and `ingestion` are present in the build context.
