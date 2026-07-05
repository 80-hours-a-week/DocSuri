# User DocModel Backend Code Summary

Status: complete

## Summary

Implemented the backend producer and bounded consumer path for user-uploaded PDF doc-models.

## Application Changes

- Added `backend.modules.user_docmodel` as the shared backend coordinator for:
  - deterministic `userdoc:{uuid}` identity generation,
  - S3 PDF upload with metadata,
  - best-effort `BUILD_USER_DOC_MODEL` enqueue,
  - bounded doc-model polling by `(paperId, version)`.
- Extended the SQS doc-model build adapter with `enqueue_user_build` for the frozen PR0 payload.
- Extended attachment DTOs with `objectKey`, `paperId`, and `recordRef`.
- Added PDF upload endpoints:
  - `POST /api/evidence/attachments`
  - `POST /api/research/attachments`
  - raw `application/pdf` handling on `POST /api/novelty/jobs/{jobId}/manuscript`
- Evidence/research PDF attachments now poll the generated doc-model and pass it through the existing extraction path when ready.
- Novelty PDF manuscripts now enqueue the user doc-model build, persist `paperId`/`recordRef`, and use doc-model `fullText` for similarity checks.
- Novelty evidence adapter no longer fabricates arXiv URLs for `userdoc:` sources.

## Failure Behavior

- Evidence/research continue fail-soft with the frozen notice:
  `[첨부 안내] PDF 본문을 해석하지 못해 첨부 근거는 제외했습니다.`
- Novelty similarity degrades with `manuscript_pdf_parse_unavailable` when the PDF doc-model is unavailable.
- Queue enqueue remains best-effort; missing or delayed doc-models do not fail the user workflow.

## Tests

- Focused backend PR2 suite: 103 passed.
- Broad backend suite: 453 passed, 4 skipped.
- Backend ruff: clean.
- Compile check: clean.
- Diff whitespace check: clean.

## Extension Compliance

- Security: compliant for this slice. PDF upload type/size is checked, S3 metadata is scoped to the owner/upload identity, and user-uploaded sources do not receive invented arXiv URLs.
- Resiliency: compliant for this slice. Enqueue is best-effort and readiness polling is bounded with existing degradation behavior.
- PBT partial mode: N/A for new mandatory properties in this slice; contract-specific regression coverage exercises payload identity and source-reference invariants.
