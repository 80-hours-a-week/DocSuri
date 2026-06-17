# u4-library-nfr-requirements-plan.md — NFR Requirements 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Requirements (유닛별 루프, Track 2 두 번째·최종 유닛) · **유닛**: U4 Library (검색 저장·라이브러리·이력) · **트랙**: Track 2(@revenantonthemission) · **일자**: 2026-06-17
**근거(SSOT)**: `tmp/u4-design-brief.md`(D1~D12 + BR-L1..L10 + INV-L1..L4 + PBT-09), U4 FD 산출물(`construction/u4-library/functional-design/`), `requirements.md`(공통 NFR·확장 규칙), U3 Accounts `nfr-requirements/`(TD-U3-1/3/6 [상속] 템플릿), `construction/shared/dtos.md` §3·§1.1, `shared/events/search-executed.schema.json`, `backend/wiring.py`(마운트 시임)
**목적**: U4 비기능 요구사항(성능·확장성·가용성·신뢰성) 확정 + **기술 스택 상속/선정** 확정. 브리프 §3 D10(영속성 포트)과 §9(컨벤션)을 NFR/스택 결정으로 고정한다.

> **[전역 계승](재결정 아님)**: U1(빌드 #1)이 PIN한 시스템 전역 결정 — **§5: backend 런타임=Python** · **NFR-C1=$1600/월(시스템 전역 상한)** · **신규 서드파티 의존성 0(모노레포 backend)**. 해당 질문엔 `[전역 계승]` 표기.
> **[U3 계승](재결정 아님)**: Track 2 선행 유닛 U3 Accounts가 확정한 결정 — **TD-U3-3 영속성=Amazon RDS(PostgreSQL)** · **TD-U3-5 SQLAlchemy 2.x** · **SEC-8 인가 단일 권위=`AuthorizationGuard`** · **TD-U3-6 PBT=Hypothesis**. 해당 질문엔 `[U3 계승]` 표기.
> **[backend-shared] 조율 존**: 웹 프레임워크(CG-1=FastAPI)·공급망 툴링은 backend 모듈형 모놀리스(app-shell) 공유 결정 — 현 app-shell 소유자(Track 2 @revenantonthemission)가 합의. `[backend-shared]` 표기.
> **(무태그) = U4 고유 결정** — 본 단계에서 새로 정하는 것.

---

## 1. 유닛 컨텍스트 및 목표 (Step 1)

U4 Library는 사용자 **소유자 비공개(owner-private) CRUD** + **검색 이력 이벤트 소비**를 담당하는 동기 API 모듈(배포 ① backend 모놀리스 내, `backend.modules.library`)이다. 세 서브도메인(Saved Searches US-L1/FR-8 · Library US-L2/FR-9 · Search History US-L3/FR-10)으로 구성된다. U3 Accounts와 달리 **게이트웨이 핫패스(요청마다 동기 호출)가 아니므로** 극저지연(NFR-P1 수준) 요구는 없으나, 다음이 U4의 핵심 NFR 동인이다.

- **핵심 NFR 대상**:
  - **가용성 격리(Availability Isolation)**: 라이브러리 카드는 저장된 `LibraryItemMeta` 스냅샷(D5/BR-L5)으로 렌더 — 목록 조회 시 U2/인덱스 재호출 0. 라이브 인덱스 장애와 무관하게 라이브러리/이력 읽기가 동작해야 한다.
  - **데이터 정합성(Consistency)**: 쿼터 강제(BR-L2 200 / BR-L4 1000)의 count-then-insert 경합, 멱등 upsert(BR-L1·L3), 이력 exactly-once 기록(BR-L7·INV-L3)을 트랜잭션·Unique 제약으로 보장.
  - **보안(Security)**: 소유자 스코핑 backstop(INV-L1·SEC-8), fail-closed 인가(INV-L4 → 404/401), 비노출(SEC-9 — 내부 필드 미직렬화), 입력 검증(SEC-5), 감사(SEC-13).
  - **비용 무동인(Cost)**: U4는 직접 LLM/임베딩 비용 동인이 **없다**(CRUD + 영속화). 유일한 비용 경로인 rerun은 `SearchGatewayPort` 경유(D9/INV-L2)로 시스템 게이트(NFR-C1 $1600)에 위임 — 백도어 부재.
  - **기술 스택**: Python 환경 영속성(RDS/SQLAlchemy 상속) + 포트 기반 mock-first 리포지토리(D10) 선정.

- **FD 잠금(브리프 §3·§4)**: D1 정규화·멱등 dedup · D2/D4 쿼터 · D3 라이브러리 멱등 · D5 메타 스냅샷·가용성 격리 · D6 롤링 500 보존 · D7 이력 멱등(dedupe_key) · D8 keyset 커서(limit 20/max 100) · D9 rerun via gateway · D10 포트 영속성(InMemory 기본 + Sql scaffold) · D11 인가 위임·404 일반화 · D12 AuditSink no-op.

---

## 2. NFR Requirements 실행 계획 (Step 2)

> 질문 답변 완료 후, 아래 산출물들을 `aidlc-docs/construction/u4-library/nfr-requirements/` 디렉터리에 작성한다. **§4 답변 전 미생성** 원칙(단, 권장 기본값이 모두 답변되었으므로 작성 가능 상태).

- [x] **nfr-requirements.md** — 성능·확장성·가용성·신뢰성·보안 요건 명세
  - 성능: U4는 게이트웨이 핫패스 아님 → 일반 CRUD 레이턴시 예산(목록/단건) 정의(Q1). 페이지네이션 keyset 안정성(D8/BR-L8).
  - 확장성: owner당 쿼터(저장 200·라이브러리 1000·이력 롤링 500)와 owner 규모(1,000 활성 사용자·사용자당 스토리지 상한) 정의(Q3).
  - 가용성/복원력: 영속성 가용성(RTO/RPO)은 U3 RDS 상속 + **가용성 격리(라이브 인덱스 장애 시에도 라이브러리/이력 동작)** 명세(Q4).
  - 신뢰성: 이력 exactly-once(INV-L3)·멱등 upsert(BR-L1·L3)·fail-closed 인가(INV-L4).
  - 보안: INV-L1 owner-scoping · SEC-8 인가 위임 · SEC-9 비노출 · SEC-5 검증 · SEC-13 감사 · SEC-15 fail-closed.
  - 비용: **NFR-C1 U4 슬라이스 = 0 직접 동인**; rerun만 게이트(`SearchGatewayPort`) 위임으로 일반 검색 1회와 동일 계상.
  - 테스트(QT/PBT): **PBT-09(DTO 라운드트립 — U4 블로킹 PBT, 내부 필드 비누출)** · cursor property(advisory).
- [x] **tech-stack-decisions.md** — U4 기술 스택 및 라이브러리 선정 (ADR 형식: 결정·근거·대안·전환 비용)
  - [전역 계승]: Python 3.12+(Q2) · 신규 의존성 0(Q9).
  - [backend-shared]: FastAPI / CG-1(Q2 결선).
  - [U3 계승]: RDS PostgreSQL(Q4) · SQLAlchemy 2.x(Q5) · AuthorizationGuard 위임(Q6) · Hypothesis(Q9).
  - U4 고유: 포트 기반 리포지토리(InMemory 기본 + Sql scaffold + DDL, Q5) · base64 keyset 커서 코덱(Q7) · `SearchGatewayPort`+`StubSearchGateway` rerun(Q8) · shared DTO/이벤트 SSOT 재사용·`LibraryItemMeta` 내부 검증기 · `AuditSink` no-op · `SearchExecutedEvent` 멱등 소비자.
  - **이미 작성됨**: `construction/u4-library/nfr-requirements/tech-stack-decisions.md`(TD-U4-1..13). 본 계획은 그 결정의 질문 게이트(근거·대안 surface)다.
- [x] **추적성** — NFR/스택 결정 → D1~D12, BR-L1..L10, INV-L1..L4, SEC-5/8/9/13/15, NFR-C1, PBT-09 역추적.

---

## 3. 가정 (Assumptions)

- **AS-1 [전역 계승]**: 백엔드 런타임은 공통 결정(§5)에 따라 **Python 3.12+**를 사용한다 — U4 재논의 아님.
- **AS-2 [U3 계승]**: 프로덕션 영속성은 U3가 확정한 **Amazon RDS(PostgreSQL)**를 상속한다(TD-U3-3). U4는 owner-scoped 테이블 3종(`saved_searches`·`library_items`·`search_history`)을 추가한다.
- **AS-3 [전역 계승]**: U4는 **신규 서드파티 런타임 의존성을 도입하지 않는다.** `fastapi`·`sqlalchemy`·`pydantic`은 `backend/pyproject.toml`에 이미 선언; 커서 코덱·검증·dedupe는 표준 라이브러리(`base64`·`json`·`hashlib`·`unicodedata`·`re`)로 충족.
- **AS-4**: app-shell 마운트는 **mock-first** — `backend/wiring.py::_mount_library`가 `InMemoryUserDataRepository`/`StubSearchGateway`/`InMemoryAuditSink`를 주입하여 **라이브 DB 없이** 마운트되고 테스트가 그린으로 통과한다(D10, discovery mock-first 자세와 동형).
- **AS-5**: 리전/AZ 토폴로지·IaC·CI/CD·배포 타깃·DDL 인덱스 확정·`SqlUserDataRepository` 트랜잭션 격리 수준은 본 단계 밖(NFR Design / Infra Design 산출물이 SSOT). 본 계획은 "스택 종류 + NFR 목표(정책 형태)"를 정한다.
- **AS-6**: 인가는 **U3 `AuthorizationGuard` 단일 권위에 위임**(SEC-8)하며 U4는 별도 가드를 정의하지 않는다(INV-L4 fail-closed). `Principal`/`Action`/`AccountId`/`Decision`은 `backend.modules.accounts`에서 재사용(재정의 금지).

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그로 답변)

