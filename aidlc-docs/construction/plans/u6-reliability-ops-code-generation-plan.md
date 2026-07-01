# u6-reliability-ops-code-generation-plan.md — U6 Reliability/Ops 코드 생성 계획서

**단계**: CONSTRUCTION → Code Generation (Part 1 - Planning)  
**유닛**: U6 Reliability/Ops — 데이터 및 탐지 파이프라인 우선  
**일자**: 2026-06-16  
**근거**: `code-generation.md`, Security Baseline, Resiliency Baseline, `overconfidence-prevention.md`, `aidlc-docs/inception/`, `aidlc-docs/construction/`, 현재 코드 상태  
**상태**: 계획 수립 완료 — 승인 전 코드 생성 금지  
**문서 언어**: 한국어  

---

## 1. 계획 범위

이번 계획은 U6 전체 중 **데이터 및 탐지 파이프라인**을 먼저 구현하기 위한 코드 생성 계획이다.

### 포함
- `ops/` 신규 패키지 생성
- U6 이벤트 소비·정규화·멱등 처리
- 비용 폭발 탐지
- 할루시네이션 탐지
- 반쪽짜리 결과 탐지
- 인시던트 분류 및 `ClassifiedIncident`/`OpsAlert` 발행
- 운영 대시보드용 인메모리/로컬 저장소와 조회 서비스
- `ObservabilityHub` 구현
- `CostGuardCircuitBreaker` 구현
- `GroundingEnforcementHook` 구현의 최소 런타임 게이트
- `ReliabilityEvalProbe` 구현
- `HealthCheckService`의 U1 `indexStats` 소비 seam
- U6 데이터/탐지 파이프라인 단위 테스트, PBT, 폴트 인젝션 테스트

### 명시적으로 후속 단계로 남김
- 실제 AWS EventBridge/SQS/SNS/PagerDuty/CloudWatch 연동
- 실제 운영 대시보드 UI
- 구체 IAM/KMS/VPC 정책 및 IaC
- U5 프런트엔드 연동
- U2 real OpenSearch/Bedrock 어댑터 전환

---

## 2. 현재 코드 상태 요약

- `ops/` 디렉터리 없음.
- `backend/middleware/` 디렉터리 없음.
- `backend/` app-shell은 FastAPI 기반이며 accounts/discovery를 선택적으로 마운트한다.
- `shared/python/src/docsuri_shared/ports.py`에 U6가 구현해야 할 `GroundingEnforcementHook`, `CostGuardCircuitBreaker`, `ObservabilityHub` Protocol이 있다.
- `shared/python/src/docsuri_shared/events.py`에 `ClassifiedIncident`, `OpsAlert`, `IngestionFailureSignal`, `AccountCreated`, `SignupAbuseSignal`, `AuthFailureSignal`, `SearchExecutedEvent`가 있다.
- U1은 `indexStats`를 제공하고 U6 deep health check가 이를 소비해야 한다.
- U2는 mock-first로 U6 포트 스텁을 사용하고 있으며, U6 실구현으로 교체 가능해야 한다.
- U3는 account/auth 이벤트 신호를 생산할 수 있는 구조로 구현되어 있다.

---

## 3. 구현 대상 스토리와 요구사항

| 스토리 | U6 책임 |
|---|---|
| US-D5 | `GroundingEnforcementHook` 단일 권위로 근거화 위반 차단/기권 |
| US-R1 | QT-1 평가셋 실행, 할루시네이션 인시던트 탐지·경보 |
| US-R2 | 저하·불완전 결과 탐지, 반쪽짜리 결과 인시던트 발행 |
| US-R3 | 비용 상한 서킷 브레이커, 비용 폭발 탐지·경보 |
| US-R4 | 관측성 수집, 인시던트 경보, 대시보드 데이터 제공 |
| US-R5 | 얕은/깊은 헬스 체크 |
| US-I2/I3 기여 | 인제스천 실패·갱신 건강도 신호 소비 |
| US-A1/A2 기여 | 가입 남용·인증 실패 신호 소비 |

핵심 요구사항: FR-5, FR-11, NFR-C1, NFR-R1/R2, NFR-O1, RES-5/6/7/9/11, SEC-3/8/9/11/14/15.

