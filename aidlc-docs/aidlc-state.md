# AI-DLC 상태 추적 (State Tracking)

## 프로젝트 정보
- **프로젝트명**: DocSuri (연구 지원 애플리케이션)
- **프로젝트 유형**: Greenfield(그린필드)
- **시작일**: 2026-06-15T04:36:30Z
- **현재 단계**: CONSTRUCTION - U8 Citation Graph Functional Design 계획·질문 게이트 작성 완료, 답변 대기. **[2026-06-19: U8 Citation Graph 편입 — 질문지 22문 답변 반영(Q3/Q10=X, Q4/Q14=B, 나머지 권장안), FR-15~16·NFR-P3·QT-6·US-CG1..CG6·U8 유닛 등재. Functional Design 계획서 `construction/plans/u8-citation-graph-functional-design-plan.md` Q1~Q12 답변 대기.]**
- **문서 언어**: 한국어(`aidlc-docs/` 산출물). 업스트림 룰셋(`AGENTS.md`, `.aidlc-rule-details/`)은 영어 유지.

## ⚠️ 검증 재기준선 (Verification Re-baseline) — 2026-06-16

코드 대조 감사(7개 영역 병렬 검증, 각 테스트 스위트 실제 실행) 결과, 아래 항목은 문서가 실제 상태를 **과대 표기**하고 있어 정정한다. **`완료·승인`은 "설계/코드 작성 완료"를 뜻하며 "통합·실 인프라 동작·실 안전장치 작동"을 보증하지 않는다.** 제품은 현재 엔드투엔드 사용 불가(프런트 없음·게이트웨이 없음).

- **U2 미마운트 (High)**: app-shell 부팅 시 discovery는 매번 **graceful-skip**된다(별도 uv 프로젝트 `discovery`가 backend venv에 미설치 → `_mount_discovery` `ModuleNotFoundError`). 통합 앱은 `/auth/*`+health만 노출, **`/api/search` 없음**. 8개 테스트는 레지스트리 *집합*만 단언하고 실제 마운트는 단언하지 않아 skip이 green으로 통과.
- **근거화(Grounding) 실효 없음 (Blocker)**: INV-1 분리는 구조적으로 정확. **U6는 `feature/track6`(미머지)에 구현됨** — 실 `GroundingEnforcementHook.enforce`(`ops/grounding.py`: retrieved 미포함 참조=block·근거 없음=abstain) + `backend/middleware/` 게이트웨이(rate-limit·보안헤더·fail-closed; **단 게이트웨이 자체는 grounding 미호출**). **그러나 라이브 경로 미연결**: `create_app`이 게이트웨이 미설치(테스트만 `configure_u6_middleware` 호출)·discovery 와이어링은 여전히 `StubGroundingHook`(항상 `pass`) 주입(`backend/app.py`·`backend/wiring.py`·discovery 모듈 track6에서 미변경). ⇒ **develop엔 환각/날조 방지(US-D5/US-R1)가 실 경로에서 작동 전무이며, track6 단순 머지만으로도 미해소** — 연결 last-mile(게이트웨이 설치 + 시임에 실 hook 주입, ops↔shared 타입 정합) 필요.
- **CI 부재 (High)**: `.github/workflows/` 없음(CODEOWNERS+PR 템플릿만). `CI=GHA`·`드리프트 CI 가드`는 의도일 뿐 **미구현** — 드리프트 가드/모든 테스트는 수동 실행.
- **U3 결함 (High)**: `auth.py`가 10회 실패 시 `status=LOCKED` 전이 → **BR-A4 무잠금 anti-DoS 규칙 직접 위반**. TOTP MFA·시딩 관리자(BR-A7) 미구현(ADMIN 도달 불가). accounts가 `docsuri_shared` 미소비·DTO 자체 재정의(**SSOT 포크**)·`AccountCreated` raw dict·ObservabilityHub camelCase 오호출.
- **인프라/배포 부재 (High)**: IaC·CD 전무, 인프라 설계는 U3만 존재. U2 real 어댑터(OpenSearch/Bedrock) 미존재 → 실데이터 검색 불가.
- **테스트 수 정정 (Low)**: U1 21→**23**, U2 27→**31**(api extra)/29+1 skip.

**후속 크리티컬 패스**: ① discovery 마운트+CI 마운트-단언 → ② GHA CI(드리프트+pytest+ruff) → ③ U3 정정(BR-A4·SSOT) → ④ **U6 통합 [키스톤·대부분 빌드 완료]: `feature/track6` 머지 + `create_app` 게이트웨이 설치 + discovery 시임에 실 grounding hook 주입(`StubGroundingHook` 대체)** → ⑤ U5 프런트 → ⑥ U2 real 어댑터 → ⑦ 시스템 인프라+U4. _주: track6 머지 시 aidlc-state.md(track6 +5/-1)·audit.md 충돌 예상._

## ✅ 크리티컬 패스 종결 (Critical Path Closure) — 2026-06-18

위 2026-06-16 재기준선이 지정한 후속 크리티컬 패스 ①~⑦가 **전부 랜딩**됐고 시스템 전역 인프라가 AWS에 배포됐다. 본 절은 코드/깃 이력 대조로 확인한 종결 상태를 기록한다(원 재기준선 텍스트는 2026-06-16 시점 사실로 보존; **본 절이 현재 상태의 단일 진실**). 커밋 SHA 병기.

