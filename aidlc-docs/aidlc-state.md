# AI-DLC 상태 추적 (State Tracking)

## 프로젝트 정보
- **프로젝트명**: DocSuri (연구 지원 애플리케이션)
- **프로젝트 유형**: Greenfield(그린필드)
- **시작일**: 2026-06-15T04:36:30Z
- **현재 단계**: CONSTRUCTION 진행(3 트랙 병렬, 유닛별 루프). **develop 통합 머지(2026-06-16)**: U1 Ingestion(Code Generation·Build and Test 완료·승인)·U2 Discovery(mock-first Code Generation)·U3 Accounts(Code Generation) + backend app-shell(**accounts만 실제 마운트; discovery는 매 부팅 graceful-skip — §검증 재기준선 참조**). shared/ 공용 규약 완료. U1 OPERATIONS는 placeholder 확인(현 AI-DLC 룰셋은 Build and Test 이후 실제 Operations 실행 절차 미제공). **U1 프로덕션 배포 미표시**: AWS 토폴로지·IAM/KMS/network·OpenSearch/SQS/control-plane 배포·CI/CD·롤백·운영 런북은 후속 Infrastructure Design/Operations 확장 필요. 다음: 각 유닛 후속 루프(U4~U6·U2 real 어댑터·U5 Frontend).
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
- [x] 사용자 스토리(User Stories) — 계획 승인(PQ1–5=A); Part 2에서 `stories.md`(스토리 **21개**, 6 에픽: Hero 1 + Discovery 7 + Accounts 2 + Library 3 + Ingestion 3 + Reliability 5) + `personas.md`(P1 박지훈, P2, OP) 생성; FR-1..11 전부 커버; **승인 완료**. **적대적 비평 패스 완료(2026-06-15, 7/7 critic)** → requirements/stories 보정 반영.
- [x] Workflow Planning — `execution-plan.md` **승인 완료**. 판정: 리버스 엔지니어링만 SKIP, 그 외 전 단계 EXECUTE.
- [x] Application Design — 완료(리뷰 게이트). `application-design/` 5문서(components·component-methods·services·component-dependency·application-design); 6 유닛(U1~U6); 적대적 3 critic→blocking/major 보정 반영(근거화 단일 권위, SearchExecuted 생산자, SEC-8 단일 결정점, QT-3 소유자, 백도어 차단)
- [x] Units Generation — 완료(리뷰 게이트). `unit-of-work.md`·`unit-of-work-dependency.md`·`unit-of-work-story-map.md`; 6 유닛·4 배포 단위·모노레포·데모 우선 순서; 스토리 21개 전수 매핑·코드 의존 DAG(adversarial 검증 solid)
- [ ] Units Generation — **EXECUTE** (예비 유닛: U1 인제스천, U2 디스커버리 API, U3 계정/인증, U4 검색저장/라이브러리, U5 모바일 웹, U6 신뢰성/운영)

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
- [x] Code Generation (mock-first) — **완료 (2026-06-16)**. `backend/modules/discovery/`(pyproject·테스트). **31 passed(api extra)/29+1 skip · ruff clean.** 도메인 6컴포넌트(validator·expander·retriever[RRF·PaperId 디덥]·ranker[N=20]·grounding_adapter·assembler) + orchestrator(plan_and_retrieve/finalize 분리, **INV-1 enforce 미호출**) + `api/gateway_seam`(단일 enforce invocation=게이트웨이 대역) + mock 어댑터/스텁(KO↔EN cross-lingual+QT-2 픽스처) + thin FastAPI 라우터. PBT-02/03/07/09·RES-12 폴트인젝션 테스트. **⏳ FastAPI/배포·real 어댑터(OpenSearch/Bedrock)·캐시 스토어는 app-shell 합의·Infra 후속.** ⚠️ **app-shell 부팅 시 discovery 미마운트(매 부팅 graceful-skip; 별도 uv 프로젝트 미설치)** — 통합 앱에 `/api/search` 없음. **근거화는 프로덕션에서 `StubGroundingHook`(항상 pass)만 주입 — 실효 enforcement 없음(실 hook은 `feature/track6`에 존재하나 라이브 경로 미주입).** 리뷰 게이트.
**U3 Accounts** (Track 2):
- [x] Functional Design — **완료·승인 (2026-06-16)**. `construction/u3-accounts/functional-design/`(domain-entities·business-logic-model·business-rules). 비밀번호 최소 10자 복잡도+로컬 블랙리스트(Q1=B), Argon2id KDF(Q2=A), Sliding 2h+절대 30d 세션(Q3=B), 지수 백오프+10회 CAPTCHA(Q4=B), 이메일 가입 링크 인증 PENDING/ACTIVE(Q5=B), Stateless 인가 결정(Q6=A), 시딩 관리자+TOTP MFA(Q7=B) 확정.
- [x] NFR Requirements — **완료·승인 (2026-06-16)**. `construction/u3-accounts/nfr-requirements/`(nfr-requirements·tech-stack-decisions). 세션 P50<5ms/P99<20ms(Q1=A), argon2-cffi(Q2=A), Multi-AZ 고가용 세션(Q3=A), RDS PostgreSQL+ElastiCache Redis(Q4=A), Google reCAPTCHA v3(Q5=B), Amazon SES(Q6=A) 확정.
- [x] NFR Design — **완료·승인 (2026-06-16)**. `construction/u3-accounts/nfr-design/`(nfr-design-patterns·logical-components). Redis 장애 시 Fail-Closed(Q1=A), reCAPTCHA Fail-Closed 및 SES PENDING 소프트폴백(Q2=B/A), PostgreSQL(10/20)+Redis(50) 커넥션풀(Q3=A), ECS 환경변수 주입 시크릿(Q4=A), 프런트 Origin CORS 명시 바인딩(Q5=A) 확정.
- [x] Infrastructure Design — **완료·승인 (2026-06-16)**. `construction/u3-accounts/infrastructure-design/`(infrastructure-design·deployment-architecture). Fargate 최소 사양(Q1=B), db.t4g.small Multi-AZ(Q2=B), cache.t4g.micro 1+1 Multi-AZ(Q3=B), NAT Gateway 배제 및 ECS Fargate 퍼블릭 서브넷 배치, RDS/Redis 고립 서브넷 배치(Q4=A), SES 도메인 인증(Q5=B) 확정.
- [~] Code Generation — **부분 완료 (2026-06-16, 재기준선 강등)**. `construction/plans/u3-accounts-code-generation-plan.md` 17단계를 구현했으나 검증 결과 결함 확인: ⚠️ **BR-A4 위반**(`auth.py` 10회 실패 시 `status=LOCKED` → 무잠금 anti-DoS 규칙 직접 위반); **BR-A7 미구현**(TOTP MFA·시딩 관리자 없음 → ADMIN 도달 불가, `mfa_verified` 하드코딩 False); **SSOT 포크**(`docsuri_shared` 미소비·DTO 자체 재정의·`AccountCreated` raw dict·ObservabilityHub camelCase 오호출); 문서화된 `pytest` 명령 수집 실패(hypothesis·pytest-asyncio 누락); accounts 레인 ruff 132건(modules 제외 설정에 은폐). 의존성 주입 시 15 passed.