---

## 4. 코드 위치

### 애플리케이션 코드
- `ops/pyproject.toml`
- `ops/README.md`
- `ops/src/docsuri_ops/`
- `ops/tests/`
- `backend/middleware/`

### 문서
- `aidlc-docs/construction/u6-reliability-ops/code/u6-reliability-ops-code-summary.md`

### 생성하지 않는 위치
- `aidlc-docs/` 내부 애플리케이션 코드
- `shared/` 계약 변경
- `backend/modules/discovery/` 내부 U2 재구현
- `backend/modules/accounts/` 내부 U3 재구현
- `ingestion/` 내부 U1 재구현

---

## 5. 설계 불변식

1. **근거화 단일 권위**: U6만 `GroundingEnforcementHook.enforce`를 구현한다. U2는 enforce를 재구현하지 않는다.
2. **비용 단일 권위**: U6만 비용 누적·임계·서킷 전이를 판단한다. U2는 `get_budget_state()` 조회 결과만 사용한다.
3. **관측성 단일 수집**: U6 `ObservabilityHub`가 로그·메트릭·트레이스·감사 이벤트를 정규화한다.
4. **이벤트 at-least-once 안전성**: 모든 소비자는 `eventId`, `requestId`, 또는 안정 fingerprint 기반 멱등 처리를 한다.
5. **PII/시크릿 금지**: 로그·이벤트·인시던트·대시보드 데이터는 PII와 시크릿을 포함하지 않는다.
6. **내부 정보 비노출**: raw score, owner id, stack trace, 내부 debug 필드는 외부 DTO와 운영 경보에 노출하지 않는다.
7. **fail closed**: 탐지·근거화·헬스 체크 오류는 조용히 통과하지 않고 차단, 기권, 경보, degraded 상태 중 하나로 명시된다.
8. **U6 데이터 파이프라인 우선**: 실제 클라우드 라우팅보다 도메인 탐지 로직, 이벤트 계약 정합, 테스트 가능한 포트 구현을 먼저 만든다.

---

## 6. 패키지 구조 계획

### `ops/`

| 경로 | 목적 |
|---|---|
| `ops/pyproject.toml` | Python 패키지 설정, `docsuri-shared` path dependency, pytest/ruff/hypothesis |
| `ops/src/docsuri_ops/domain/models.py` | TelemetryEvent, IncidentCandidate, ClassifiedIncidentRecord, AlertRecord, BudgetSnapshot, HealthReport |
| `ops/src/docsuri_ops/domain/enums.py` | IncidentClass, Severity, CircuitState, DegradeMode, SignalKind |
| `ops/src/docsuri_ops/domain/errors.py` | U6 fail-closed 예외 타입 |
| `ops/src/docsuri_ops/ports.py` | EventStore, IncidentStore, AlertPublisher, Clock, IndexStatsProvider Protocol |
| `ops/src/docsuri_ops/observability.py` | `ObservabilityHub` 구현, PII/시크릿 redaction, append-only audit seam |
| `ops/src/docsuri_ops/cost_guard.py` | `CostGuardCircuitBreaker` 구현, usage 누적, 80% alert, hard-cap 전 degrade/open |
| `ops/src/docsuri_ops/grounding.py` | `GroundingEnforcementHook` 구현, 실재 record 매핑·기권·위반 산출 |
| `ops/src/docsuri_ops/detectors.py` | CostExplosionDetector, HallucinationDetector, PartialResultDetector |
| `ops/src/docsuri_ops/incidents.py` | AiIncidentDetectorSuite, IncidentEventPublisher |
| `ops/src/docsuri_ops/health.py` | HealthCheckService, U1 indexStats provider seam |
| `ops/src/docsuri_ops/reliability_eval.py` | ReliabilityEvalProbe, QT-3 평가셋 실행 |
| `ops/src/docsuri_ops/dashboard.py` | OpsDashboardService, windowed summary/listIncidents |
| `ops/src/docsuri_ops/adapters/local.py` | InMemory stores, local event bus, capturing alert publisher |
| `ops/src/docsuri_ops/worker.py` | 로컬/운영 워커 진입점. 이벤트 polling loop seam |
| `ops/src/docsuri_ops/cli.py` | run-detectors, run-grounding-eval, run-reliability-eval, dashboard-summary |