> 모든 질문은 **권장 기본값(recommended default)**을 제시하며, 이는 **검토 게이트에서 override 가능**하다(브리프 §3: "recommended defaults; surfaced for user override at the review gate"). 답변은 D1~D12 결정과 정합한다.

### Q1 — U4 CRUD 레이턴시 예산 (Performance)
U4는 게이트웨이 동기 핫패스(U3 SessionVerifier 같은 요청마다-호출)가 **아니다.** 저장/라이브러리/이력의 목록·단건 CRUD 응답 레이턴시 목표(성능 예산)를 어떻게 설정하는가?

A) **(권장) 일반 저지연 (목록 P50 < 50ms, P99 < 200ms; 단건 mutate P50 < 80ms, P99 < 300ms)** — owner-scoped 인덱스 + keyset 페이지네이션(오프셋 아님)으로 most-recent-first 안정 조회. 가용성 격리(저장 스냅샷 렌더)로 외부 호출 0. rerun은 예외(외부 검색 1회 = U2 NFR-P1 종단 예산에 종속).

B) **극저지연 (U3 NFR-P1 수준, P50 < 5ms)** — U4를 인메모리 핫스토어로 강제(과설계 — U4는 게이트가 아님).

C) Other (아래 `[Answer]:` 뒤에 상세 기재).