**U4 Library** (Track 2 — U3 다음, **Track 2 최종 유닛**):
- [x] Functional Design — **완료 (2026-06-17)**. `construction/u4-library/functional-design/`(domain-entities·business-logic-model·business-rules). 3 소유자 비공개 서브도메인(저장검색 US-L1/FR-8·라이브러리 US-L2/FR-9·이력 US-L3/FR-10). 결정 **D1~D12(권장 기본값 — 리뷰 게이트 override 가능)**: 저장검색 정규화 dedup+정원 200(BR-L1/L2)·라이브러리 `(owner,arxivId)` 멱등+정원 1000+meta 스냅샷(BR-L3/L4/L5)·이력 at-least-once `dedupe_key` 멱등+롤링 500 보존(BR-L6/L7)·키셋 커서 페이지(기본20/최대100, BR-L8)·**rerun=게이트웨이-프런티드(INV-L2 백도어 차단)**·SEC-8 **U3.AuthorizationGuard 위임**→cross-owner 일반화 404(SEC-9/INV-L4). **docsuri_shared DTO SSOT 재사용(포크 금지)**.
- [x] NFR Requirements — **완료 (2026-06-17)**. `construction/u4-library/nfr-requirements/`. [전역/U3 계승]: Python·FastAPI(CG-1)·RDS PostgreSQL·SQLAlchemy·Hypothesis·**NFR-C1 신규 비용 0(CRUD only)**. U4 고유: 포트 리포(InMemory 기본 mock-first + SQL 스캐폴드 + DDL)·base64 키셋 커서·**NFR-R2 가용성 격리(meta 스냅샷)**·QT-4 멱등.
- [x] NFR Design — **완료 (2026-06-17)**. `construction/u4-library/nfr-design/`. owner-scoping 백스톱(INV-L1)·fail-closed authz→404(INV-L4)·멱등 upsert+이벤트 멱등 소비(INV-L3)·롤링 보존 prune·정원 가드·키셋 페이지·감사 sink(SEC-13)·mock-first 포트 스왑. CI=GHA는 **deferred(재기준선: CI 전무)**.
- [x] Infrastructure Design — **완료 (2026-06-17)**. `construction/u4-library/infrastructure-design/`. **U3 인프라 계승**(동일 ECS Fargate 배포①·동일 RDS PostgreSQL); 신규 테이블 `saved_searches`/`library_items`/`search_history`(+ DDL `backend/modules/library/migrations/001`); 신규 관리형 서비스·비용 0; 이력 소비자=공유 이벤트버스(future U6/EventBridge).
- [x] Code Generation — **완료·검증 (2026-06-17)**. `backend/modules/library/`(models·schemas[docsuri_shared 재사용]·validation·ports·repository[memory+sql]·services×3·gateway 스텁·history_consumer·controller[3 라우터]·audit·migration). app-shell **`_mount_library` 마운트(mock-first, 무 DB)**. **검증: `pytest` 64 passed(library 41 + accounts 15 + app-shell 8)·`ruff` clean.** 적대적 설계 검증 18건(0 blocking)→문서 정합 반영. ⚠️ `shared/dtos/library.schema.json` PROVISIONAL→정제 스펙은 별도 shared/ PR(Track3 사인오프) 대기(코드는 로컬 검증으로 무관하게 정상).
- **→ Track 2 (U3 Accounts → U4 Library) 레인 완료.**
- [ ] (U5 Frontend·U6 통합·U2 real 어댑터는 후속 트랙/루프)