### `backend/middleware/`

| 경로 | 목적 |
|---|---|
| `backend/middleware/__init__.py` | U6 middleware package marker |
| `backend/middleware/request_context.py` | requestId, principal, degradation context 타입 |
| `backend/middleware/gateway.py` | FastAPI middleware seam: requestId, production error mapping, observability hook |
| `backend/middleware/security_headers.py` | SEC-4 보안 헤더 정책 |
| `backend/middleware/rate_limit.py` | U6 RateLimiter seam, local in-memory implementation |
| `backend/middleware/wiring.py` | app-shell이 나중에 mount 가능한 U6 middleware factory |

---

## 7. 코드 생성 단계

### Phase 1 — U6 패키지와 공용 테스트 기반
- [x] **Step 1: `ops/` 패키지 스캐폴드 생성**
  - `pyproject.toml`, `README.md`, `src/docsuri_ops/`, `tests/`
  - `docsuri-shared` path dependency 연결
  - pytest, ruff, hypothesis는 가상환경 안에서만 설치·사용
- [x] **Step 2: U6 도메인 모델과 enum 생성**
  - TelemetryEvent, UsageEvent, GroundingViolation, IncidentCandidate, BudgetSnapshot, DashboardWindow
  - IncidentClass는 RES-11 a/b/c와 `docsuri_shared.events.IncidentClass`에 정합
- [x] **Step 3: U6 포트 정의**
  - EventStore, IncidentStore, AlertPublisher, Clock, IndexStatsProvider
  - at-least-once 멱등 처리를 포트 계약에 명시

### Phase 2 — 관측성 데이터 파이프라인
- [x] **Step 4: `ObservabilityHub` 구현**
  - `emit_metric`, `emit_log`, `start_span`, `audit_append`
  - PII/시크릿 redaction allowlist 방식 적용
  - append-only audit store seam 제공
- [x] **Step 5: 로컬 이벤트/저장 어댑터 구현**
  - InMemoryEventStore, InMemoryIncidentStore, CapturingAlertPublisher
  - duplicate event id 처리 멱등성 구현
- [x] **Step 6: 관측성 단위 테스트 작성**
  - redaction, requestId 상관, audit append-only, duplicate event id 멱등 처리

### Phase 3 — 비용 상한 서킷과 비용 폭발 탐지
- [x] **Step 7: `CostGuardCircuitBreaker` 구현**
  - 월 시스템 상한은 현행 SSOT 기준 `$1600/month`
  - 80% 임계 경보
  - hard cap 접근 전 `degradeMode=LEXICAL_ONLY` 또는 `RERANK_OFF` 반환
  - U2는 조회만 하도록 `get_budget_state()` 포트 유지
- [x] **Step 8: `CostExplosionDetector` 구현**
  - intraday spend velocity, rate-limit spike, usage anomaly를 IncidentCandidate로 변환
  - 동일 window/requestId 중복 후보 멱등 처리
- [x] **Step 9: 비용 관련 테스트 작성**
  - 80% 경보, hard-cap 전 degrade, 비용 급증 분류, 중복 이벤트 억제
  - PBT: 임의 usage event sequence에서 누적 지출 단조성 및 임계 전이 안정성

### Phase 4 — 근거화 게이트와 할루시네이션 탐지
- [x] **Step 10: `GroundingEnforcementHook` 구현**
  - CandidateResponse의 노출 arXiv ID/URL이 RetrievedRecordSet에 존재하는지 검증
  - record 미매핑 또는 출처 없는 AI 텍스트는 `block` 또는 `abstain`
  - violations 목록은 내부 상세를 보존하되 외부 경보에는 일반화
- [x] **Step 11: `HallucinationDetector` 구현**
  - grounding violations, QT-1 eval failures, fabricated reference patterns를 RES-11(b) 후보로 변환