[Answer]: A. U4는 사용자가 명시적으로 호출하는 일반 CRUD 경로이므로 게이트웨이 수준의 극저지연(NFR-P1)이 불필요하다. **일반 저지연(목록 P50<50ms/P99<200ms, 단건 mutate P50<80ms/P99<300ms)**을 목표로 하고, 이를 위해 (1) 모든 쿼리를 `owner_id`로 구조적 필터링(INV-L1)하며 owner-scoped 인덱스를 둔다, (2) D8 keyset 커서로 오프셋 스캔을 회피한다, (3) 라이브러리 목록은 저장된 `LibraryItemMeta` 스냅샷만 반환해 외부 호출 0(가용성 격리, BR-L5). **rerun**은 `SearchGatewayPort` 경유 외부 검색 1회를 포함하므로 본 예산에서 제외하고 U2 NFR-P1 종단 예산에 종속시킨다.

---

### Q2 — 언어/런타임 및 웹 프레임워크 ([전역 계승] + [backend-shared] / Tech Stack)
U4 모듈의 런타임 언어와 API 웹 프레임워크는 무엇인가?

A) **(권장) Python 3.12+ (전역 상속) + FastAPI `APIRouter` (CG-1, backend-shared)** — `backend.modules.library` 패키지, async 엔드포인트 + `Depends` DI; accounts 모듈과 동형. `fastapi>=0.110`·`pydantic` v2 이미 선언됨.

B) 다른 프레임워크(Flask/Starlette 직접 등) — backend 단일 런타임 공유 결정 위반.

C) Other.

