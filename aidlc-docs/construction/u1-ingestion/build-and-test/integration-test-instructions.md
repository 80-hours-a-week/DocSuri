# Integration Test Instructions — U1 Corpus

## Local Smoke Scenarios

### FullText to DocModel to Index

```bash
cd ingestion
uv run pytest tests/test_docmodel_build_job.py tests/test_orchestration.py
```

Expected:
- NEW paper builds DocModel before index write.
- CHANGED paper replaces stale chunks.
- OpenSearch candidate generation validation blocks empty candidates.
- Alias cutover remains separate from write path.

### U7 DocModel Read Compatibility

```bash
cd backend/modules/summarization
uv run pytest tests/test_docmodel_input.py tests/test_docmodel_endpoint.py
```

Expected:
- `S3DocModelReader` keeps bare paper id key normalization.
- `InputRefiner.refine_doc_model` projects sections/tables/formulas/captions from DocModel.
- Root `fullText` stays aligned with section projection.

### Frontend Rich View Compatibility

```bash
cd frontend
pnpm exec vitest run test/classifyDocModel.test.ts test/useDocModel.test.ts test/docModelViewer.test.tsx
```

Expected:
- `classifyDocModelResponse` accepts required `fullText`.
- lazy build polling is unchanged.
- `DocModelViewer` still renders section tree, table data, and figure join through assets.

## Env-Gated Production Smoke

Run after deploying migration and worker task:

1. Enable only arXiv source first: `DOCSURI_CORPUS_SOURCES=ARXIV`.
2. Ingest one known OA paper.
3. Confirm S3 full text and `doc-model/{paperId}/v{version}.json` exist.
4. Confirm OpenSearch candidate index document count is greater than zero.
5. Run generation validation.
6. Switch alias only after validation passes.
7. Query U7 `GET /api/papers/{id}/doc-model?version={version}`.

## Cleanup

- Do not delete active alias targets during smoke.
- Roll back by keeping or restoring the previous OpenSearch alias target.
- DLQ reprocess should reuse original pipeline metadata and idempotent upsert paths.