- [x] **Step 12: 근거화 테스트 작성**
  - pass/block/abstain 경로
  - 코퍼스 밖 질의 기권
  - fabricated arXiv ID 차단
  - PBT: 노출 카드 arxivId 집합은 retrieved record id 집합의 부분집합

### Phase 5 — 반쪽짜리 결과 탐지와 QT-3 평가
- [x] **Step 13: `PartialResultDetector` 구현**
  - `degraded=true` 누락, resultCount 불일치, retrieval failure + success 표시, empty success를 탐지
  - U2/U5가 명시한 degraded/abstain/fail-closed 상태를 정상 경로로 인정
- [x] **Step 14: `ReliabilityEvalProbe` 구현**
  - embedding failure -> lexical fallback
  - vector index failure -> fail-closed
  - empty candidate -> abstain
  - forced cost degrade -> explicit degraded result
- [x] **Step 15: 신뢰성/저하 테스트 작성**
  - QT-3 대표 시나리오 보고서 생성
  - PBT: 불완전 상태가 성공 상태로 잘못 분류되지 않음

### Phase 6 — 인시던트 분류·발행·대시보드 데이터
- [x] **Step 16: `AiIncidentDetectorSuite` 구현**
  - TelemetryEvent를 세 탐지기에 fan-out
  - IncidentCandidate를 `ClassifiedIncident`로 분류
  - severity 규칙: info/warn/critical에 대응하는 내부 enum과 shared schema 정합
- [x] **Step 17: `IncidentEventPublisher` 구현**
  - `docsuri_shared.events.ClassifiedIncident`
  - `docsuri_shared.events.OpsAlert`
  - requestId 기반 멱등 발행
  - alert/audit 동시 기록
- [x] **Step 18: `OpsDashboardService` 구현**
  - getDashboard(window)
  - listIncidents(filter)
  - 비용 상태, grounding health, partial-result incidents, ingestion health summary 제공
- [x] **Step 19: 인시던트/대시보드 테스트 작성**
  - cost/hallucination/partial-result class 매핑
  - alert 중복 억제
  - dashboard window aggregation

### Phase 7 — 헬스 체크와 backend middleware seam
- [x] **Step 20: `HealthCheckService` 구현**
  - shallowCheck
  - deepCheck
  - U1 `indexStats` provider seam
  - stale lastWrite, index count mismatch, dependency down 판정
- [x] **Step 21: `backend/middleware/` 최소 seam 구현**
  - FastAPI middleware factory
  - requestId 주입
  - production error mapping
  - security headers
  - rate limit seam
  - U6 ObservabilityHub 호출 seam
  - 실제 app-shell 결선은 별도 통합 PR에서 수행 가능하게 분리
- [x] **Step 22: 헬스/middleware 테스트 작성**
  - security headers
  - fail-closed production error response
  - shallow/deep health status
  - stale indexStats alert candidate

### Phase 8 — CLI, 문서, 검증
- [x] **Step 23: CLI/worker 진입점 구현**
  - `python -m docsuri_ops.cli run-detectors`
  - `python -m docsuri_ops.cli run-grounding-eval`
  - `python -m docsuri_ops.cli run-reliability-eval`
  - `python -m docsuri_ops.worker`
- [x] **Step 24: README 및 코드 요약 문서 작성**
  - `ops/README.md`
  - `aidlc-docs/construction/u6-reliability-ops/code/u6-reliability-ops-code-summary.md`
- [x] **Step 25: 검증 실행**
  - 가상환경 생성 후 의존성 설치
  - `python -m pytest`
  - `python -m ruff check .`
  - shared contract import smoke

---

## 8. 테스트 계획

| 테스트 범주 | 대상 |
|---|---|
| Unit | redaction, cost circuit, detectors, grounding, health, dashboard |
| PBT | usage 누적 단조성, grounding subset invariant, partial-result misclassification 방지 |
| Fault Injection | event duplicate, store failure, alert publisher failure, stale indexStats, detector exception |
| Contract | `docsuri_shared.events` payload 생성, `docsuri_shared.ports` Protocol 호환 |
| Security | PII/secret redaction, generic errors, append-only audit, no internal debug exposure |
| Resiliency | duplicate event idempotency, fail-closed, stale dependency health, alert routing |