[Answer]: A. **Python 3.12+**는 모듈형 모놀리스 시스템 결정(§5)의 전역 상속이며 재논의 대상이 아니다. 웹 프레임워크는 app-shell이 확정한 **CG-1 = FastAPI**(backend-shared)를 상속한다 — 3개 컨트롤러(SavedSearchController·LibraryController·SearchHistoryController)를 FastAPI `APIRouter`로 구현하고 app-shell `create_app`이 선택적 마운트한다. pydantic v2로 shared DTO 검증·자동 OpenAPI. timezone-aware UTC(`datetime.now(UTC)`) 규약 상속(`datetime.utcnow()` 폐기 회피, §9). → TD-U4-1, TD-U4-2.

---

### Q3 — 쿼터·보존 한도 및 owner 규모 (Scalability)
owner당 쿼터(저장 검색·라이브러리·이력)와 1차 프로덕션 owner 규모를 어떻게 확정하는가?

A) **(권장) 브리프 D2/D4/D6 수치 채택**: 저장 검색 **200/owner**(BR-L2, 초과 → 409) · 라이브러리 **1000/owner**(BR-L4, 초과 → 409) · 이력 **롤링 500/owner**(BR-L6, 초과 시 가장 오래된 것부터 프루닝). 1차 타깃 owner 규모는 U3 상속(최대 ~1,000 활성 사용자).

B) 무제한/별도 수치 — 스토리지·경합 통제 약화.

C) Other.

[Answer]: A. 브리프가 핀한 **저장 검색 200(BR-L2)·라이브러리 1000(BR-L4)·이력 롤링 500(BR-L6)**을 그대로 채택한다. 쿼터 초과(신규 행 생성에 한함; 멱등 재저장/재추가는 카운트하지 않음)는 `QuotaExceededError` → **HTTP 409**. 이력은 record 시점 cap 초과 시 oldest-first 프루닝, `clearHistory`는 owner 전체 삭제. 쿼터 카운트는 owner-scoped 저장소 카운트(INV-L1)에 기반하며, count-then-insert 경합은 트랜잭션(SQL 어댑터)으로 정합 처리한다. owner 규모는 U3 1차 타깃(~1,000 활성 사용자)을 상속하고, **정확한 임계 강제 지점·인덱스 수치는 NFR Design/Infra가 SSOT**다. → BR-L2/L4/L6.

---

### Q4 — 영속성 가용성 및 가용성 격리 (Availability & Resilience)
U4 도메인 데이터(저장 검색·라이브러리·이력)의 영속성 가용성/복구 목표와, 라이브 인덱스(U2) 장애 시 동작을 어떻게 정의하는가?

A) **(권장) U3 RDS 가용성 상속 + 가용성 격리**: 영속성은 U3가 확정한 RDS PostgreSQL Multi-AZ 가용성(가용성 99.99% / RPO ≤ 24h 스냅샷 / RTO ≤ 4h, U3 자격증명 DB와 동급)을 상속. **+ 가용성 격리**: 라이브러리/이력 읽기는 저장 스냅샷(`LibraryItemMeta`)만 사용 → U2/인덱스/게이트웨이 장애와 **무관하게 동작**(rerun만 외부 의존).

B) U4 전용 고가용성 캐시 계층(ElastiCache 등) — U4 도메인 데이터는 영속·관계형 무결성 요구이므로 캐시 불요(과설계).

C) Other.

[Answer]: A. U4 도메인 데이터의 영속성 가용성은 U3가 확정한 **Amazon RDS(PostgreSQL) Multi-AZ**(가용성 목표 99.99% / RPO ≤ 24h 일일 스냅샷+증분 / RTO ≤ 4h)를 상속한다(TD-U3-3 동급). U4는 별도 캐시/세션 스토어가 불필요하다(U3가 세션용으로 쓰는 ElastiCache는 U4 도메인 데이터에 부적합 — 영속·관계형 무결성·쿼터 카운트·NFC 유니크 강제가 관계형 친화적). 핵심은 **가용성 격리(BR-L5)**: 라이브러리 카드는 추가 시점 저장된 `LibraryItemMeta` 스냅샷을 verbatim 반환하므로, 라이브 인덱스(U2)/게이트웨이가 다운되어도 라이브러리·이력 목록 읽기는 정상 동작한다. 외부 의존은 **rerun 한 경로뿐**이며, 이는 `SearchGatewayPort` 장애 시 우아하게 실패(rerun만 5xx, 목록은 영향 없음)한다. → TD-U4-3, BR-L5/INV-L1.

---

