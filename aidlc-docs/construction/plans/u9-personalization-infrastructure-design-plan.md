# u9-personalization-infrastructure-design-plan.md — Infrastructure Design 계획 + 질문 게이트

**단계**: CONSTRUCTION -> Infrastructure Design (유닛별 루프)  
**유닛**: U9 Personalization  
**일자**: 2026-06-23  
**근거**: `construction/u9-personalization/functional-design/`, `construction/u9-personalization/nfr-design/`

> 본 계획서는 리뷰 게이트다. 아래 `[Answer]:`가 모두 확정되기 전에는 Infrastructure Design 산출물을 만들지 않는다.

## 1. Infrastructure Design 실행 판정

U9는 새 사용자 행동 이벤트 테이블, 집계 프로필 테이블, 백업 테이블, 삭제/보관 운영 경로가 필요하므로 Infrastructure Design을 실행한다.

기본 방향은 기존 인프라 재사용이다.

- 기존 FastAPI backend app-shell에 U9 route를 추가한다.
- 기존 ECS/Fargate API 배포 단위와 U6 gateway/auth/rate-limit 경로를 재사용한다.
- 기존 RDS PostgreSQL에 U9 테이블과 migration을 추가한다.
- 기존 U6 ObservabilityHub/EventStore와 CloudWatch 경보 경로를 재사용한다.
- v1에서는 새 ECS 상시 서비스, 새 Redis cache, 새 SQS queue, 새 analytics lake, 새 ML pipeline을 만들지 않는다.

## 2. Infrastructure Design 실행 계획

답변 확정 후 아래 산출물을 `aidlc-docs/construction/u9-personalization/infrastructure-design/`에 작성한다.

- [ ] **infrastructure-design.md**
  - compute, storage, lifecycle, security, observability, shared infrastructure mapping
- [ ] **deployment-architecture.md**
  - existing backend deployment, RDS table boundary, U6 gateway path, scheduled cleanup path

## 3. 질문 범주 검토

| 범주 | 적용 여부 | 계획 반영 |
| --- | --- | --- |
| Deployment Environment | 적용 | 기존 AWS `ap-northeast-2` 프로덕션 환경 재사용 여부 확인 |
| Compute Infrastructure | 적용 | 기존 API ECS task에 동거할지, 별도 서비스가 필요한지 확인 |
| Storage Infrastructure | 적용 | 기존 RDS 테이블 및 backup table lifecycle 확인 |
| Messaging Infrastructure | 적용 | 이벤트 기록을 동기 best-effort DB write로 둘지 큐를 둘지 확인 |
| Networking Infrastructure | 적용 | 기존 ALB/CloudFront/U6 gateway 경로 재사용 확인 |
| Monitoring Infrastructure | 적용 | 기존 U6/CloudWatch 경로 재사용 확인 |
| Shared Infrastructure | 적용 | 새 공유 리소스 생성 없이 기존 리소스에 붙는지 확인 |

## 4. 명확화 질문

### Q1 — Deployment and Compute
U9 API와 decision read path는 어디에 배포할까요?

A) **기존 backend app-shell/ECS API task에 `backend/modules/personalization/`로 추가한다.** 새 상시 서비스는 만들지 않는다. (권장)

B) U9를 별도 ECS service로 분리한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Q2 — Storage
행동 이벤트, 백업 이벤트, 프로필, 설정은 어디에 저장할까요?

A) **기존 RDS PostgreSQL에 migration으로 `user_behavior_events`, `user_behavior_event_backup`, `user_interest_profiles`, `personalization_settings` 테이블을 추가한다.** (권장)

B) 별도 PostgreSQL database/schema를 만든다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Q3 — Backup Table Retention
사용자가 raw behavior log 삭제를 요청했을 때 생성되는 backup table row는 얼마나 보관할까요?

A) **개인화 경로에서는 즉시 제외하고, backup row는 30일 보관 후 purge한다.** 복구/감사 안전성만 남기고 장기 보관은 피한다. (권장)

B) active raw event와 동일하게 90일 보관 후 purge한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Q4 — Cleanup Job
active raw event 90일 retention과 backup table purge는 어떤 방식으로 실행할까요?

A) **기존 backend container의 maintenance command를 EventBridge scheduled ECS task로 매일 실행한다.** 상시 worker는 만들지 않는다. (권장)

B) cleanup을 API 요청/집계 시점의 lazy cleanup으로만 처리한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Q5 — Messaging
행동 이벤트 기록에 큐를 둘까요?

A) **큐 없이 기존 API path에서 best-effort RDS write로 기록한다.** 실패해도 본 기능은 성공 유지하고 U6 telemetry만 남긴다. (권장)

B) SQS queue와 별도 consumer를 추가해 비동기 기록한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Q6 — Monitoring and Configuration
U9 관측과 설정은 어떤 인프라를 사용할까요?

A) **기존 U6 ObservabilityHub/CloudWatch와 env feature flag `PERSONALIZATION_ENABLED`를 재사용한다.** 원시 행동 payload는 로그/메트릭에 싣지 않는다. (권장)

B) 별도 analytics/BI 관측 파이프라인을 만든다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## 5. Content Validation

- Mermaid diagram: 없음.
- ASCII diagram: 없음.
- Markdown table/code block: CommonMark 호환 형식으로 작성.
- Question format: 모든 질문은 A/B/X 선택지와 `[Answer]:` 태그를 포함.

