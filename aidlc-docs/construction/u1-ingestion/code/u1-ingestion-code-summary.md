# u1-ingestion-code-summary.md — U1 Ingestion 코드 생성 요약

**단계**: CONSTRUCTION → Code Generation Part 2  
**유닛**: U1 Ingestion  
**상태**: 코드 생성 및 검증 완료

---

## 1. 생성 위치

### 애플리케이션 코드
- `ingestion/pyproject.toml`
- `ingestion/README.md`
- `ingestion/Dockerfile`
- `ingestion/migrations/postgres/001_control_plane.sql`
- `ingestion/src/docsuri_ingestion/`

### 테스트
- `ingestion/tests/conftest.py`
- `ingestion/tests/test_domain_units.py`
- `ingestion/tests/strategies.py`
- `ingestion/tests/test_properties.py`
- `ingestion/tests/test_orchestration.py`

---

## 2. 구현 모듈

| 모듈 | 역할 |
|---|---|
| `domain/ids.py` | arXiv ID 정규화, 버전 파싱, `paperId+version` fingerprint |
| `domain/models.py` | U1 값 타입과 배치 모델 |
| `ports.py` | U1 내부 포트 Protocol |
| `settings.py` | 환경 변수 기반 설정과 safe logging |
| `processors.py` | OA 검증, withdrawal 탐지, 청킹, 디덥, IndexRecord 조립 |
| `resilience.py` | timeout, retry, circuit breaker, token bucket, failure signal |
| `application.py` | `ingest_one`, rebuild, schedule tick, new-arXiv event orchestration |
| `adapters/arxiv.py` | OAI-PMH, Atom API, full-text fetch adapter |
| `adapters/aws.py` | S3, Bedrock Cohere, OpenSearch, SQS adapter |
| `adapters/postgres.py` | Postgres control-plane store |
| `adapters/local.py` | fake/in-memory adapter and fault injection helpers |
| `cli.py`, `worker.py` | manual CLI and SQS polling worker |

---

## 3. 스토리 매핑

| 스토리 | 코드 매핑 |
|---|---|
| US-I1 arXiv 인제스천 및 인덱싱 | `ArxivHttpSource`, `FetchParseProcessor`, `Chunker`, `BedrockCohereEmbeddingPort`, `OpenSearchVectorIndex`, `IngestionPipelineService` |
| US-I2 최신성 스케줄 갱신 | `RefreshOrchestrationService.on_schedule_tick`, `Watermark`, `advance_watermark`, `SqsQueue` |
| US-I3 복원력 인제스천 | `RetryPolicy`, `CircuitBreaker`, `TokenBucket`, `IngestFailureHandler`, DLQ adapter, fault-injection tests |
| US-H1/US-D2/US-D5 backing | `docsuri_shared.vector_spec.IndexRecord`, `chunk_id`, card fields, lexical/vector fields, arXiv grounding URL |

---

## 4. 테스트 매핑

| 요구 | 테스트 |
|---|---|
| arXiv ID/version | `test_arxiv_id_normalization_and_version_parsing` |
| OA 라이선스 | `test_strict_oa_license_validation_rejects_missing_or_arxiv_only_license` |
| 청킹 결정성 | `test_chunker_is_deterministic_and_contiguous`, PBT P2 |
| 디덥/멱등 | `test_dedup_guard_decisions_and_mark_ingested`, PBT P3 |
| watermark max-clamp | `test_watermark_max_clamp`, PBT P6 |
| tombstone highest-vN-wins | `test_tombstone_strictly_newer_version_wins` |
| 논문 단위 원자성 | `test_bulk_partial_failure_does_not_mark_ingested` |
| retry/DLQ | `test_bedrock_retry_recovers_after_429_like_failure`, `test_arxiv_404_permanent_failure_goes_to_dlq` |
| rebuild 상호배제 | `test_rebuild_lock_defers_incremental_and_event_paths` |

---

## 5. 규칙 준수 요약

### Security Baseline
- 시크릿과 DSN/URL은 `safe_log_dict` 및 `sanitize_log_entry`에서 redaction 처리.
- 외부 입력은 arXiv ID, metadata, queue payload, IndexRecord 조립 단계에서 validation.
- S3 full-text adapter는 public 접근을 전제하지 않으며 SSE 기본값을 설정.
- 구체 IAM/KMS/network policy JSON은 Infrastructure Design 소관으로 남김.

### Resiliency Baseline
- arXiv, S3, Bedrock, OpenSearch, SQS, Postgres 의존성을 포트와 adapter로 분리.
- retry, timeout, circuit breaker, token bucket, DLQ, failure signal을 구현.
- OpenSearch `_bulk` per-item 실패를 검사하고 실패 시 `mark_ingested`를 호출하지 않음.
- `indexStats`는 TTL cache 경계를 포함.

### Property-Based Testing
- `tests/strategies.py`에 generator를 중앙화.
- P2, P3, P4, P5, P6 속성 테스트를 Hypothesis로 작성.
- `derandomize=True`와 제한된 `max_examples`로 재현 가능한 실행을 설정.

---

## 6. 검증 결과

- `PYTHONPATH="ingestion/src;shared/python/src" python -m pytest ingestion/tests`
  - 결과: 21 passed
- `python -m ruff check ingestion`
  - 결과: All checks passed
- `uv lock`
  - 결과: `ingestion/uv.lock` 생성