### Q5 — 영속성 접근 패턴 및 ORM (D10 / Tech Stack)
U4 영속성 접근을 어떤 패턴/도구로 구현하는가? (브리프 §3 D10 직접 대상)

A) **(권장) 포트 기반 리포지토리: `InMemoryUserDataRepository`(기본, mock-first) + `SqlUserDataRepository`(SQLAlchemy 2.x scaffold, 프로덕션) + DDL `001_create_library_tables.sql`** — `UserDataRepository`를 `typing.Protocol` 포트로 정의(3개 서브-리포 집약). 두 어댑터 모두 read/write를 `owner_id`로 구조적 필터링(INV-L1). Unique 제약으로 멱등성 backstop: `(owner_id, normalized_query)`·`(owner_id, arxiv_id)`·`(owner_id, dedupe_key)`. SQLAlchemy 2.x는 이미 선언됨(신규 의존성 0).

B) 단일 SQL 전용 구현 — 테스트/마운트에 라이브 DB 강제(U2/U3 mock-first 규약 위반).

C) 원시 SQL(asyncpg 직접) — 매핑/마이그레이션·타 모듈 패턴 정합 저하.

D) Other.

[Answer]: A. **D10대로** `UserDataRepository`를 `typing.Protocol` 포트로 정의하고 두 어댑터를 제공한다 — **`InMemoryUserDataRepository`(기본·mock-first)**로 app-shell이 PostgreSQL 없이 마운트되고 CI가 그린으로 통과(가용성 격리·CI unblock; "마운트=라이브 인프라 필요" 결합 차단), **`SqlUserDataRepository`(프로덕션 scaffold)**는 **SQLAlchemy 2.x**(이미 선언 → 신규 의존성 0, U3 상속 TD-U3-5)로 typed `Mapped[...]` 매핑. **DDL `migrations/001_create_library_tables.sql`** 동봉(3개 테이블 + 위 3개 Unique 제약). 두 어댑터 모두 owner-scoping backstop(INV-L1)을 구조적으로 강제. 동일 포트 뒤 두 구현으로 PBT-09·쿼터·멱등 속성을 어댑터 무관 검증. **정확한 인덱스명·트랜잭션 격리·DDL 확정은 NFR Design/Infra가 SSOT.** → TD-U4-4, TD-U4-5.

---

### Q6 — 인가 권위 ([U3 계승] / SEC-8)
U4의 소유권 인가는 어디서 결정하는가?

A) **(권장) U3 `AuthorizationGuard`에 위임(SEC-8 단일 권위)** — `AuthorizationGuard.authorize(principal, action, AccountId(owner_id))`. `Principal`/`Action`/`AccountId`/`Decision` 재사용(재정의 금지). 컨트롤러는 `get_principal`로 `request.state.principal`(U6 미들웨어 세팅)을 읽고 부재 시 401. cross-owner OR principal 부재 → DENY → **404 일반화**(SEC-9 존재 비노출). 알 수 없는 오류 → fail-closed 500.

B) U4 자체 ownership 체크 — 인가 권위 분기(U3가 회피하려던 결함의 재현, SEC-8 위반).

C) 게이트웨이 단독 인가 — 데이터 계층 backstop(INV-L1) 상실.

[Answer]: A. **SEC-8 단일 인가 권위**를 유지한다 — U4는 자체 인가 로직을 정의하지 않고 전적으로 `AuthorizationGuard.authorize(...)`에 위임하며, `Principal`/`Action`/`AccountId`/`Decision`을 `backend.modules.accounts`에서 재사용(재정의 금지). 컨트롤러는 `get_principal` 의존성으로 `request.state.principal`을 읽고 부재 시 **401**, 테스트/standalone은 의존성 오버라이드. cross-owner OR principal 부재 → DENY → **HTTP 404**로 일반화(SEC-9 존재 비노출), 알 수 없는 오류 → **fail-closed 500**(INV-L4: 절대 fail-open 아님, SEC-15). 데이터 계층의 owner-scoping(INV-L1)은 가드 결정 하위의 방어심층(defense-in-depth)이다. → TD-U4-7, D11/INV-L4.

---

### Q7 — 페이지네이션 커서 코덱 (D8 / Tech Stack)
목록 엔드포인트(저장 검색·라이브러리·이력)의 페이지네이션을 어떻게 구현하는가?

