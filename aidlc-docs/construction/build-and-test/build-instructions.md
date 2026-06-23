# Build Instructions

## Prerequisites
- **Build Tool**: Python 3.12+, `uv` (Astral)
- **Dependencies**: boto3, opensearch-py, pydantic (resolved via `pyproject.toml`)
- **Environment Variables**:
  - `DOCSURI_OPENSEARCH_ENDPOINT`
  - `DOCSURI_BEDROCK_MODEL_ID`
  - `DOCSURI_OPENSEARCH_INDEX_V2`
  - `DOCSURI_BEDROCK_MODEL_ID_V2`

## Build Steps

### 1. Install Dependencies
```bash
uv sync --all-extras
```

### 2. Configure Environment
```bash
export DOCSURI_OPENSEARCH_ENDPOINT=http://localhost:9200
export DOCSURI_BEDROCK_MODEL_ID=cohere.embed-multilingual-v3.0
export DOCSURI_BEDROCK_MODEL_ID_V2=cohere.embed-multilingual-v4.0
```

### 3. Build All Units
Ensure local Docker services (OpenSearch, etc.) are running:
```bash
cd backend && docker-compose up -d
```

### 4. Verify Build Success
- **Expected Output**: Dependencies installed, Docker containers healthy.
- **Build Artifacts**: `uv` virtual environment.
