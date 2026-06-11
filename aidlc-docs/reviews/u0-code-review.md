# U0 Foundation 코드 리뷰

> **대상**: PR #14 — `backend/` U0 Foundation 구현 (커밋 `f6cf5a7`·`5e82714`)
> **리뷰어**: Claude (작성) — 팀 리뷰어는 본 문서에 코멘트/체크 추가
> **일자**: 2026-06-11
> **기준**: [component-model §2](../design-artifacts/component-model.md) 계약 정합 · [U0 §8](../design-artifacts/units/unit-u0-foundation.md) 변경 정책 · [ADR §12](../design-artifacts/architecture_decision_record.md) 매핑 · NFR 추적 · 머지 기준은 demo-scope("데모가 뜨는가")
> **판정**: ✅ **승인 (demo-scope 머지 가능)** — High 0건 · Medium 3건(후속 라운드 배치) · Low 5건

---

## 1. 검증 요약

| 항목 | 결과 |
|---|---|
| pytest | 14/14 통과 |
| U0 §6 빌드 가능 정의 (`scripts/u0_demo.py`) | 6/6 통과 (mock, 자격 증명 불필요) |
| 포트 시그니처 정합 (§2 비교 — 아래 §3) | 변경 0건 |
| 보안 (NFR-SEC-03) | 평문 키 없음 · `.env` 비추적 · `.env.example`만 커밋 ✅ |

## 2. 발견 사항 (Findings)

### Medium — 다음 라운드에서 보강 (데모 차단 아님)

| ID | 위치 | 내용 | 권고 |
|---|---|---|---|
| M1 | `llm_gateway.py:20-27` | **CostGuard check→record 비원자성** — `check_budget`과 `record_cost` 사이에 동시 Lambda 호출이 끼면 상한을 약간 초과할 수 있다 (R3 잔여 위험). 데모 트래픽에선 실질 영향 미미. | 환경 구축 라운드에서 DynamoDB 조건부 갱신(`ConditionExpression: usd < :cap`)으로 원자화 |
| M2 | `aws.py:235-269` | **Semantic Scholar 429 미구분** — 레이트 리밋(429)도 빈 결과 폴백으로 흡수되어 "인용 없음"과 구분 불가. 코퍼스 빌드에서 실제 429 발생 확인. `User-Agent`·API 키 미설정. | U4 라운드 전 보강: 429 전용 백오프 + `OneHopResult`에 degraded 플래그 또는 Telemetry 표기 + UA/API 키 환경 변수 |
| M3 | `aws.py:91` | `similarity = 1 − distance`는 **코사인 거리 인덱스 가정** — S3 Vectors 인덱스를 euclidean으로 만들면 값이 왜곡된다. | 환경 구축 체크리스트에 "인덱스 distanceMetric=cosine 명시" 추가 (ADR §14 검증 ①과 병합) |

### Low — 기회 있을 때 정리

| ID | 위치 | 내용 |
|---|---|---|
| L1 | `aws.py:273` | `_stable_hash` 데드 코드 (정의만 있고 미사용) — 삭제 |
| L2 | `aws.py:55` | Cohere `input_type="search_query"` 고정 — KB 우회 직접 적재(PutVectors) 경로를 쓰게 되면 `search_document` 분기 필요 |
| L3 | `adapters/__init__.py:56,80` | `persona_mode` `type: ignore` 2건 — `Settings.default_persona`를 `Persona` 리터럴 타입으로 좁혀 제거 가능 |
| L4 | `mock.py` `InMemoryTtlCache` | 스레드 비안전 — Lambda 단일 호출 모델에선 무해. 로컬 멀티스레드 서버로 전용 시 락 필요 (주석으로 명시 권장) |
| L5 | `aws.py` `DynamoCache` | TTL 속성명 `expires_at`은 테이블의 TTL 설정과 일치해야 함 — IaC 작성 시 항목화 |

## 3. 계약 정합 검사 (component-model §2 ↔ `ports.py`)

| 포트 | §2 시그니처 | 구현 | 정합 |
|---|---|---|---|
| EmbeddingPort | `embed(text, lang)` / `search(vec, k, filters?)` | 동일 (snake_case) | ✅ |
| LlmPort | `complete(prompt, persona, budget_tokens)` | 동일 + 게이트웨이 래핑(§2.2 구조 그대로) | ✅ |
| CachePort | `get(key)` / `set(key, value, ttl_s)` | 동일 | ✅ |
| SessionPort | `session()` + 직렬화 보조 | 동일 (`serialize_filters`/`restore_filters`) | ✅ |
| Telemetry | `record({op, latency_ms, tokens_in/out, cache_hit, persona})` | `TelemetryEvent` 필드 1:1 | ✅ |
| Glossary | `lookup(term) -> KoTranslation?` | 동일 | ✅ |
| CitationApi | `oneHop(paper_id)` | `one_hop` (파이썬 네이밍, 의미 동일) | ✅ |
| DTO `PaperHit` | §2.1 8필드 | 동일 | ✅ |

**U0 §8 금지 검사**: 도메인 로직(요약 톤 등) 미포함 ✅ — `aws.py` `_PERSONA_SYSTEM`은 포트 파라미터 전달용 최소 힌트로 한정, 상세 톤은 U2 책임으로 주석 명시.

## 4. 의도적 설계 선택 (리뷰어 참고)

1. **S3 Vectors `query_vectors` 직접 조회** — KB `Retrieve`는 텍스트 질의 전용이라 `search(vec, …)` 시그니처와 부정합. ADR-D2 결과 3에 문서화된 직접 API 경로 채택. 적재·청킹은 KB 관리 유지.
2. **CostGuard 하드 거부** — 사용자 결정(2026-06-11). 상한 도달 시 한국어 안내와 함께 예외.
3. **mock의 시간 주입식 캐시** — "25h 후 miss" 검증을 실제 대기 없이 테스트로 증명하기 위한 구조.
4. **AWS 어댑터 무테스트** — 의도된 보류: 실호출 검증은 환경 구축 라운드(ADR §14 4건)에서. mock 어댑터가 U0 §6 충족을 담당.

## 5. 후속 항목 배치

| 항목 | 배치 라운드 |
|---|---|
| M1 (CostGuard 원자화) · M3 (인덱스 metric) · L5 (TTL 속성) | 환경 구축 라운드 (ADR §14와 병합) |
| M2 (S2 429 처리) | U4 Trace 진입 전 |
| L1~L4 | 다음 backend 커밋에 동봉 |
| 코퍼스 인용수 placeholder 보강 (SS 재시도) | 환경 구축 라운드 또는 운영자 수동 재실행 |
| `data/glossary_seed.json` 50개 초안 검토 | **팀 — 본 PR 리뷰와 함께** |

---

*팀 리뷰어 추가 코멘트는 아래에:*

- [ ] (팀 코멘트 자리)