A) **(권장) 표준 라이브러리 `base64`(URL-safe) + JSON keyset 커서** — most-recent-first keyset. `cursor` = `{"ts": <정렬 인스턴트 iso>, "id": <id>}` JSON → URL-safe base64 불투명 토큰. `limit` 기본 **20** / **최대 100**(>100 → **422 REJECT**, 명시성 우선) · 첫 페이지 cursor 생략 · 마지막 페이지 `nextCursor` 부재 · 변조/깨진 커서 → **422**. 신규 의존성 0.

B) 오프셋 페이지네이션 — 대형 목록 일관성·성능 저하.

C) 서명 커서(JWT/HMAC) — 보안 토큰 아니므로 과설계.

D) Other.

[Answer]: A. **D8대로** 표준 라이브러리 `base64`(URL-safe) + `json` keyset 커서를 사용한다(most-recent-first). 커서는 **보안 토큰이 아니라 불투명 페이로드 인코딩**일 뿐이므로 서명/암호화 불요 — 변조는 keyset 디코드 실패로 422 처리. `limit` 기본 **20**·**최대 100**(초과 → **422 REJECT**, clamp 아닌 명시적 거부), 첫 페이지 cursor 생략, 마지막 페이지 `nextCursor` 부재. keyset(오프셋 아님)으로 advisory cursor property(limit L로 전 항목을 정확히 1회·누락/중복 없이 most-recent-first 수집)를 만족한다. 커서 코덱은 `UserDataDTOAndValidation`(`validation.py`)에 캡슐화. → TD-U4-6, BR-L8.

---

### Q8 — rerun 경로 (D9 / INV-L2 / Tech Stack)
저장 검색·이력 항목의 rerun(재실행)은 어떻게 검색을 수행하는가?

A) **(권장) `SearchGatewayPort` 경유(게이트웨이-fronted) + `StubSearchGateway`** — rerun은 U2를 **직접 호출하지 않는다.** `SearchGatewayPort`(`search(query, principal) -> SearchResultSetDTO`)로 게이트웨이-fronted 계약(U6 ApiGatewayMiddleware → U2)에 재진입 → 비용 게이트·근거화 hook 재적용(백도어 없음). U4는 `StubSearchGateway`(결정적 placeholder) 동봉, 실 바인딩은 U6/Infra 주입.

B) U2 서비스 직접 호출 — INV-L2 위반, 비용/근거화 우회.

C) 클라이언트가 query만 받아 별도 검색 — 서버 계약 일관성·감사성 저하.

[Answer]: A. **D9/INV-L2(no-rerun-backdoor)**대로 rerun은 저장된 query를 해석한 뒤 `SearchGatewayPort`로 호출하여 신규 검색과 **동일한 비용 게이트(U6.CostGuardCircuitBreaker)·근거화 hook**을 통과한다 — U2 직접 import는 격리·비용 통제·근거화를 우회하므로 금지. U4는 `StubSearchGateway`(결정적 placeholder)를 동봉하고 실 게이트웨이 결선은 U6 통합 시점에 주입. 이로써 rerun 비용은 일반 검색 1회와 동일하게 계상되어 **U4가 별도 비용 상한을 두지 않고 시스템 NFR-C1 게이트에 위임**한다. → TD-U4-8, INV-L2.

---

### Q9 — 빌드/의존성 및 PBT 도구 ([전역 계승] + [U3 계승] / Tech Stack)
U4가 도입하는 신규 서드파티 의존성과 PBT(속성 기반 테스트) 프레임워크는?

A) **(권장) 신규 서드파티 런타임 의존성 0 + PBT=Hypothesis(dev, 상속)** — `fastapi`·`sqlalchemy`·`pydantic`은 이미 선언; 커서·검증·dedupe는 표준 라이브러리(`base64`·`json`·`hashlib`·`unicodedata`·`re`). `hashlib.sha256`으로 `dedupe_key`(D7) 생성. PBT는 U1/U2/U3 상속 **Hypothesis**(dev 의존성)로 **PBT-09(U4 블로킹)** 구현.

B) 페이지네이션/커서/검증 전용 라이브러리 도입 — 표준 라이브러리로 충분, 공급망 표면 증가(거부).

C) Other.