- **① discovery 마운트 + 마운트-단언 — 종결.** `backend/wiring.py::_mount_discovery`가 실제 라우터를 마운트(`/api/search` 라이브); 테스트가 200+`cards` 및 `skipped==[]`를 단언(레지스트리 집합 단언 아님). 커밋 `ae58e0f`·`404c1a7`.
- **② GHA CI — 종결.** `.github/workflows/ci.yml` 8 레인(shared[드리프트 가드 `tools/generate.py --check`+ruff+pytest]·ingestion·discovery[`--extra api`]·ops·backend[마운트 단언]·root-suites[accounts+library]·frontend[tsc+타입 드리프트 가드+lint+vitest+next build]) + `cd.yml`(main 푸시). 커밋 `f9a7e8a`(첫 게이트)·`7edd316`(ops)·`404c1a7`(accounts/library)·`30a0773`·`bd8817b`(frontend).
- **③ U3 정정 — 종결.** BR-A4 무잠금(자동 LOCKED 제거·백오프+CAPTCHA만, LOCKED=관리자 수동 경로 한정)·SSOT 포크 제거(`docsuri_shared` 소비)·BR-A7 실 TOTP MFA+시딩 관리자(ADMIN 도달). 커밋 `bbac74f`·`f835a26`·`9b390b9`.
- **④ U6 통합(게이트웨이+실 grounding hook) — 종결.** `create_app`이 게이트웨이 미들웨어 설치(`configure_u6_middleware`); `_mount_discovery`가 mock·real 양 경로에 실 `GroundingEnforcementHook` 주입(`StubGroundingHook`은 discovery mock 패키지에만 잔존·미배선); 게이트웨이 세션쿠키→`request.state.principal` 주입. 커밋 `ba4a62e`·`b6bb92d`·`568677c`.
- **⑤ U5 프런트 — 종결·배포.** production 패스 머지(PR #63, `86404d1`); HTTPS 프로덕션 배포(Fargate+ALB+CloudFront @ docsuri.org, `d1740b0`); BFF 빌드 복구(`344172e`).
- **⑥ U2 real 어댑터 — 종결.** OpenSearch k-NN+BM25 + Bedrock Cohere 질의 임베더 + EventBridge 퍼블리셔; env 토글로 mock/real. 커밋 `b87348d`·`a25d8ed`.
- **⑦ 시스템 인프라 + U4 — 종결·배포.** U4 라이브러리 머지(`b70f2ee`). 시스템 전역 Infrastructure Design(`construction/infrastructure-design/infrastructure-design.md`, `ac21ae2`); AWS CDK Python IaC 5 스택(Network·Search·Compute·Ingestion·Frontend, `ddf8858`); CD 파이프라인(ECR 빌드·푸시+ECS 롤링, `db1b187`); 프로덕션 DB/세션 실연결(RDS Postgres+ElastiCache TLS, `01fd553`·`5f7acce`); API HTTPS 하드닝(CloudFront+ACM+시크릿 오리진, `504cb64`·`28ed940`); CloudWatch EventStore 어댑터(`8b54b62`)·SQL 마이그레이션 러너(`5de4348`); SES 실 발송(boto3+도메인 인증+IAM, `50da0d5`)+바운스/불만 자동 억제+SNS(`0437b40`).

**라이브 배포(런타임·리포지토리 대조 불가)**: 4 CDK 스택 라이브 배포·API ALB healthy = 계정 028317349537/서울(`ap-northeast-2`), 팀 보고(2026-06-17). 본 종결은 IaC 코드·커밋 대조까지 보증하며 실 배포 헬스는 AWS 콘솔/자격증명 확인 필요.

### 잔여 항목 (Residual)
- **CI 린트 사각 (Low)**: 루트 `tests/` 트리를 린트하는 레인 없음 → `ruff check .` 루트 기준 `tests/accounts/*` F401 9건이 CI에 미노출(전부 `--fix` 가능). backend 레인은 `modules/` 제외·root-suites 레인은 모듈 소스만 린트.
- **ci.yml 헤더 주석 stale (Low)**: 1~5행 주석이 "tests/accounts 미연결"이라 표기하나 현 `root-suites` 잡이 해당 스위트를 실행.
- **테스트 수 드리프트 (Info·benign)**: 스위트 증가로 문서 수치 stale(U1 23→26·U6 31→34·U4 컴포넌트 분할·U2 42+1skip). 회귀 아님.
- **Operations 프레임워크 갭**: AI-DLC 룰셋은 Build and Test에서 종료(Operations=placeholder)이나 실 AWS 프로덕션 배포가 프레임워크 밖에서 수행됨 — 운영 런북/롤백/모니터링 문서 미수립(§OPERATIONS 참조).

## 워크스페이스 상태
- **기존 코드**: 없음(워킹 트리 블랭크 슬레이트; 이전 데모 사이클 폐기, git `ba3b6a9`로 복구 가능)
- **리버스 엔지니어링 필요**: 아니오(Greenfield — 디스크에 소스 파일 없음)
- **워크스페이스 루트**: 리포지토리 루트(머신별 상대; 예: `<홈>/Projects/DocSuri`) — 절대 경로는 머신마다 다름
- **프로그래밍 언어**: (미정 — Construction 단계)
- **빌드 시스템**: (미정 — Construction 단계)
- **프로젝트 구조**: 비어 있음(AI-DLC Prompt 1부터 재시작)

## 코드 위치 규칙
- **애플리케이션 코드**: 워크스페이스 루트(절대 aidlc-docs/ 안에 두지 않음)
- **문서**: aidlc-docs/ 전용
- **구조 패턴**: code-generation.md의 Critical Rules 참조

## 확장 구성 (Extension Configuration)
| 확장 | 활성 | 모드 | 결정 시점 |
|---|---|---|---|
| Security Baseline | 예 | Full(15개 규칙 전부 차단성) | Requirements Analysis (2026-06-15) |
| Resiliency Baseline | 예 | Full(15개 규칙 전부 차단성) | Requirements Analysis (2026-06-15) |
| Property-Based Testing | 예 | Partial(PBT-02/03/07/08/09만 차단성; 01/04/05/06/10 권고) | Requirements Analysis (2026-06-15); Full→Partial 변경 2026-06-15(팀원 권고, 기술 스택 확정 후 재평가) |

_Resiliency 옵트인은 `requirements.md` 확정 전에 필수 요구사항 명확화를 유발: RTO/RPO + DR 전략(RESILIENCY-02), 변경 관리(RESILIENCY-03), 장애 대응(RESILIENCY-15). `inception/requirements/requirement-clarification-questions.md`에서 질의함. 후속 단계로 보류: CI/CD + 롤백 + 배포 방식(RESILIENCY-04 → NFR Design), 리전 토폴로지(RESILIENCY-08 → Infra Design), 복원력 테스트(RESILIENCY-14 → NFR Design)._

## 단계 진행 (Stage Progress)

### 🔵 INCEPTION 단계
- [x] 워크스페이스 탐지(Workspace Detection) — Greenfield (2026-06-15)
- [~] 리버스 엔지니어링 — N/A (Greenfield, 건너뜀)
- [x] 요구사항 분석(Requirements Analysis) — 완료·승인 (2026-06-15); `requirements.md`. 명확화 2라운드; 모순 전건 해소; 확장 전부 활성
- [x] **요구사항 개정 — 신규 유닛 U7(요약/번역) 편입 (2026-06-18, 팀 합의·브랜치 `feature/u7`·PR #108)**: U1~U6 빌드·배포 완료 후 Requirements Analysis 재진입. 명확화 `requirement-verification-questions-u7.md` Q1~Q7 전부 A(초안 권장안) → `requirements.md`에 **FR-12(AI 요약·구조화·앵커)·FR-13(한국어 번역·용어집)·FR-14(개인화: persona/뷰/용어집)·NFR-P2(온디맨드 비-SLA)·QT-5(요약/번역 근거화)·NFR-C1 U7 Sonnet 비용 라인 보강·C-2 추출 경계·§12 제외(P3·자유입력)** 등재. 설계 입력 `aidlc-docs/inception/requirements/summarization-translation-pipeline.md`(2026-06-18 레포 루트→aidlc-docs 재배치 완료). **다음: User Stories(U7) → Units Generation(U7 등재·U1/U6 의존) → Construction 유닛 루프.** 리뷰 게이트 대기.
- [x] 사용자 스토리(User Stories) — 계획 승인(PQ1–5=A); Part 2에서 `stories.md`(스토리 **21개**, 6 에픽: Hero 1 + Discovery 7 + Accounts 2 + Library 3 + Ingestion 3 + Reliability 5) + `personas.md`(P1 박지훈, P2, OP) 생성; FR-1..11 전부 커버; **승인 완료**. **적대적 비평 패스 완료(2026-06-15, 7/7 critic)** → requirements/stories 보정 반영.
- [x] Workflow Planning — `execution-plan.md` **승인 완료**. 판정: 리버스 엔지니어링만 SKIP, 그 외 전 단계 EXECUTE.
- [x] Application Design — 완료(리뷰 게이트). `application-design/` 5문서(components·component-methods·services·component-dependency·application-design); 6 유닛(U1~U6); 적대적 3 critic→blocking/major 보정 반영(근거화 단일 권위, SearchExecuted 생산자, SEC-8 단일 결정점, QT-3 소유자, 백도어 차단)
- [x] Units Generation — 완료(리뷰 게이트). `unit-of-work.md`·`unit-of-work-dependency.md`·`unit-of-work-story-map.md`; 6 유닛·4 배포 단위·모노레포·데모 우선 순서; 스토리 21개 전수 매핑·코드 의존 DAG(adversarial 검증 solid)
- [ ] Units Generation — **EXECUTE** (예비 유닛: U1 인제스천, U2 디스커버리 API, U3 계정/인증, U4 검색저장/라이브러리, U5 모바일 웹, U6 신뢰성/운영)
- [x] **사용자 스토리 개정 — U7(요약/번역) 에픽 추가 (2026-06-18, 팀 합의·`feature/u7`·PR #108)**: `stories.md`에 **에픽 6 — 요약/번역**(US-S1 구조화 요약·US-S2 한국어 번역·US-S3 출처보기+기권·US-S4 개인화·US-S5 온디맨드 응답·US-S6 비용게이트+근거화 운영) 6 스토리 추가 → 총 27 스토리/7 에픽. P1(US-S1..S5)·OP(US-S6) 매핑, FR-12..14·NFR-P2·QT-5 전수 커버. 페르소나 무변경(P1·OP가 U7 커버).
- [x] **Units Generation 개정 — U7 정식 등재 (2026-06-18, 팀 합의·`feature/u7`·PR #108)**: `unit-of-work.md`(U7 Summarization 유닛 정의·배포 단위 ①+③옵션·코드트리 `backend/modules/summarization/`·확장 트랙)·`unit-of-work-dependency.md`(U7 행/열 추가, U7→U1 capability read·U7→U6 `shared/ports` lib·U5→U7/U6→U7 sync, **코드 DAG 비순환 유지 검증**, 온디맨드 요약 ASCII 흐름)·`unit-of-work-story-map.md`(US-S1..S5 Owner=U7·US-S6 Owner=U6 기여=U7, 전수 27 스토리 검증) 갱신. **7 유닛·4 배포 단위(U7=API 모듈, 초장문만 비동기 잡 옵션).** 리뷰 게이트 대기. **다음: U7 Construction 유닛 루프(Functional Design부터).**
- [x] **요구사항 개정 — 신규 유닛 U8(인용 그래프/각주 트리) 편입 (2026-06-19)**: 명확화 `requirement-verification-questions-citation-graph.md` 22문 답변 확정(Q3/Q10=X, Q4/Q14=B, 나머지 권장안) → `requirements.md`에 **FR-15(각주 트리/backward references)·FR-16(노드 저장/연동)·NFR-P3(온디맨드 비-SLA)·QT-6(인용 엣지 정확도+그래프 불변식)·§12 카브아웃** 등재. v1은 논문 상세보기 페이지의 backward references 각주 트리로 한정, FE 구현·forward citations·3-hop 이상은 제외.
- [x] **사용자 스토리 개정 — U8 에픽 추가 (2026-06-19)**: `stories.md`에 **에픽 7 — 인용 그래프 / 각주 트리**(US-CG1 상세보기 각주 트리·US-CG2 깊이/노드 메타·US-CG3 unresolved 분리·US-CG4 라이브러리 저장·US-CG5 실패/쿼터 저하·US-CG6 운영 관측성) 6 스토리 추가 → 총 33 스토리/8 에픽. P1(US-CG1..CG5)·OP(US-CG6) 매핑, FR-15..16·NFR-P3·QT-6 커버.
- [x] **Units Generation 개정 — U8 정식 등재 (2026-06-19)**: `unit-of-work.md`(U8 Citation Graph 유닛 정의·배포 단위 ① API 모듈·코드트리 `backend/modules/citation_graph/`)·`unit-of-work-dependency.md`(U8 행/열 추가, U8→U3/U6 로그인·게이트웨이, U8→U4 저장 계약, U7→U8 출처 연동, 코드 DAG 비순환 검증, 각주 트리 ASCII 흐름)·`unit-of-work-story-map.md`(US-CG1..CG5 Owner=U8·US-CG6 Owner=U6 기여=U8, 전수 33 스토리 검증) 갱신. **8 유닛·4 배포 단위(U8=API 모듈).** **후속: U8 Construction Functional Design 질문 게이트 진입 완료, 답변 대기.**

### 🟢 CONSTRUCTION 단계 (유닛별 루프)

**U1 Ingestion** (프로덕션 직행 1번; 데모 트랙 폐기):
- [x] Functional Design — **완료·승인·프로덕션 재스코핑 (2026-06-16)**. `construction/u1-ingestion/functional-design/`(domain-entities·business-logic-model·business-rules). 프로덕션: **Q1=D 풀 슬라이스(5cat×5yr 수십만)·Q2=C OA 전문 청킹·Q12=B 이벤트 경로 활성·Q13=B 철회 tombstone**. INV-1 커밋순서·논문 단위 원자성·PBT-08 P1~P6. **FD 완전 추상(기술 무관)**. 적대적 검증 3패스.
- [x] NFR Requirements — **완료·승인 (2026-06-16)**. `construction/u1-ingestion/nfr-requirements/`(nfr-requirements·tech-stack-decisions). 스택: Python·**OpenSearch[전역]**·**cross-lingual 임베딩(Cohere Embed Multilingual v3, 1024·코사인)[전역]**·EventBridge·SQS·S3·Hypothesis·SEC-10. **NFR-C1=$1600/월(시스템 전역, 기존 $300 대체)**. **엄격 OA 라이선스 검증(BR-1)**. VectorSpec PIN·AS-4 수치 확정.
- [x] NFR Design — **완료·승인 (2026-06-16)**. `construction/u1-ingestion/nfr-design/`(nfr-design-patterns·logical-components). 버전 단조 tombstone(`current_version` compare-and-set)·indexStats 내부경계+캐시TTL·RES-1 의존성맵·verify-all-then-commit·CI=GHA(**설계만; GHA 워크플로우 미구현 — §검증 재기준선**)·RES-12 폴트인젝션. 적대적 검증 + 팀 피드백 2건(tombstone 순서·indexStats 경계) 반영. _ID: RES-12(복원력 테스트)._
- [x] Code Generation — **완료·승인 (2026-06-16)**. `construction/plans/u1-ingestion-code-generation-plan.md` 17단계 전부 완료. `ingestion/` 코드·테스트·배포 스캐폴드·코드 요약 생성 및 검증(`pytest` **23 passed**, `ruff` pass, `uv.lock` 생성) 완료. ⚠️ **PBT-08 P1(디덥 멱등) 속성 테스트 누락**(예시 테스트만 존재); Dockerfile 베이스 태그 핀(sha256 미적용·SEC-10).

**U2 Discovery** (Track 3 @kyjness, mock 선행 → U5):
- [x] Functional Design — **완료·승인 (2026-06-16)**. `construction/u2-discovery/functional-design/`(domain-entities·business-logic-model·business-rules). §4 답변 전부 A: **Q2=A RRF·PaperId 디덥**·**Q3=A baseline 랭킹·relevance 비-raw**·**Q4=A 기권 vs 빈결과 구분(빈 성공 금지)**·Q5=A 검색 인증 필수·Q6=A 2단계 저하·Q7=A NFC·다국어·Q10=A N=20·Q11=A 비차단 이벤트. **INV-1 단일 근거화 게이트(U2 enforce 미호출, U6 단일 권위)**·INV-2 SEC-9 비노출·INV-3 fail-closed·PBT-02/03/07/09. cross-lingual(TD-3 한국어 질의)·capability 어댑터 seam(VectorStoreAdapter·LexicalIndexAdapter·LlmGatewayAdapter) mock-first.
- [x] NFR Requirements — **완료·승인 (2026-06-16)**. `construction/u2-discovery/nfr-requirements/`(nfr-requirements·tech-stack-decisions). **[전역 계승]**: Python·Cohere `search_query`·OpenSearch·Hypothesis·NFR-C1 $1600. **U2 고유**: opensearch-py+**앱 레벨 RRF**+PaperId 디덥·Bedrock 질의 임베딩(검색당 1회)·**임베딩 캐시(TTL)**. **⏳ FastAPI = app-shell 소유자(@ELSAPHABA) 합의 전제(잠정, backend-shared)**. NFR-P1 예산 분해(U2 단계+U6 근거화 별도)·임베딩장애→lexical 폴백/인덱스장애→fail-closed·QT-2 한국어 평가셋.
- [x] NFR Design — **완료·승인 (2026-06-16)**. `construction/u2-discovery/nfr-design/`(nfr-design-patterns·logical-components). 동기 **fail-fast+폴백**(재시도 최소)·**의존성별 서킷**(임베딩→lexical/인덱스→fail-closed)·비용 degradeMode≠장애 서킷·임베딩 **read-through 캐시(TTL)**·**k-NN∥BM25 병렬 RRF**·stateless 수평확장·SEC 계층 분리 방어심층·CI=GHA(**설계만; 워크플로우 미구현**)·RES-12 폴트인젝션.
- [x] Code Generation (mock-first) — **완료 (2026-06-16)**. `backend/modules/discovery/`(pyproject·테스트). **31 passed(api extra)/29+1 skip · ruff clean.** 도메인 6컴포넌트(validator·expander·retriever[RRF·PaperId 디덥]·ranker[N=20]·grounding_adapter·assembler) + orchestrator(plan_and_retrieve/finalize 분리, **INV-1 enforce 미호출**) + `api/gateway_seam`(단일 enforce invocation=게이트웨이 대역) + mock 어댑터/스텁(KO↔EN cross-lingual+QT-2 픽스처) + thin FastAPI 라우터. PBT-02/03/07/09·RES-12 폴트인젝션 테스트. (마운트·근거화는 후속 PR에서 해소 — 아래 real 어댑터 항목 참조.)
- [x] Code Generation (real 어댑터) — **완료·로컬 검증 (2026-06-17, 브랜치 `feature/u2-v2`, 크리티컬 패스 ⑥, 리뷰 게이트)**. `backend/modules/discovery/adapters/`: **BedrockCohereQueryEmbedder**(reader=search_query·dim 검증·실패 시 EmbeddingUnavailable→lexical 폴백), **OpenSearchVectorStoreAdapter**(k-NN cosine)·**OpenSearchLexicalIndexAdapter**(BM25) — U1 writer 인덱스(`docsuri-corpus-v1`) 동일공간 read, hit→`IndexRecord` 역직렬화(SSOT), 실패 시 **IndexUnavailable fail-closed**(INV-3), **EventBridgeEventPublisher**(논블로킹 SearchExecuted→U4). `real_wiring.build_real_orchestrator`(MR-4 계약 불변 스왑)·`scripts/seed_local_opensearch`·pyproject `real` extra(opensearch-py/boto3 lazy). **검증: `pytest` 43 passed(신규 단위 11)+1 skip·ruff clean; docker 라이브 OpenSearch 통합 3 passed(k-NN·BM25·하이브리드 디덥); app-shell 엔드투엔드 200·실 카드 반환(Bedrock 부재 시 graceful degrade).** **app-shell 마운트 토글**(`backend/wiring.py::_mount_discovery`): env(`DOCSURI_OPENSEARCH_ENDPOINT`+`DOCSURI_BEDROCK_MODEL_ID`) 있으면 real, 없으면 mock — 실 근거화 hook은 양 모드 공통(INV-1). **⏳ 의존성 플래그**: 프로덕션 실행은 공유 인프라(OpenSearch 클러스터·Bedrock 접근·이벤트 버스 = U1 보류 인프라 + 시스템 횡단) 필요(env로 분리). **⚠️ 조율존(`backend/wiring.py`) 변경 = @ELSAPHABA 사인오프 필요.**
**U3 Accounts** (Track 2):
- [x] Functional Design — **완료·승인 (2026-06-16)**. `construction/u3-accounts/functional-design/`(domain-entities·business-logic-model·business-rules). 비밀번호 최소 10자 복잡도+로컬 블랙리스트(Q1=B), Argon2id KDF(Q2=A), Sliding 2h+절대 30d 세션(Q3=B), 지수 백오프+10회 CAPTCHA(Q4=B), 이메일 가입 링크 인증 PENDING/ACTIVE(Q5=B), Stateless 인가 결정(Q6=A), 시딩 관리자+TOTP MFA(Q7=B) 확정.
- [x] NFR Requirements — **완료·승인 (2026-06-16)**. `construction/u3-accounts/nfr-requirements/`(nfr-requirements·tech-stack-decisions). 세션 P50<5ms/P99<20ms(Q1=A), argon2-cffi(Q2=A), Multi-AZ 고가용 세션(Q3=A), RDS PostgreSQL+ElastiCache Redis(Q4=A), Google reCAPTCHA v3(Q5=B), Amazon SES(Q6=A) 확정.
- [x] NFR Design — **완료·승인 (2026-06-16)**. `construction/u3-accounts/nfr-design/`(nfr-design-patterns·logical-components). Redis 장애 시 Fail-Closed(Q1=A), reCAPTCHA Fail-Closed 및 SES PENDING 소프트폴백(Q2=B/A), PostgreSQL(10/20)+Redis(50) 커넥션풀(Q3=A), ECS 환경변수 주입 시크릿(Q4=A), 프런트 Origin CORS 명시 바인딩(Q5=A) 확정.
- [x] Infrastructure Design — **완료·승인 (2026-06-16)**. `construction/u3-accounts/infrastructure-design/`(infrastructure-design·deployment-architecture). Fargate 최소 사양(Q1=B), db.t4g.small Multi-AZ(Q2=B), cache.t4g.micro 1+1 Multi-AZ(Q3=B), NAT Gateway 배제 및 ECS Fargate 퍼블릭 서브넷 배치, RDS/Redis 고립 서브넷 배치(Q4=A), SES 도메인 인증(Q5=B) 확정.
- [x] Code Generation — **완료·③ 정정 (2026-06-17)**. _2026-06-16 재기준선 강등 결함은 ③에서 전량 해소: BR-A4 무잠금(자동 LOCKED 제거·백오프+CAPTCHA만)·SSOT 포크 제거(`docsuri_shared` 소비·`AccountCreated` model_dump·snake_case ObservabilityHub)·BR-A7 실 TOTP MFA+시딩 관리자(ADMIN 도달). 커밋 `bbac74f`·`f835a26`·`9b390b9`._ 원 강등 기록(2026-06-16): `construction/plans/u3-accounts-code-generation-plan.md` 17단계를 구현했으나 검증 결과 결함 확인: ⚠️ **BR-A4 위반**(`auth.py` 10회 실패 시 `status=LOCKED` → 무잠금 anti-DoS 규칙 직접 위반); **BR-A7 미구현**(TOTP MFA·시딩 관리자 없음 → ADMIN 도달 불가, `mfa_verified` 하드코딩 False); **SSOT 포크**(`docsuri_shared` 미소비·DTO 자체 재정의·`AccountCreated` raw dict·ObservabilityHub camelCase 오호출); 문서화된 `pytest` 명령 수집 실패(hypothesis·pytest-asyncio 누락); accounts 레인 ruff 132건(modules 제외 설정에 은폐). 의존성 주입 시 15 passed.

**U4 Library** (Track 2 — U3 다음, **Track 2 최종 유닛**):
- [x] Functional Design — **완료 (2026-06-17)**. `construction/u4-library/functional-design/`(domain-entities·business-logic-model·business-rules). 3 소유자 비공개 서브도메인(저장검색 US-L1/FR-8·라이브러리 US-L2/FR-9·이력 US-L3/FR-10). 결정 **D1~D12(권장 기본값 — 리뷰 게이트 override 가능)**: 저장검색 정규화 dedup+정원 200(BR-L1/L2)·라이브러리 `(owner,arxivId)` 멱등+정원 1000+meta 스냅샷(BR-L3/L4/L5)·이력 at-least-once `dedupe_key` 멱등+롤링 500 보존(BR-L6/L7)·키셋 커서 페이지(기본20/최대100, BR-L8)·**rerun=게이트웨이-프런티드(INV-L2 백도어 차단)**·SEC-8 **U3.AuthorizationGuard 위임**→cross-owner 일반화 404(SEC-9/INV-L4). **docsuri_shared DTO SSOT 재사용(포크 금지)**.
- [x] NFR Requirements — **완료 (2026-06-17)**. `construction/u4-library/nfr-requirements/`. [전역/U3 계승]: Python·FastAPI(CG-1)·RDS PostgreSQL·SQLAlchemy·Hypothesis·**NFR-C1 신규 비용 0(CRUD only)**. U4 고유: 포트 리포(InMemory 기본 mock-first + SQL 스캐폴드 + DDL)·base64 키셋 커서·**NFR-R2 가용성 격리(meta 스냅샷)**·QT-4 멱등.
- [x] NFR Design — **완료 (2026-06-17)**. `construction/u4-library/nfr-design/`. owner-scoping 백스톱(INV-L1)·fail-closed authz→404(INV-L4)·멱등 upsert+이벤트 멱등 소비(INV-L3)·롤링 보존 prune·정원 가드·키셋 페이지·감사 sink(SEC-13)·mock-first 포트 스왑. CI=GHA는 **deferred(재기준선: CI 전무)**.
- [x] Infrastructure Design — **완료 (2026-06-17)**. `construction/u4-library/infrastructure-design/`. **U3 인프라 계승**(동일 ECS Fargate 배포①·동일 RDS PostgreSQL); 신규 테이블 `saved_searches`/`library_items`/`search_history`(+ DDL `backend/modules/library/migrations/001`); 신규 관리형 서비스·비용 0; 이력 소비자=공유 이벤트버스(future U6/EventBridge).
- [x] Code Generation — **완료·검증 (2026-06-17)**. `backend/modules/library/`(models·schemas[docsuri_shared 재사용]·validation·ports·repository[memory+sql]·services×3·gateway 스텁·history_consumer·controller[3 라우터]·audit·migration). app-shell **`_mount_library` 마운트(mock-first, 무 DB)**. **검증: `pytest` 64 passed(library 41 + accounts 15 + app-shell 8)·`ruff` clean.** 적대적 설계 검증 18건(0 blocking)→문서 정합 반영. ⚠️ `shared/dtos/library.schema.json` PROVISIONAL→정제 스펙은 별도 shared/ PR(Track3 사인오프) 대기(코드는 로컬 검증으로 무관하게 정상).
- **→ Track 2 (U3 Accounts → U4 Library) 레인 완료.**
- [x] U6 통합·U2 real 어댑터 — **완료 (2026-06-17, ④·⑥; §크리티컬 패스 종결 참조)**

**U5 Frontend** (Track 3 @kyjness, mock-first → U2/U3/U4 DTO 계약):
- [x] Functional Design — **완료·승인 (2026-06-16)**. `construction/u5-frontend/functional-design/`(domain-entities·business-logic-model·business-rules·frontend-components). **히어로 슬라이스 스코프**(가입→로그인→검색→근거화 결과 + 상태UX; 라이브러리/이력은 계약만·후속 패스). 9컴포넌트(AppShell·PhoneMockupFrame·HeroLanding·Signup/LoginForm·SearchScreen·ResultList·ResultCard·StateView·ApiClient). 핵심: SearchResponse 4분기 상태머신(기권≠빈결과 구분)·ResultCard 7필드만(relevance=U2 표시값, raw 차단 SEC-9)·전역스토어 없음·DTO 파생 mock+transport seam(real 전환=설정 교체)·BR-U5-1~22(입력검증·XSS·SEC-12 세션·접근성). 개발지침↔aidlc 충돌 점검: PWA·오프라인 over-scope 제거. **⏳ 기술 스택(TS/SSR·타입 생성)은 NFR Requirements §5-D.**
- [x] NFR Requirements — **완료·승인 (2026-06-16)**. `construction/u5-frontend/nfr-requirements/`(nfr-requirements·tech-stack-decisions). **스택(§5-D)**: Next.js(React App Router SSR·신규 선택)·TS+JSON Schema→TS 생성(드리프트 0)·ApiClient transport-seam(전역 서버상태 라이브러리 없음)·CSS Modules·Vitest+Testing Library/Playwright/DTO 계약 테스트·SSR httpOnly 쿠키 포워딩·pnpm 독립 배포 ④. **U5 LLM 직접호출 없음 → NFR-C1 비용 기여 0**. 오프라인·PWA 제외 확정. 정량 SLO·호스팅·외부 APM은 후속.
- [x] NFR Design — **완료·승인 (2026-06-16)**. `construction/u5-frontend/nfr-design/`(nfr-design-patterns·logical-components). 패턴: 차등 재시도(멱등 GET만)·SSR 실패=완성 페이지·2계층 에러 바운더리·저하 흐름·서버/클라 컴포넌트 경계·캐싱(정적 장기/검색·세션 no-store)·**server-only 호출 경계(토큰 클라 유출 0)**·CSP frame-ancestors self·출력 무해화·stateless SSR 수평확장. 논리 컴포넌트 LC-1~9 + FD 9컴포넌트 매핑. 호스팅·정량 SLO·구체 CSP는 후속(Infra).
- [x] Code Generation (mock-first) — **Part 2 생성 완료·검증 (2026-06-16, 리뷰 게이트)**. 코드 `frontend/`(Next.js App Router·TS·CSS Modules). 16단계 전부. **검증: `tsc --noEmit` 0 errors · `vitest` 32 passed(7 files) · `next build` 성공(First Load JS ~113kB).** 히어로 슬라이스(US-H1·US-D7 + US-D1/D4·A1/A2 기여; US-L* 시그니처 stub만). ApiClient transport seam(MockTransport·real=HttpTransport 설정 교체)·server-only 토큰 경계·SEC-9 7필드·차등 재시도·2계층 에러 바운더리·CSP. 요약 `construction/u5-frontend/code/README.md`. **⚠️ TypeGen 플래그**: SSOT 스키마 루트리스/무타입 한계로 자동 codegen 대신 큐레이트 타입+드리프트검토(`pnpm gen:types`→`types/.schema-raw/`) 채택. **[2026-06-17: 아래 production 패스로 대체·머지됨.]**
- [x] Code Generation (production 패스) — **완료·로컬 검증 (2026-06-17, 브랜치 `feature/u5-v2`, 리뷰 게이트)**. 계획서 `construction/plans/u5-frontend-production-pass-plan.md`(14단계 전부). **스코프: 풀 기능 ①②③**(히어로 + 라이브러리/저장검색/이력; 인프라/CD ④는 공통 인프라 단계로 분리). **P1 계약 정렬**: 프런트 경로를 머지된 실 백엔드로(`/search`→`/api/search`·`/accounts/*`→`/auth/*`); **login 계약 정정**(실 login=쿠키만+`{status,message}`, `ApiClient.login()`→`Promise<void>`, 세션은 `GET /auth/session`); MFA=범위 밖(graceful); 생성타입 드리프트 갱신(라이브러리 DTO 전수 추가). **P2 실 transport(BFF 패턴)**: `app/bff/[...path]` catch-all(서버, `DOCSURI_GATEWAY_URL`→`HttpTransport` 쿠키 포워딩+Set-Cookie 릴레이, 없으면 mock)·클라 `RouteHandlerTransport`(`/bff/*` 동일출처)·`getApiClient` `NEXT_PUBLIC_DOCSURI_REAL_API` 분기·`server-only` 클라 미유출·호출처 5곳 교체. **P3 화면(US-L1/L2/L3)**: ApiClient stub 7개→실구현+rerun/clear, `/library`·`/library/saved`·`/library/history`(커서 페이지·rerun 인라인·담기/저장/삭제/비우기), 공용 `usePaginatedList`·`OutcomeView`·`LibraryTabs`·`cardFromMeta`(relevance 제거 SEC-9), 진입점(AppHeader 내비·ResultCard 담기·SearchScreen 검색저장). **검증: `tsc` 0 · `vitest` 48 passed(9 files; 신규 apiLibrary·libraryScreens + contract 라이브러리 계약) · `next lint` clean · `next build` 성공(라우트 10, `/bff/[...path]` 동적).** 적대적 자기검토 반영(SEC-9/8·커서 경계·login 계약·server-only). **⚠️ 의존성 플래그(U5 외부)**: 게이트웨이 세션쿠키→`request.state.principal` 미주입 → `/library/*`·`/api/search` 실 백엔드 401(fail-closed) = `backend/` 조율존 + 시스템 인프라 단계; reCAPTCHA 토큰 미전송(사이트키 필요); 인프라/CD/호스팅·구체 CSP·정량 SLO=공통 인프라 단계. **[2026-06-17 갱신: PR #63 머지(`86404d1`)·HTTPS 프로덕션 배포(`d1740b0`, Fargate+ALB+CloudFront @ docsuri.org)·BFF 빌드 복구(`344172e`); ⑤ 종결. 게이트웨이 principal 주입(`568677c`)으로 `/library/*`·`/api/search` 401 갭 해소.]**

**U6 Reliability/Ops** (데이터 및 탐지 파이프라인 우선):
- [x] Code Generation — **완료 (2026-06-16)**. `construction/plans/u6-reliability-ops-code-generation-plan.md` 25단계 전부 완료. `ops/` 패키지와 `backend/middleware/` seam 생성. 구현 범위: ObservabilityHub, CostGuardCircuitBreaker, GroundingEnforcementHook, RES-11 a/b/c 탐지기, IncidentEventPublisher, OpsDashboardService, HealthCheckService, ReliabilityEvalProbe, CLI/worker. 검증: `ops/.venv`에서 U6 범위 `pytest ops\tests backend\tests\test_u6_middleware.py` 31 passed, U6 범위 `ruff check ops backend\middleware backend\tests\test_u6_middleware.py` passed, shared contract import 및 CLI smoke passed. 명시 통합 테스트 `pytest ops\tests backend\tests\test_u6_middleware.py tests`는 46 passed. 루트 기본 `pytest`는 기존 `tests/accounts` 15 passed. 루트 `ruff check .`는 기존 `tests/accounts` unused import 9건(F401)으로 실패하여 U6 외 잔여 정리 필요. **[2026-06-17 갱신(④): `create_app` 게이트웨이 설치 + discovery 시임 실 `GroundingEnforcementHook` 주입으로 라이브 경로 연결(`ba4a62e`); PR#45 크로스리뷰 반영(`b6bb92d`); ops CI 레인(`7edd316`); CloudWatch EventStore 어댑터·프로덕션 자동 선택(`8b54b62`). F401 9건은 §크리티컬 패스 종결 잔여 항목으로 추적.]**

**U7 Summarization** (요약/번역 — 코어 U1~U6 완료 후 편입 유닛, 단일 트랙·**실배포 기준 real-first 구현**):
- [x] Functional Design — **완료·승인 (2026-06-18, 브랜치 `feature/u7-v2`·PR #115)**. 계획서 `construction/plans/u7-summarization-functional-design-plan.md`(명확화 질문 **17문** 전수 답변: **A 14·B 1[Q2 노이즈 범위 한정]·X 2[Q10/Q11 real-first]**). 산출물 `construction/u7-summarization/functional-design/`(domain-entities·business-logic-model·business-rules — 도메인 엔티티·9 컴포넌트 파이프라인·BR-S1~S14·PBT-S1~S5·추적성 미커버 0·설계입력 §2~§12 흡수 맵). **핵심 결정**: Q4(U7 고유 결정적 근거화 게이트 — frozen `enforce` 검색형상 미재사용·"단일 권위=U6"는 검색 한정 해석)·Q6(`split_sections` 부재→U7 섹션 도출+span)·Q12(버퍼-검증-스트리밍)·**Q10/Q11 real-first(포트 유지·첫 구현부터 실 Bedrock/S3+Redis·mock 대역 없음)**. **앱 코드 미생성.** _승인 완료(2026-06-18)._
- [x] NFR Requirements — **완료·승인 (2026-06-19)**. 계획서 15문 전수 A(Q14는 A+명시: **Production Mock Adapter 미구현·단위 테스트 Fixture/Stub 허용**). 산출물 `construction/u7-summarization/nfr-requirements/`(nfr-requirements·tech-stack-decisions). **바인딩**: 모델=Sonnet 4.6 요약/Haiku 4.5 번역(TD-S3)·Bedrock 스트리밍(TD-S4)·스토어 S3+Redis(TD-S5)·개인 용어집=**RDS PostgreSQL**(TD-S6)·섹션 도출=정규식·휴리스틱(TD-S7)·**비동기 잡=fast-follow(v1 동기+토큰 캡, TD-S9)**·**real-first 테스트(TD-S12)**.
- [x] NFR Design — **완료·승인 (2026-06-19)**. 계획서 10문 전수 A. 산출물 `construction/u7-summarization/nfr-design/`(nfr-design-patterns·logical-components). **패턴**: Bedrock 격리(타임아웃+1재시도+서킷→기권)·근거화 1회 재시도·**저하 3계층 구분**(비용 degradeMode≠의존성 서킷≠소스 폴백)·캐시 우선 read/write-through·**생성-버퍼-검증-점진렌더**(구조화 JSON은 완성 후 근거화)·stateless+공유 외부 상태·보안 방어심층(인젝션·개인 용어집 owner 격리)·CI real-first(단위 Fixture/Stub 항상+통합 실 의존성 별도 게이트)·RES-12 폴트 인젝션. 논리 컴포넌트 토폴로지(FD 9↔논리 매핑·기존 인프라 재사용·신규 관리형 0). 앱 코드 미생성. _승인 완료(2026-06-19)._
- [x] Infrastructure Design — **완료·승인 (2026-06-19)**. 계획서 9문 전수 A. 산출물 `construction/u7-summarization/infrastructure-design/`(infrastructure-design·deployment-architecture). **신규 관리형 서비스 0**(전부 기존 자산 재사용): 컴퓨트=기존 ECS Fargate 모듈·S3 `summaries/` 프리픽스·Redis `sum:` 키스페이스+TTL·RDS `user_glossary` 테이블(마이그레이션)·Bedrock IAM(모델 ARN 스코프)·CloudWatch/Budget 비용 라인·CI 통합 게이트 레인. 비동기 잡 v1 미프로비저닝. 증분 비용≈Bedrock 토큰(가변). **조율 존**(task role·CI·IaC·마운트)=@ELSAPHABA/Infra. 앱 코드 미생성. _승인 완료(2026-06-19)._
- [x] Code Generation — **Part 1·2 완료·검증 (2026-06-19, 브랜치 `feature/u7-v2`·PR #115)**. 계획서 18단계 전부 [x]. 코드 `backend/modules/summarization/`(src-layout, real-first): 도메인 9컴포넌트(models·refiner·source_selector·cache_key·length_router·glossary·grounding·assembler·orchestrator)·실 어댑터 단일본(bedrock_llm 스트리밍·s3_redis_store·s3_full_text·rds_glossary)·api(router `/api/summarize`·gateway_seam)·prompts(본문 격리)·real_wiring·`migrations/001_create_user_glossary.sql`. **검증: `pytest` 29 passed + 1 skip(통합 self-skip)·`ruff` clean.** Q4 U7 고유 결정적 근거화·Q5 버퍼-검증·저하 3계층·Q8 후치환(한국어 조사 안전)·real-first(Production Mock Adapter 없음·테스트 Fixture/Stub). **⚠️ 마운트=조율 존**: `backend/wiring.py` 미변경(쉘 테스트 보호) — mounter 스니펫을 `code/README.md`에 사인오프-레디로 제시. 인프라 증분(IAM·마이그레이션·CI)=@Infra. _승인 완료(2026-06-19)._
- [x] Build & Test — **완료 (2026-06-19)**. 산출물 `construction/u7-summarization/build-and-test/`(build-instructions·unit-test·integration-test·security-test·build-and-test-summary). **검증: `pytest` 29 passed + 1 skip(통합 게이트 self-skip)·`ruff` clean·임포트 스모크 OK.** 통합 5 시나리오 정의(게이트 레인 전용·real-first). 성능=N/A(NFR-P2 온디맨드). **U7 CONSTRUCTION 종료.** Operations 전 last-mile(프레임워크 밖): app-shell 마운트(@ELSAPHABA)·인프라 증분(@Infra)·`shared/dtos/summarization` 승격·비동기 잡 fast-follow.

**U8 Citation Graph** (인용 그래프/각주 트리 — 2026-06-19 편입 유닛, FE 구현 제외 API 모듈):
- [~] Functional Design — **계획·질문 게이트 작성 완료, 답변 대기 (2026-06-19)**. 계획서 `construction/plans/u8-citation-graph-functional-design-plan.md` 작성. Q1~Q12는 API 응답 union, unresolved 노출, 중복/순환 folding, 2-hop lazy-load, 50노드 truncation, 정렬, 수동 새로고침, U4 저장 메타 adapter, canonical id 우선순위, U6 관측 이벤트, QT-6 PBT 범위, 구현 전략을 다룸. **FD 산출물·앱 코드·FE 미생성.** 기술 스택(Semantic Scholar/OpenAlex, 캐시/스토어, TTL 수치, API runtime, CI 통합 테스트)은 Functional Design 승인 후 NFR Requirements에서 질문.

**공통 후속 단계** (per-unit 또는 횡단):
- [x] 병렬 개발 조율 (2026-06-16 반영) — `shared/` 공용 규약 선행 작성 및 3개 독립 트랙 병렬 진행 확정
- [x] `shared/` 규약 작성 (vector-spec·DTOs·events·ports) — **완료 (2026-06-16)**. `construction/shared/`(5문서). vector-spec 🔒FROZEN(Cohere 1024·코사인·input_type 비대칭·IndexRecord); DTOs/events/ports SSOT 정합·적대적 검증(ship); **63 tests pass·드리프트 스크립트(`tools/generate.py --check`) 동작**. **3 트랙 unblocked.** ⚠️ **드리프트 가드는 수동 스크립트일 뿐 CI 미연결**(`.github/workflows/` 부재); **U3 accounts는 docsuri_shared 미소비(SSOT 포크)** — U1·U2만 실소비.
- [x] U1 NFR Design 승인 (2026-06-16)
- [x] Infrastructure Design — **완료 (2026-06-17, 시스템 전역)**. `construction/infrastructure-design/infrastructure-design.md`(`ac21ae2`) + AWS CDK 5 스택(Network·Search·Compute·Ingestion·Frontend, `ddf8858`). AWS 자원·리전/AZ 토폴로지(RES-2, 서울 단일리전 멀티 AZ)·오토스케일링/쿼터(RES-8) 반영.
- [x] Code Generation — **완료**. 전 유닛(U1~U6) 코드 + 시스템 IaC/CD(`db1b187`)·프로덕션 실연결(`01fd553`·`5f7acce`)·SES(`50da0d5`·`0437b40`).
- [x] 빌드 & 테스트 — **완료·승인 (2026-06-16)**. `construction/build-and-test/`에 build, unit, integration, performance, contract, security, summary 문서 생성. 로컬 U1 검증 결과(`pytest` **23 passed**, `ruff` pass, CLI smoke `NEW`) 반영. ⚠️ **자동 CI 게이트 없음**(수동 실행만; §검증 재기준선).

### 🟡 OPERATIONS 단계
- [~] Operations — **placeholder 확인 완료 (2026-06-16)**. `operations/operations-placeholder.md` 생성. 현재 룰셋상 배포·모니터링·운영 런북 실행은 future scope이며, 워크플로우는 Build and Test 이후 종료.
- [x] **Operations 하드닝 패스 (2026-06-18, PR #79·#84 → develop, 라이브 배포·검증 완료)** — CONSTRUCTION 종료 후 프로덕션 운영 첫 단계. 산출:
  - [x] **운영 런북** `operations/runbook.md` — 시스템 맵·함정(RETAIN 3종·ALB `/healthz` 서킷브레이커·SSO)·비용가드 강등표·복구절차·SLO 3개.
  - [x] **알림 마지막 1마일** (코드에 존재하나 사람에게 미연결이던 갭): G3 `CLOUDWATCH_NAMESPACE` env로 prod 관측 활성·G2 SES 토픽 ops 구독·G4 CloudWatch 알람(5xx·p95)+G1 AWS Budget($1280) → `OpsAlerts` 토픽/ops 메일. 전부 `compute_stack.py` (synth 검증).
  - [x] **검증(라이브, 2026-06-18, 계정 028317349537)**: `cdk deploy Docsuri-Compute -c ops_alert_email=corpseonthemission@icloud.com` → API 롤링 생존(/healthz 200) · SNS 구독 2개 confirm · **테스트 알람(set-alarm-state ALARM)→이메일 수신 확인** · **RDS 스냅샷→`docsuri-restore-test` 복원 available(DBName=docsuri·pg16.13)→폐기**. Budget는 직접 이메일 구독이라 구성 완료(실 발화는 $1280 도달 시).
  - [x] **G3 IAM 보강** (PR #84): task role에 `cloudwatch:PutMetricData`(namespace 스코프)+`logs:*` + `/docsuri/ops` 로그그룹 retention 30일 선생성. `CLOUDWATCH_NAMESPACE` env만으론 부족(권한 부재→AccessDenied 무성 실패)했던 것 보강.
  - [ ] **G3 잔여(U6 후속)**: 모듈 서비스가 `NoopObservabilityHub`에 emit(`discovery/real_wiring.py:84`·`mocks/wiring.py:56`, "until U6 exposes process-wide singletons") → 정상 트래픽 앱 메트릭이 진짜 hub(→CloudWatch)에 미도달. 게이트웨이 에러 경로만 진짜 hub. 수정=`backend/wiring.py`+모듈 팩토리에 `app.state.observability` 주입(ops 범위 밖). **알림/페이징은 네이티브 ALB 메트릭이라 무관하게 작동.**
  - 천장(의도적 미구현): 앱 내부 cost guard의 per-incident SNS publisher — Budget가 빌링 레벨에서 대체.

## 비고
- 이번 사이클은 클린 재시작이다. 폐기된 사이클 1(U1·U2·U4 데모)은 AWS Bedrock(Claude Haiku), Amazon Comprehend, S3 Vectors 기반 Bedrock Knowledge Base, Amplify 호스팅, Python 백엔드, Next.js 프런트엔드를 사용했다. 그중 어느 선택도 기본 계승하지 않으며 선행 사례(prior art)로만 참조한다.
- 브랜치: `develop` (4 트랙 PR + 후속 크리티컬 패스 ①~⑦ PR 전부 머지 완료). **2026-06-18 기준: CONSTRUCTION 코드·인프라 종결·AWS 프로덕션 배포 완료(§크리티컬 패스 종결). 잔여 = 문서 정합·루트 `tests/` 린트 사각(F401 9건)·Operations 런북 결정.**
