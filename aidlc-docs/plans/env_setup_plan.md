# 환경 구축 라운드 — 작업 계획 (상시 데모 인프라)

> **Phase**: AIDLC Construction — 환경 구축 (Operations)
> **선행 완료** (2026-06-11, [`u0-aws-env-verification.md`](../reviews/u0-aws-env-verification.md) · PR #25 머지됨): ADR §14 검증 4건 실측 종결(도쿄+Cohere 조합). 검증 리소스는 전량 삭제 — **상시 리소스는 현재 0개**.
> **⟳ 전제 갱신 (2026-06-12 라운드 개시 시점)**: [ADR-D3 재검토](../plans/adr_d3_reconsideration_plan.md)(Prompt 26)로 **리전 서울(ap-northeast-2) + Titan Text Embeddings V2(1024d)** 확정 환원. `aws.py`는 Titan·청크 dedup으로 재작성되어 develop 포함. **ADR-D2 잔여 = "서울+Titan 재검증"** — 본 라운드의 프로비저닝(B1·B2)이 곧 그 재검증이다.
> **계정**: 028317349537 · **서울(ap-northeast-2)** · SSO `AdministratorAccess-028317349537` (활성 확인) · use-case 폼 게이트 해소.
> **이번 라운드의 일**: 데모용 상시 인프라 프로비저닝 + 데이터 적재 + 백엔드 배포 + Amplify 연동 + aws 모드 검증 + 리뷰 후속 병합분.
> **비용**: 상시 리소스 ~<$2/월 + Bedrock 사용량(CostGuard $50 하드 스톱) — [ADR §13](../design-artifacts/architecture_decision_record.md) 범위 내.

---

## 사전 확인 (완료)

- [x] **S0. 선행 검증 산출물 정독** — KB teardown 함정(DS `RETAIN` 후 삭제), `.metadata.json` 사이드카로 숫자 `year` 필터 전파, 콜드 P50 887ms(워밍 불요), LLM 경로는 cost 테이블 요구.
- [x] **S1. 자격·게이트 확인** — SSO 활성(계정 일치), use-case 폼 해소.
- [x] **S2. 워크트리 정리 (2026-06-12, 사용자 지시)** — PR #22·#25 머지 확인 → `aws-env-verify`(머지됨)·`aws-integration-test`(하네스가 develop에 포함됨 확인)·`fix-ingest-stream-url`(레거시 demo/ 대상 미커밋 90줄 — job tmp에 patch 백업 후) 워크트리 3개 제거, 로컬·원격 머지 브랜치 정리. 타 세션 활성 워크트리 `github-team-project`는 보존. 본 워크트리는 `feature/aidlc-construction-env-setup`(develop 분기)으로 전환.

---

## 사용자 클래리피케이션 (확인 완료, 2026-06-12)

- [x] **C1. 프로비저닝 방식** — **boto3 idempotent 스크립트** 확정 (`scripts/provision_aws.py` + `teardown_aws.py`).
- [x] **C2. 배포 범위** — **Amplify 연동까지 포함** 확정 (사용자 선택 — GitHub 권한 대기 발생 가능 인지). 백엔드 Lambda + Function URL + 프론트 Amplify Git 연동 시도, 권한 게이트에 걸리면 가이드로 전환.
- [x] **C3. 브랜치 기반** — **#25(및 #22) 머지 후 develop 분기** 확정·완료.
- [x] **C4. U4-M2 처리** — UI 문구 보수화 기본값으로 승인 (OneHopResult 플래그는 후속 사이클 백로그).

---

## 실행 단계 (승인 후 진행)

### Part A — 선행 정리

- [x] **A1. 검증 하네스 회수** — **불필요 판정**: `test_aws_integration.py`가 이미 develop에 포함(머지 확인). 하네스 docstring의 구 리전 표기(도쿄)만 A3에서 소정리.
- [ ] **A2. U0-M1 패치** — `DynamoCostStore`에 조건부 갱신(`usd < :cap`) 추가로 check→record 비원자성 해소 (CostGuard 하드 스톱의 원자화). InMemoryCostStore 동일 의미 적용 + 테스트.
- [ ] **A3. 소정리** — U4-L1(캐시 윈도우 트레이드오프 주석), U4-M2(빈 상태 문구 보수화 — C4), 하네스 docstring 리전 표기 갱신.

### Part B — 프로비저닝 (boto3, 서울, 태그 `project=docsuri-demo`) — *ADR-D2 "서울+Titan 재검증" 겸함*

- [ ] **B1. `scripts/provision_aws.py`** — DynamoDB 3테이블(cache·glossary·cost, TTL 속성 `expires_at` — U0-L5 정합) · S3 소스 버킷 + S3 Vectors 버킷·인덱스(**cosine, 1024d Titan V2** — U0-M3 명시) · KB 서비스 롤 + KB + 데이터소스(`dataDeletionPolicy=RETAIN` — teardown 함정 선제 회피). idempotent(존재 시 skip).
- [ ] **B2. 데이터 적재** — `build_corpus.py` 확장(초록 본문도 저장: `corpus_docs.json`) 후 재수집 → 100편 본문+`.metadata.json` 사이드카 S3 업로드 → KB ingestion job · glossary 50개 → DynamoDB 적재. **서울 KB×S3 Vectors×Titan 생성·색인 성공 = ADR-D2 잔여 재검증 닫힘.**
- [ ] **B3. `scripts/teardown_aws.py`** — 역순 삭제(KB→인덱스→버킷→테이블), 검증 세션의 함정 대응 포함.

### Part C — 백엔드 배포 (C2 범위)

- [ ] **C-D1. Lambda 컨테이너** — Dockerfile(arm64, Web Adapter) + ECR push + 함수 생성(1024MB) + Function URL + 환경 변수(`DOCSURI_ADAPTER_MODE=aws`, 테이블·버킷·KB ID).
- [ ] **C-D2. Amplify 준비** — `amplify.yml` 빌드 스펙 + 연결 가이드 문서 (실제 연동은 팀 액션).

### Part D — 검증·마감

- [ ] **D1. aws 모드 통합 테스트** — 하네스 전체(Tier A+B — DynamoDB 캐시·용어집·비용 누적 경로 포함) 통과.
- [ ] **D2. aws 모드 E2E** — Function URL로 `/healthz`·`/api/search`(실 Bedrock+S3V)·`/api/citations`(실 Semantic Scholar) 호출 + 프론트 로컬(BACKEND_URL=Function URL) 브라우저 확인. NFR-PERF 실측 기록.
- [ ] **D3. 이중 캐시 실측(U4-L2)** — citation 1회 흐름의 DynamoDB 쓰기 수 확인, 비용 영향 기록.
- [ ] **D4. 문서·커밋** — 구축 결과를 `aidlc-docs/reviews/env-setup-report.md`(리소스 목록·실측치·비용)로 기록, 계획 갱신, 커밋·PR.
- [ ] **D5. 사용자 최종 리뷰** — Function URL·실측 결과 제출.

---

## 범위 밖 (Out of Scope)

- Amplify 실제 Git 연동·프로덕션 도메인 (팀 액션 후 후속).
- 정식 IaC 전환(SAM/CDK), CI/CD — 후속 사이클.
- U3 통합 (타 팀원 빌드 중).
- OneHopResult degraded 플래그 (동결 모델 변경 — 후속 사이클 백로그, C4).