[Answer]: A. U4는 **신규 런타임 서드파티 의존성을 0**으로 한다(U1/U2/U3와 동형 공급망 자세 SEC-10, 모노레포 단일 락파일 정합) — 사용 라이브러리는 이미 선언, 커서 코덱·SEC-5 검증·dedupe는 표준 라이브러리로 충족(`hashlib.sha256`으로 `dedupe_key`). PBT는 U3 상속 **Hypothesis**(dev 의존성)로 작성하며, **PBT-09(U4 핀, 블로킹)**: 임의의 유효 도메인 엔티티에 대해 `to_dto(entity)` → shared DTO 검증이 안정적이고, 유효 create DTO의 `validate_and_map`이 public 필드를 라운드트립하며, **직렬화→역직렬화가 public 필드를 보존하고 내부 필드(owner_id·dedupe_key·normalized_query·scores·audit meta)를 절대 누출하지 않는다**(SEC-9). cursor property(advisory)도 Hypothesis로 검증. → TD-U4-9, TD-U4-10, PBT-09.

---

### Q10 — 와이어 DTO/이벤트 소스 (브리프 §5 / SSOT)
요청/응답 DTO와 이력 이벤트의 정의는 어디서 가져오는가?

A) **(권장) `docsuri_shared` SSOT 재사용(포크 금지) + U4 내부 검증 강화** — `docsuri_shared.dtos`에서 import(`PageParams, SavedSearchCreateDTO, SavedSearchDTO, SavedSearchPageDTO, LibraryItemCreateDTO, LibraryItemDTO, LibraryPageDTO, HistoryEntry, HistoryPageDTO, SearchResultSetDTO`), 이벤트는 `docsuri_shared.events.SearchExecutedEvent`(🔒FROZEN). U4는 §3 정련(max limit 100, 타입 meta, string id, 커서 시맨틱)을 **자체 검증 계층**(`UserDataDTOAndValidation`)에서 강제. `LibraryItemMeta`는 U4-내부 검증기(와이어 DTO 재정의 아님).

B) U4 로컬 DTO 정의 — SSOT 포크(U3가 범한 결함의 재현, 거부).

C) Other.

[Answer]: A. 와이어 DTO는 `docsuri_shared.dtos` SSOT에서 import하고 이벤트는 `docsuri_shared.events.SearchExecutedEvent`(🔒FROZEN, U2 producer ↔ U4 consumer)를 재사용한다 — **SSOT 포크는 U3가 범한 결함**(BR-A4 위반+SSOT 포크)으로 명시적으로 회피한다. shared 바인딩이 느슨한 부분(`id`/`meta`=Any, `limit` ge=1·max 없음)은 **U4 자체 검증 계층(`UserDataDTOAndValidation`)이 §3 정련으로 강화**(limit 최대 100, string id, 커서 시맨틱)하고, **`LibraryItemMeta`(U4-내부 pydantic 모델)가 `meta: Any`를 타입 검증**한다(U2 ResultCardVM 카드 필드 미러 — title·authors·year·arXivId·abstractSnippet·arxivUrl, 가용성 격리). 따라서 재생성 바인딩 설치 여부와 무관하게 U4가 정확하다. `LibraryItemMeta`는 **와이어 DTO 재정의가 아니라 내부 검증기**다. → TD-U4-11.

---

### Q11 — 감사 및 이력 쓰기 경로 (D12 / D7 / SEC-13)
변경 연산 감사(SEC-13)와 검색 이력 쓰기는 어떻게 처리하는가?

A) **(권장) `AuditSink` 포트 + `InMemoryAuditSink`(no-op 기본) + `SearchExecutedEvent` 멱등 소비자(비-공개 POST)** — 서비스는 변경 연산(save/delete·add/remove·clear)에서 `AuditSink`로 감사 이벤트 발행(민감/내부 필드 미포함, SEC-9; no-op 기본으로 의존성 없이 마운트, 실 결선 U6/ops). 이력 **쓰기는 이벤트 구동** — `history_consumer.py`가 `SearchExecutedEvent`(at-least-once)를 소비해 `dedupe_key`로 멱등 기록(exactly-once 행, INV-L3); **공개 POST 엔드포인트 없음**.

B) 직접 로깅 호출 + 공개 history POST — 교체성·테스트성 저하 + 클라이언트 위조/중복/인가 표면 증가(거부).

C) Other.

