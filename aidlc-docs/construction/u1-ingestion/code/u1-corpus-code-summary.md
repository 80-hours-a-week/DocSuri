# U1 Corpus Code Generation Summary

**Stage**: CONSTRUCTION / U1 Corpus / Code Generation Part 2  
**Branch**: `feature/u1-corpus-code-generation`  
**Date**: 2026-06-26

## 구현 요약

U1 Corpus 구축 파이프라인의 코드 생성 범위를 구현했다. 핵심 변화는 DocModel을 AI 입력용 완성형 산출물로 승격하고, ingestion index 경로가 가능한 경우 DocModel을 먼저 만든 뒤 block-aware chunk를 생성하도록 바꾼 것이다.

## 주요 변경

- `shared/dtos/docmodel.schema.json`
  - `DocModel.fullText`를 required 필드로 추가했다.
  - `fullText`는 reading-order 텍스트 투영본이며 image bytes, base64, presigned URL, object ref를 포함하지 않는다.
  - Python generated DTO와 frontend curated type을 갱신했다.

- `ingestion/src/docsuri_ingestion/docmodel/parser.py`
  - section/block tree에서 paragraph, table, formula, figure caption, list, code 텍스트를 읽기 순서로 투영해 `fullText`를 생성한다.
  - asset internals와 raw binary는 projection에 포함하지 않는다.

- `ingestion/src/docsuri_ingestion/application.py`
  - full-text 저장 후 index write 전에 DocModel을 eager build한다.
  - DocModel source unavailable은 terminal parse failure로 처리해 불완전한 index 노출을 막는다.
  - tombstone 시 DocModel cache invalidation을 수행한다.

- `ingestion/src/docsuri_ingestion/processors.py`
  - `Chunker.chunk_doc_model()`을 추가해 DocModel block 단위 chunk를 생성한다.
  - chunk에 `block_refs`를 보존하고, 기존 OpenSearch DTO schema 변경 없이 `lexicalTerms`에 block id를 포함한다.

- `ingestion/src/docsuri_ingestion/corpus_sources.py`
  - arXiv HTML/PDF 우선순위는 기존 adapter를 재사용한다.
  - Semantic Scholar/OpenAlex는 PDF bytes를 메모리에서만 GROBID로 넘기고, 반환 artifact에는 PDF bytes를 저장하지 않는다.

- `ingestion/src/docsuri_ingestion/domain/canonical.py`
  - canonical key 우선순위는 DOI -> arXiv id -> title/author/year hash다.
  - source별 dedup state 저장 포트를 in-memory/Postgres에 추가했다.

- `ingestion/src/docsuri_ingestion/domain/models.py`, `worker.py`, queue adapters
  - retry/DLQ payload에 `sourceName`, `failureStage`, `canonicalKey`, `paperId`, `version`을 포함한다.

- `ingestion/src/docsuri_ingestion/adapters/aws.py`
  - OpenSearch candidate generation validation과 alias cutover 메서드를 추가했다.
  - validation 실패 시 alias switch를 호출하지 않는 경계를 테스트했다.

- `ingestion/src/docsuri_ingestion/adapters/grobid.py`, `runtime.py`, `settings.py`
  - GROBID HTTP client와 runtime wiring을 추가했다.
  - `DOCSURI_OPENSEARCH_ALIAS`, `DOCSURI_CORPUS_SOURCES`, `DOCSURI_GROBID_URL` 설정을 추가했다.

- `ops/cdk/stacks/ingestion_stack.py`
  - 기존 ingestion worker service를 유지하면서 internal GROBID sidecar와 env만 추가했다.
  - 신규 queue, bucket, DB는 만들지 않았다.

- `backend/modules/summarization`
  - DocModel fixtures/tests에 required `fullText`를 반영했다.
  - 번역 DocModel은 LLM 로직 변경 없이 sections에서 root `fullText`를 재투영해 계약 일관성을 유지한다.

- `frontend`
  - DocModel fixtures/tests에 `fullText`를 추가했다.
  - `DocModelViewer` 렌더 구조는 변경하지 않고, 화면 중복 렌더도 추가하지 않았다.

## 신규 파일

- `ingestion/src/docsuri_ingestion/corpus_sources.py`
- `ingestion/src/docsuri_ingestion/domain/canonical.py`
- `ingestion/src/docsuri_ingestion/adapters/grobid.py`
- `ingestion/migrations/postgres/003_corpus_control_plane.sql`
- `ingestion/tests/test_canonical_dedup.py`
- `ingestion/tests/test_corpus_sources.py`
- `ingestion/tests/test_grobid_adapter.py`
- `aidlc-docs/construction/u1-ingestion/code/u1-corpus-code-summary.md`

## 검증 결과

- `shared/python`: `uv run python tools/generate.py --check` -> passed
- `ingestion`: `uv run pytest` -> 121 passed, 1 skipped
- `ingestion`: `uv run ruff check .` -> passed
- `backend/modules/summarization`: `uv run pytest` -> 116 passed, 3 skipped
- `frontend`: targeted `pnpm exec vitest ...` -> 5 files, 19 tests passed
- `frontend`: `pnpm exec tsc --noEmit` -> passed
- repo root: `git diff --check` -> passed

## 추적성

- FR-6 U1 Corpus 구축: eager DocModel build, chunk/embed/index path, retry/DLQ metadata, OpenSearch generation validation.
- FR-18 DocModel 리치뷰/AI 입력: required `fullText`, multimodal blocks, U7/frontend consumer 정합.
- US-I1 Corpus seed/indexing: fake adapter NEW/CHANGED smoke test로 FullText -> DocModel -> chunk -> embed -> index path 확인.
- US-I2 source별 incremental update: source enum, source adapter boundary, source별 watermark PBT.
- US-I3 retry/DLQ/reprocess: DLQ payload metadata 보존 테스트.
- QT-9 DocModel/index invariant: parser fullText projection, block_refs validation, schema drift check.

## Extension Compliance

- Security Baseline: Compliant. Raw PDF bytes는 transient in-memory 처리이며 DocModel과 candidate artifact에 저장하지 않는다. GROBID는 worker sidecar로만 노출한다. DocModel은 signed URL/image bytes를 포함하지 않고 asset id만 참조한다.
- Resiliency Baseline: Compliant. Source별 watermark, retry/DLQ stage metadata, OpenSearch validation-before-alias-cutover, rollback boundary를 추가했다.
- Property-Based Testing: Compliant for enabled partial rules. Canonical key determinism, arXiv suffix normalization, source watermark monotonicity/independence, existing chunk/index idempotency PBT를 유지·보강했다.
- N/A: Browser CSP/auth/password rules는 U1 ingestion worker code generation 범위가 아니다.
