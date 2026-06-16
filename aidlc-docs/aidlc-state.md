# AI-DLC 상태 추적 (State Tracking)

## 프로젝트 정보
- **프로젝트명**: DocSuri (연구 지원 애플리케이션)
- **프로젝트 유형**: Greenfield(그린필드)
- **시작일**: 2026-06-15T04:36:30Z
- **현재 단계**: CONSTRUCTION 진행(유닛별 루프, **프로덕션 직행** U1 — 데모 트랙 폐기). **U1 Functional Design·NFR Requirements 완료·승인(2026-06-16)**; **U1 NFR Design 완료·승인(2026-06-16)**. 병렬화 조율(shared/ 규약 선행 및 3개 병렬 트랙) 반영. **shared/ 공용 규약 작성 완료**(5문서, 3 트랙 unblocked). 다음: **3 트랙 병렬 착수**(Track1 U1 Infra Design·Track2 U3 Accounts FD·Track3 U2 mock FD). U1 설계 일체 develop PR 랜딩. PR #36 머지(INCEPTION→develop). 브랜치 `feature/aidlc-construction-u1`.
- **문서 언어**: 한국어(`aidlc-docs/` 산출물). 업스트림 룰셋(`AGENTS.md`, `.aidlc-rule-details/`)은 영어 유지.

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
- [x] NFR Design — **완료·승인 (2026-06-16)**. `construction/u1-ingestion/nfr-design/`(nfr-design-patterns·logical-components). 버전 단조 tombstone(`current_version` compare-and-set)·indexStats 내부경계+캐시TTL·RES-1 의존성맵·verify-all-then-commit·CI=GHA(CD는 Infra)·RES-12 폴트인젝션. 적대적 검증 + 팀 피드백 2건(tombstone 순서·indexStats 경계) 반영. _ID: RES-12(복원력 테스트)._
- [ ] (이하 U2~U6 Functional Design은 각 유닛 루프 진입 시)

**공통 후속 단계** (per-unit 또는 횡단):
- [x] 병렬 개발 조율 (2026-06-16 반영) — `shared/` 공용 규약 선행 작성 및 3개 독립 트랙 병렬 진행 확정
- [x] `shared/` 규약 작성 (vector-spec·DTOs·events·ports) — **완료 (2026-06-16)**. `construction/shared/`(5문서). vector-spec 🔒FROZEN(Cohere 1024·코사인·input_type 비대칭·IndexRecord); DTOs/events/ports SSOT 정합·적대적 검증(ship). **3 트랙 unblocked.**
- [x] U1 NFR Design 승인 (2026-06-16)
- [ ] Infrastructure Design — **EXECUTE** (AWS 자원·**리전/AZ 토폴로지 RES-2**·오토스케일링/쿼터 RES-8 확정)
- [ ] Code Generation — **EXECUTE** (항상)
- [ ] 빌드 & 테스트 — **EXECUTE** (항상)

### 🟡 OPERATIONS 단계
- [ ] Operations (플레이스홀더)

## 비고
- 이번 사이클은 클린 재시작이다. 폐기된 사이클 1(U1·U2·U4 데모)은 AWS Bedrock(Claude Haiku), Amazon Comprehend, S3 Vectors 기반 Bedrock Knowledge Base, Amplify 호스팅, Python 백엔드, Next.js 프런트엔드를 사용했다. 그중 어느 선택도 기본 계승하지 않으며 선행 사례(prior art)로만 참조한다.
- 브랜치: `feature/aidlc-inception` (레포 리셋 커밋 `1f47ac2` + 모든 인셉션 산출물 번들; `develop`로 단일 통합 PR로 랜딩).