[Answer]: A. **감사(D12/BR-L10)**: 서비스는 변경 연산에서 `AuditSink` 포트로 감사 이벤트를 발행하고 기본 구현은 인메모리/no-op(`InMemoryAuditSink`)이며 실 결선은 U6/ops — 페이로드에 민감/내부 필드 미포함(SEC-9), no-op 기본으로 app-shell이 의존성 없이 마운트. **이력 쓰기(D7/INV-L3/BR-L7)**: Search History의 쓰기는 **이벤트 구동**으로 `history_consumer.py`가 `SearchExecutedEvent`(🔒FROZEN, at-least-once)를 소비해 `dedupe_key = sha256(owner_id|executed_at.isoformat()|query)`로 멱등 기록한다 — 재전달이 중복 행을 생성하지 않으며(exactly-once 행), 데이터 계층 `(owner_id, dedupe_key)` Unique와 함께 이중 보장. **공개 history POST 엔드포인트는 없다**(클라이언트 위조·중복·인가 표면 회피). → TD-U4-12, TD-U4-13.

---

## 5. 추적성 요약 (Traceability)

| 질문 | 결정 | 매핑 ID |
|---|---|---|
| Q1 | CRUD 레이턴시 예산(게이트 아님) + 가용성 격리 | BR-L5, BR-L8, INV-L1 |
| Q2 | Python 3.12+ [전역] + FastAPI/CG-1 [backend-shared] | TD-U4-1, TD-U4-2, §9 |
| Q3 | 쿼터 200/1000 + 보존 500 + owner 규모 | BR-L2, BR-L4, BR-L6 |
| Q4 | RDS 가용성 [U3] + 가용성 격리 | TD-U4-3, BR-L5, INV-L1 |
| Q5 | 포트 리포지토리(InMemory 기본 + Sql scaffold + DDL) [U3 ORM] | TD-U4-4, TD-U4-5, D10, INV-L1 |
| Q6 | 인가 위임(AuthorizationGuard, 404 일반화) [U3] | TD-U4-7, D11, INV-L4, SEC-8, SEC-9 |
| Q7 | base64 keyset 커서(limit 20/max 100, 422) | TD-U4-6, BR-L8, D8 |
| Q8 | rerun via SearchGatewayPort + Stub | TD-U4-8, BR-L9, INV-L2 |
| Q9 | 신규 의존성 0 [전역] + Hypothesis/PBT-09 [U3] | TD-U4-9, TD-U4-10, PBT-09 |
| Q10 | shared DTO/이벤트 SSOT 재사용 + LibraryItemMeta 검증기 | TD-U4-11, 브리프 §5 |
| Q11 | AuditSink no-op + SearchExecutedEvent 멱등 소비자 | TD-U4-12, TD-U4-13, D7, D12, INV-L3 |
| — | 비용 무동인 / rerun만 게이트 위임 | NFR-C1(시스템 전역 $1600) |

## 6. 결정 요약 & 후속 (Step 4)

- ✅ **[전역 계승]**: Python 3.12+(Q2) · 신규 서드파티 의존성 0 / 모노레포 backend(Q9) · NFR-C1 $1600 시스템 전역 상한(U4 직접 동인 0).
- ✅ **[backend-shared]**: FastAPI / CG-1(Q2).
- ✅ **[U3 계승]**: RDS PostgreSQL(Q4) · SQLAlchemy 2.x(Q5) · AuthorizationGuard 위임(Q6) · Hypothesis(Q9).
- ✅ **U4 고유**: CRUD 레이턴시 예산 + 가용성 격리(Q1·Q4) · 쿼터/보존 수치(Q3) · 포트 기반 리포지토리(Q5) · base64 keyset 커서(Q7) · rerun via SearchGatewayPort(Q8) · shared DTO SSOT 재사용 + LibraryItemMeta(Q10) · AuditSink no-op + 이력 멱등 소비자(Q11).
- **후속(NFR Design / Infra로 이관)**:
  - 쿼터/보존 임계 강제 지점 구현 세부(BR-L2 200·L4 1000·L6 500의 count-then-insert 트랜잭션/프루닝).
  - `001_create_library_tables.sql` DDL 확정(3개 테이블 + 3개 Unique 인덱스: `(owner_id, normalized_query)`·`(owner_id, arxiv_id)`·`(owner_id, dedupe_key)` + owner-scoped 보조 인덱스).
  - `SqlUserDataRepository` 트랜잭션/격리 수준 · 페이지 한도 422 메시지 일반화.
  - 실 `SearchGateway`/`AuditSink` 결선(U6 통합) · CI 드리프트 가드(shared 바인딩) 통과 확인.
  - CRUD 레이턴시(Q1) 실측은 Build & Test/Infra.