---

## 9. 가상환경 및 의존성 원칙

사용자 지시에 따라 전역/user Python 환경에는 테스트 라이브러리를 설치하지 않는다.

구현 단계에서 필요한 경우:

1. `ops/.venv` 생성
2. 해당 가상환경 활성화
3. `ops/pyproject.toml` 기반으로 dev dependency 설치
4. 테스트와 린트는 가상환경 Python으로 실행

---

## 10. 보안 준수 계획

| 규칙 | 적용 계획 |
|---|---|
| SECURITY-03 | 구조화 로그, requestId, PII/시크릿 redaction |
| SECURITY-05 | 이벤트 payload schema validation, unknown field handling |
| SECURITY-08 | ops dashboard/admin API는 관리자 인가/MFA seam만 제공, 공개 접근 금지 |
| SECURITY-09 | 내부 stack/debug/raw score 비노출 |
| SECURITY-10 | lockfile 또는 가상환경 기반 dependency pin, SBOM/SCA 명령 문서화 |
| SECURITY-11 | RateLimiter와 cost guard 연동 |
| SECURITY-13 | critical audit event append-only |
| SECURITY-14 | alert/dashboard/audit retention seam 문서화 |
| SECURITY-15 | detector/store/publisher 실패 시 fail-closed 또는 alertable degraded state |

N/A: SECURITY-01/02/04/06/07/12는 이번 코드 계획에서는 직접 IaC나 사용자 인증 구현을 생성하지 않으므로 후속 Infrastructure/App-shell 통합에서 적용한다. 단, middleware seam은 해당 규칙을 위반하지 않도록 public ingress를 열지 않는다.

---

## 11. 복원력 준수 계획

| 규칙 | 적용 계획 |
|---|---|
| RESILIENCY-01 | U6 dependency map: U1 indexStats, U2 telemetry, U3 auth signals, event backbone, alert publisher |
| RESILIENCY-05 | metrics/logs/traces/audit 수집 구현 |
| RESILIENCY-06 | shallow/deep health check 구현 |
| RESILIENCY-07 | stale ingestion, cost spike, partial result, grounding failure alert |
| RESILIENCY-09 | detector/store/publisher timeout/fail-closed seam |
| RESILIENCY-10 | downstream alert publisher/store 실패 격리 |
| RESILIENCY-11 | RES-11 a/b/c 인시던트 분류·발행 |
| RESILIENCY-14 | ReliabilityEvalProbe와 QT-3 시나리오 |
| RESILIENCY-15 | 경량 IR/COE 라우팅용 incident/alert payload 제공 |

N/A 또는 후속: RESILIENCY-02/03/04/08/12/13은 인프라/배포/운영 런북 범위이므로 이번 코드 계획에서는 seam과 문서 근거만 남긴다.

---

## 12. 완료 기준

- U6 코드 생성 계획의 모든 단계가 승인 후 순서대로 실행되고 `[x]`로 갱신된다.
- `ops/` 패키지가 `docsuri_shared` 계약을 직접 소비한다.
- `backend/middleware/`에는 app-shell과 결선 가능한 seam이 생성된다.
- U6는 `GroundingEnforcementHook`, `CostGuardCircuitBreaker`, `ObservabilityHub` Protocol을 구현한다.
- RES-11 a/b/c 세 인시던트가 모두 탐지·분류·발행 테스트를 갖는다.
- QT-1/QT-3 평가 진입점이 CLI와 테스트로 검증된다.
- PII/시크릿 redaction, 멱등 소비, fail-closed 경로가 테스트된다.
- 전체 테스트와 린트가 가상환경 안에서 통과한다.

---

## 13. 승인 게이트

본 문서는 U6 Reliability/Ops 데이터 및 탐지 파이프라인 Code Generation의 단일 실행 계획이다. 승인 전에는 `ops/` 또는 `backend/middleware/` 애플리케이션 코드를 생성하지 않는다.

승인 후 Code Generation Part 2에서 Step 1부터 순차 실행하며, 각 단계 완료 즉시 본 계획의 체크박스를 `[x]`로 갱신한다.