**공통 후속 단계** (per-unit 또는 횡단):
- [x] 병렬 개발 조율 (2026-06-16 반영) — `shared/` 공용 규약 선행 작성 및 3개 독립 트랙 병렬 진행 확정
- [x] `shared/` 규약 작성 (vector-spec·DTOs·events·ports) — **완료 (2026-06-16)**. `construction/shared/`(5문서). vector-spec 🔒FROZEN(Cohere 1024·코사인·input_type 비대칭·IndexRecord); DTOs/events/ports SSOT 정합·적대적 검증(ship); **63 tests pass·드리프트 스크립트(`tools/generate.py --check`) 동작**. **3 트랙 unblocked.** ⚠️ **드리프트 가드는 수동 스크립트일 뿐 CI 미연결**(`.github/workflows/` 부재); **U3 accounts는 docsuri_shared 미소비(SSOT 포크)** — U1·U2만 실소비.
- [x] U1 NFR Design 승인 (2026-06-16)
- [ ] Infrastructure Design — **EXECUTE** (AWS 자원·**리전/AZ 토폴로지 RES-2**·오토스케일링/쿼터 RES-8 확정)
- [ ] Code Generation — **EXECUTE** (항상)
- [x] 빌드 & 테스트 — **완료·승인 (2026-06-16)**. `construction/build-and-test/`에 build, unit, integration, performance, contract, security, summary 문서 생성. 로컬 U1 검증 결과(`pytest` **23 passed**, `ruff` pass, CLI smoke `NEW`) 반영. ⚠️ **자동 CI 게이트 없음**(수동 실행만; §검증 재기준선).

### 🟡 OPERATIONS 단계
- [~] Operations — **placeholder 확인 완료 (2026-06-16)**. `operations/operations-placeholder.md` 생성. 현재 룰셋상 배포·모니터링·운영 런북 실행은 future scope이며, 워크플로우는 Build and Test 이후 종료.

## 비고
- 이번 사이클은 클린 재시작이다. 폐기된 사이클 1(U1·U2·U4 데모)은 AWS Bedrock(Claude Haiku), Amazon Comprehend, S3 Vectors 기반 Bedrock Knowledge Base, Amplify 호스팅, Python 백엔드, Next.js 프런트엔드를 사용했다. 그중 어느 선택도 기본 계승하지 않으며 선행 사례(prior art)로만 참조한다.
- 브랜치: `develop` (4 트랙 PR 전부 머지 완료; 다음 작업은 후속 유닛 루프 — §검증 재기준선의 크리티컬 패스 참조)
