# u4-library-nfr-design-plan.md — NFR Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Design (유닛별 루프, Track 2 두 번째·최종 유닛) · **유닛**: U4 Library · **일자**: 2026-06-17
**근거(SSOT)**: `tmp/u4-design-brief.md` (Identity §0 · 결정 D1~D12 · BR-L1~L10 · INV-L1~L4 · SEC-5/8/9/13/15 · PBT-09) · **상위 NFR/Infra(부모)**: `construction/u3-accounts/nfr-design/` (복원력·풀·시크릿·CORS 정본) + `construction/u4-library/infrastructure-design/infrastructure-design.md` (U3 인프라 상속, RDS 테이블 3개 추가)
**소유**: Track 2 (@revenantonthemission) · Track 2 흐름 = U3 Accounts → **U4 Library**(최종 유닛)

---

## 1. 유닛 컨텍스트 및 목표 (Step 1)

U4 Library는 **소유자 비공개(owner-private) 동기 CRUD + 검색 이력 이벤트 소비** 유닛이며, 자체 신규 관리형 서비스나 신규 비용이 없습니다(infrastructure-design.md §0). 인프라 차원에서는 U3가 확정한 ECS Fargate 모놀리스(배포 단위 ①)에 코드만 동봉되고 U3 RDS PostgreSQL에 테이블 3개를 추가할 뿐입니다. 따라서 U4의 NFR Design은 **인프라 토폴로지 재설계가 아니라**, 다음 두 축의 **디자인 패턴 + 논리 컴포넌트 상호작용**을 확정하는 데 집중합니다.

1. **포트-우선(port-first) 의존성 격리**: U4는 `UserDataRepository`·`SearchGatewayPort`·`AuditSink` 세 개의 `typing.Protocol` 포트 뒤에 외부 의존성(DB·게이트웨이/U2·감사 백본)을 격리합니다(브리프 §7). 기본 구현은 모두 **인메모리(mock-first)** 이므로, 라이브 인프라 없이도 app-shell이 8 라우터를 그린으로 마운트합니다(브리프 §8). NFR Design은 이 포트 경계에서의 **복원력·타임아웃·격리** 정책을 디자인합니다.
2. **보안·정합성 불변식의 강제 지점 디자인**: SEC-8(인가 단일 권위점 U3 Guard 위임)·SEC-9(교차 소유자 404 일반화·내부 필드 비누출)·INV-L1(소유자 스코핑 데이터 백스톱)·INV-L4(Fail-closed)·BR-L8(키셋 커서)·PBT-09(DTO 라운드트립)가 **어떤 논리 컴포넌트에서 어떻게 강제되는가**를 디자인합니다.

- **핵심 NFR 디자인 요소**:
  - **복원력(Resilience)**: `SearchGatewayPort`(rerun 경로) 및 history 컨슈머의 타임아웃·실패 격리; 가용성 격리(라이브러리는 라이브 인덱스 비의존, BR-L5); 포트 기본값이 인메모리이므로 외부 장애가 U4 마운트를 막지 않도록 하는 graceful-skip 디자인.
  - **확장성/성능(Scalability/Performance)**: 커서 기반 키셋 페이지네이션(BR-L8)과 owner-scoped 인덱스(`(owner_id, <sort> DESC, id DESC)`)로 OFFSET 없는 O(limit) 조회; 소유자별 상한(200/1000/500)으로 무제한 증가 차단; 이력 쓰기 비차단(NFR-P1).
  - **보안(Security)**: SEC-8 인가 위임 + INV-L1 데이터 백스톱의 이중 방어심층; SEC-9 비노출(직렬화 화이트리스트); SEC-15/INV-L4 Fail-closed 예외 매핑; SEC-13 감사 포트.

> **상속 선언**: 커넥션 풀 수치, RDS/Redis 타임아웃, 시크릿 환경변수 주입(12-Factor/SEC-10), CORS·HTTP 보안 헤더 등 **전역·U3 확정 사항은 U4에서 재정의하지 않고 부모 NFR Design(`u3-accounts/nfr-design/`)을 정본으로 상속**합니다. U4 고유 결정만 본 문서에서 확정합니다.

---

## 2. NFR Design 실행 계획 (Step 2)

> 질문(Q1~Q6) 답변 완료 후, 아래 산출물을 `aidlc-docs/construction/u4-library/nfr-design/` 디렉터리에 작성합니다. 구조·문체는 U3 `nfr-design/`의 두 산출물(`nfr-design-patterns.md`·`logical-components.md`)을 그대로 미러링합니다.

- [ ] **nfr-design-patterns.md** — 비즈니스 예외 및 시스템 장애 관련 디자인 패턴 정의
  - `SearchGatewayPort` rerun 경로의 타임아웃·실패 격리·Fail-Closed 패턴 (Q1).
  - 이력 컨슈머 at-least-once → exactly-once 멱등 기록 및 포트 격리 패턴 (Q2).
  - `AuthorizationGuard` 위임 + 데이터 백스톱(INV-L1) 이중 방어심층 및 SEC-15 Fail-closed 예외→HTTP 매핑 패턴 (Q3, Q6).
  - 가용성 격리(BR-L5) — 라이브러리 렌더링이 라이브 인덱스/게이트웨이를 재조회하지 않는 스냅샷 패턴.
- [ ] **logical-components.md** — 논리 컴포넌트 구조도 및 책임 명세
  - 포트 경계(`UserDataRepository`·`SearchGatewayPort`·`AuditSink`)와 기본 인메모리 구현 ↔ 프로덕션 SQL/실 게이트웨이 어댑터의 교체 시임 구조 (Q4).
  - 커서 코덱(URL-safe base64 불투명 토큰)·키셋 정렬 키·page limit 강제(REJECT)를 담는 `UserDataDTOAndValidation` 컴포넌트 명세 (Q5).
  - SEC-9 직렬화 경계(내부 필드 비누출 화이트리스트) 및 `get_principal` DI 시임(`request.state.principal`, U6 미들웨어가 설정; 테스트 오버라이드).
  - PBT-09(차단성)·PBT-Cursor(advisory) 및 CI 통합(드리프트 가드·ruff·Hypothesis) 모델.

---

## 3. 가정 (Assumptions)

- **AS-1 (mock-first 운영 기본값)**: U4의 세 포트는 모두 인메모리 기본 구현(`InMemoryUserDataRepository`·`StubSearchGateway`·`InMemoryAuditSink`)으로 마운트됩니다(브리프 §8, D10/D9/D12). 라이브 DB·게이트웨이·감사 백본은 **프로덕션/Infra 배선 시점**에만 주입되며, 본 NFR Design은 두 모드(인메모리·프로덕션) 모두에서 동일한 불변식이 성립하도록 디자인합니다.
- **AS-2 (동기 런타임 상속)**: U3와 동일하게 동기식 멀티스레드/멀티프로세스 컨테이너 런타임을 전제합니다(U3 AS-2). 단 컨트롤러는 FastAPI `async` 엔드포인트이며, 인메모리 기본 구현은 블로킹 I/O가 없습니다. 프로덕션 `SqlUserDataRepository`는 U3가 확정한 SQLAlchemy `QueuePool`(pool_size 10 / max_overflow 20 / pool_timeout 3.0초 / pool_recycle 1800초)을 **그대로 상속**하며 본 문서에서 재정의하지 않습니다.
- **AS-3 (인가 단일 권위점 위임)**: 소유권 인가는 U3 `AuthorizationGuard.authorize(principal, action, AccountId(owner_id))`에 위임합니다(SEC-8). U4는 인가 정책·세션 검증·Redis 복원력을 **재정의하지 않으며**, 그 모든 결정은 U3/U6 정본을 상속합니다(D11).
- **AS-4 (이벤트 계약 동결)**: `SearchExecutedEvent`는 🔒FROZEN이며 at-least-once 전달을 전제합니다. 메시지 버스(EventBridge/SQS)의 전달 보증 수준과 무관하게 `dedupe_key` 고유 제약으로 exactly-once 행을 수렴합니다(INV-L3). 실제 버스 배선은 U6/공유 인프라의 관심사로 이연합니다(infrastructure-design.md §4).

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그로 답변, 권장 기본값은 override 가능)

> 아래 답변은 **브리프의 결정(D1~D12)에서 도출한 권장 기본값(recommended default)**이며, 리뷰 게이트에서 override 가능합니다. 어느 것도 브리프를 넘어서는 새 결정을 만들지 않으며, 브리프가 침묵하는 곳은 상속/전역 결정을 명시합니다.

### Q1 — 재실행(rerun) 게이트웨이 포트의 복원력 패턴 (Resilience / SearchGatewayPort)
`rerunSavedSearch` / `rerunHistoryEntry`는 저장된 질의를 해석한 뒤 `SearchGatewayPort.search(query, principal) -> SearchResultSetDTO`로 재진입합니다(D9/BR-L9, INV-L2 — U2 직접 호출 금지). 이 게이트웨이 경유 검색이 일시적으로 타임아웃되거나 다운되는 경우 어떻게 처리합니까?

A) **Fail-Closed (게이트웨이 격리)**: rerun은 게이트웨이 경유로만 재진입한다는 불변식(INV-L2)을 절대 우회하지 않는다. 게이트웨이 호출 타임아웃(권장 **3.0초**, U3 외부 호출 버짓과 정합)·에러·서킷 오픈 시 rerun 요청을 즉시 실패 처리하여 일반화된 시스템 오류(**HTTP 503/500**)를 반환하고, 절대 캐시된 라이브러리 스냅샷이나 직접 U2 호출로 폴백하지 않는다(백도어 금지). 게이트웨이 장애가 라이브러리/이력 **조회**(rerun이 아닌 CRUD)에는 전파되지 않도록 rerun 경로만 격리한다.

B) **소프트 폴백 (캐시된 결과 반환)**: 게이트웨이 장애 시 마지막으로 알려진 결과나 라이브러리 스냅샷을 임시 결과로 반환하여 사용자 흐름을 유지한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재).

[Answer]: A. rerun의 본질은 "비용·근거화 훅을 재적용한 신선한 검색"(BR-L9)이므로, 캐시·스냅샷·직접 U2 호출로 폴백(B안)하면 게이트웨이 전면(U6 ApiGatewayMiddleware)이 부과하는 비용 통제·근거화·인가 훅을 우회하는 백도어가 되어 INV-L2를 정면으로 위반한다. 따라서 게이트웨이 경유를 절대 우회하지 않는 Fail-Closed를 채택하되, 게이트웨이 호출에 **3.0초 타임아웃**과 짧은 서킷 브레이커(U3 외부 API 패턴 상속: 10초 윈도우 5회 실패 시 OPEN, 30초 후 half-open 1회 검증)를 둔다. rerun 실패는 **HTTP 503**(일시적·재시도 가능)으로 일반화하여 반환하고, 이 장애는 **rerun 경로에만 격리**되어 저장 검색/라이브러리/이력의 순수 CRUD 조회(가용성 격리, BR-L5)에는 전파되지 않는다. 인메모리 단계의 `StubSearchGateway`는 결정론적 placeholder이므로 본 타임아웃·서킷 정책은 실 게이트웨이 어댑터 주입(U6/Infra) 시점에 활성화되는 사양으로 명세한다.

### Q2 — 검색 이력 컨슈머의 멱등성 및 실패 격리 패턴 (Resilience / History Consumer)
검색 이력 쓰기는 공개 POST가 아니라 `SearchExecutedEvent`(🔒FROZEN, at-least-once) 구독 컨슈머입니다(브리프 §6, D7/BR-L7). 이벤트 재전달·부분 실패·버스 미연결 상황을 어떻게 디자인합니까?

A) **디덥 키 기반 exactly-once + 비차단 + graceful 미연결**: `dedupe_key = sha256(owner_id|executed_at.isoformat()|query)`의 고유 제약으로 at-least-once 재전달을 exactly-once 행으로 수렴한다(INV-L3). 이력 기록은 검색 응답 경로를 차단하지 않으며(NFR-P1), 라이브 메시지 버스가 없는 단계에서는 인메모리 컨슈머(`history_consumer.py`)로 동작하여 U4 단독 마운트·테스트가 그린이 되도록 한다. 기록 중 일시 오류는 at-least-once 재전달에 맡겨 재시도되며(중복은 디덥이 흡수), 기록 실패가 발행자(U2 검색)에게 역전파되지 않는다.

B) **동기 기록 + 발행자 차단**: 검색 응답 전에 이력 기록 성공을 동기로 보장하고, 기록 실패 시 검색 자체를 실패시킨다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재).

[Answer]: A. 이력은 부가 기록이며 검색의 핵심 응답이 아니다(NFR-P1: 검색 응답 비차단). B안처럼 이력 기록을 검색 응답 경로에 동기로 묶으면 이력 저장소 장애가 검색 가용성을 직접 끌어내리는 결합을 만든다. 따라서 컨슈머는 발행자와 비동기·격리되며, `dedupe_key` 고유 제약(infrastructure-design.md §3.2 `UNIQUE (owner_id, dedupe_key)`)이 at-least-once 재전달을 exactly-once 행으로 수렴한다(INV-L3). 한도(rolling 500, D6/BR-L6) 초과 시 가장 오래된 행을 같은 트랜잭션에서 프루닝한다. 라이브 버스 미연결 단계에서는 인메모리 컨슈머로 동작하여 EventBridge/SQS 같은 신규 관리형 서비스가 U4 마운트의 전제가 되지 않도록 한다(infrastructure-design.md §4). 실제 버스 배선·DLQ 정책은 U6/공유 인프라로 이연한다.

### Q3 — 인가 강제 지점 및 데이터 백스톱 이중화 패턴 (Security / Authorization + INV-L1)
소유자 비공개 자원의 접근 통제를 **어느 계층에서 몇 번** 강제합니까? (SEC-8 인가 단일 권위점 + INV-L1 데이터 백스톱)

A) **이중 방어심층 (Guard 위임 + 구조적 owner-scoping)**: ① 서비스 계층에서 `AuthorizationGuard.authorize(principal, action, AccountId(owner_id))`로 소유권 결정을 위임하고(SEC-8 단일 권위점), ② 그와 독립적으로 모든 리포지토리 read/write가 `owner_id`로 **구조적 필터링**되어(INV-L1) Guard가 어떤 이유로 우회되더라도 타 소유자 행을 반환·변경할 수 없게 한다. 두 계층 모두에서 위반은 DENY로 종결되며 자원 관련은 **404로 일반화**(SEC-9, 존재 비노출).

B) **단일 강제 (Guard만)**: 인가는 Guard 한 곳에서만 결정하고 리포지토리는 owner 필터 없이 id로 조회한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재).

[Answer]: A. SEC-8은 인가 결정의 단일 권위점을 U3 `AuthorizationGuard`로 못박지만(중복 정책 정의 금지), 이는 "결정 로직의 단일화"이지 "강제 지점의 단일화"가 아니다. 데이터 계층의 owner-scoping(INV-L1)은 별도의 인가 정책을 정의하는 것이 아니라, Guard 결정 하위에서 동작하는 **방어심층(defense-in-depth) 백스톱**이다 — 컨트롤러/서비스의 버그나 누락된 Guard 호출이 있어도 SQL/인메모리 질의 자체가 `WHERE owner_id = :principal_owner`로 묶여 타 소유자 데이터 유출을 구조적으로 차단한다. 따라서 ①Guard 위임 + ②구조적 owner-scoping의 이중화를 채택한다. 두 계층 모두 위반 시 자원 관련은 403이 아닌 **404로 일반화**(SEC-9)하여 존재 여부를 비노출하고, 세션/주체 부재는 401로 분기한다(INV-L4). 멱등 재저장·재추가만 정상 200으로 처리한다.

### Q4 — 포트 경계 및 구현 교체 시임 디자인 (Scalability / Port-First DI)
세 포트(`UserDataRepository`·`SearchGatewayPort`·`AuditSink`)의 인메모리 기본 ↔ 프로덕션 어댑터 교체를 어떻게 디자인합니까? (D10/D9/D12, 브리프 §8 app-shell wiring)

A) **`typing.Protocol` 포트 + DI 오버라이드 시임**: 세 포트를 `ports.py`에 `typing.Protocol`로 선언하고, 컨트롤러는 accounts 패턴(`get_db_session`-style provider + `Depends`)으로 구현을 주입받는다. app-shell `_mount_library`가 인메모리 싱글턴(`InMemoryUserDataRepository`·`StubSearchGateway`·`InMemoryAuditSink`)을 빌드해 DI 프로바이더를 오버라이드하고 3개 라우터를 `include_router`한다. 프로덕션 배선만 `SqlUserDataRepository`/실 게이트웨이/실 감사 싱크로 동일 시임을 교체한다(코드 변경 없이 주입만 교체). 테스트/스탠드얼론도 동일 오버라이드로 의존성을 격리한다.

B) **구체 클래스 직접 인스턴스화**: 서비스가 구체 리포지토리/게이트웨이를 직접 `import`·생성한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재).

[Answer]: A. B안(구체 직접 인스턴스화)은 rerun이 U2를 직접 호출하지 않는다는 INV-L2를 깨뜨리기 쉽고(게이트웨이 우회), 라이브 인프라 없이 마운트한다는 mock-first 요구(브리프 §8)와도 충돌한다. 따라서 세 의존성을 `typing.Protocol` 포트로 추상화하고(브리프 §7 `ports.py`), 컨트롤러는 accounts와 동일한 `Depends` 기반 DI 시임으로 구현을 주입받는다. app-shell `_mount_library(app, settings, result)`는 인메모리 싱글턴을 1회 빌드해 DI 프로바이더를 오버라이드하고 `"library"`를 `result.mounted`에 추가하며, `_mount_library`를 `_INTEGRATIONS`에 등록한다(브리프 §8). 이 시임은 (a) 라이브 DB 없이 마운트(가용성), (b) rerun의 게이트웨이 단일 경로 강제(INV-L2), (c) 테스트 격리를 동시에 만족한다. accounts의 DB 엔진 재사용 패턴은 가용 상태로 두되 U4 기본값은 인메모리이며 PostgreSQL을 마운트 전제로 요구하지 않는다.

### Q5 — 페이지네이션 커서 및 page limit 강제 디자인 (Performance / Keyset + SEC-5)
모든 컬렉션 조회의 키셋 커서·정렬·limit 경계를 어떻게 강제합니까? (D8/BR-L8, SEC-5)

A) **불투명 base64 커서 + REJECT 상한 + 키셋 인덱스**: `cursor`는 `{"ts": <정렬 instant ISO>, "id": <id>}`의 **URL-safe base64** 불투명 토큰으로, 첫 페이지는 생략하고 마지막 페이지 응답에는 `nextCursor`를 부재시킨다. `limit` 기본 **20**, 최대 **100**이며 `>100`은 클램프가 아니라 **REJECT(HTTP 422)**(명시성), `<1`도 422. 변조/손상 커서는 디코드/검증 실패 시 **422 + 일반화 메시지**. 정렬은 최신순이며 owner-scoped 복합 인덱스 `(owner_id, <sort> DESC, id DESC)`로 OFFSET 없는 O(limit) 조회를 보장하고, 커서 코덱·검증은 `UserDataDTOAndValidation`이 단일 책임으로 보유한다.

B) **OFFSET/LIMIT 숫자 페이지 + 자동 클램프**: `page`/`size` 숫자 파라미터, 초과 limit은 100으로 조용히 클램프.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재).

[Answer]: A. B안의 OFFSET 페이지네이션은 깊은 페이지에서 O(offset) 스캔 비용과 동시 삽입 시 행 중복/누락(키셋 불안정)을 일으키며, 자동 클램프는 클라이언트가 잘못된 limit을 모르고 지나치게 한다. 브리프 D8은 **명시성을 위해 REJECT**를 택했으므로 `>100`·`<1`은 422로 거절한다(SSOT `ge=1` + U4 상한 강제). 커서는 정렬 기준 instant와 tie-breaker `id`를 함께 담은 URL-safe base64 불투명 토큰으로, 노출 시 내부 구조(컬럼명·정렬 키)를 드러내지 않고(SEC-9 정합) 변조 시 422로 일반화한다. owner-scoped 복합 인덱스 `(owner_id, <sort> DESC, id DESC)`(infrastructure-design.md §3.2)가 키셋 조회를 인덱스만으로 충족하여 O(limit) 성능과 안정 순회(중복·누락 없음)를 보장한다. 커서 인코딩·디코딩·검증·정렬 키 산출은 `UserDataDTOAndValidation`에 단일 책임으로 모으고, PBT-Cursor(advisory)로 전수 순회 속성을 검증한다.

### Q6 — Fail-closed 예외 → HTTP 매핑 및 SEC-9 직렬화 경계 (Security / Error Mapping + Non-Disclosure)
도메인 예외·인가 실패·미지 오류를 어떻게 HTTP로 일반화하고, 어떤 필드를 응답에서 차단합니까? (SEC-15/INV-L4, SEC-9)

A) **Fail-closed 일반화 매핑 + 직렬화 화이트리스트**: 컨트롤러는 `DomainException` 계열을 4xx로 매핑하되 — `ValidationError`→**422**, `QuotaExceededError`→**409**, 교차 소유자/미존재(Guard DENY 일반화)→**404**, 주체 부재→**401**, 멱등 재저장/재추가→**200** — 미지 예외는 전역 핸들러에서 **500 fail-closed**로 종결하고 내부 상태를 노출하지 않는다. 응답 DTO는 공유 SSOT(`docsuri_shared`) 공개 필드만 직렬화하는 **화이트리스트** 경계를 가지며, 내부 필드(`owner_id`·`dedupe_key`·`normalized_query`·scores·audit meta)는 어떤 경로로도 직렬화되지 않는다(SEC-9). 감사 페이로드에도 민감/내부 필드를 담지 않는다(BR-L10).

B) **상세 오류 노출**: 검증 실패 위치·자원 존재 여부·내부 식별자를 응답에 포함해 디버깅 편의를 높인다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재).

[Answer]: A. B안은 SEC-9(존재 비노출)·SEC-15(fail-closed)를 정면으로 위반한다(403 vs 404 구분 노출, 내부 식별자 누출). 따라서 모든 예외는 fail-closed로 일반화 매핑한다: `ValidationError`/커서 변조/limit 범위→**422**, `QuotaExceededError`(저장 검색 200·라이브러리 1000)→**409**, 교차 소유자/미존재→Guard DENY를 **404로 일반화**(403 아님), 세션/주체 부재→**401**, 멱등 정상 재저장·재추가→**200**, 미지 예외→**500 fail-closed**(내부 상태 비노출). 직렬화는 차단(blacklist)이 아니라 **공개 필드 화이트리스트**로 설계하여 새 내부 필드가 추가돼도 기본적으로 누출되지 않게 하고, PBT-09 속성 3(내부 필드 비누출)으로 이를 차단성 테스트로 강제한다. 와이어 DTO는 `docsuri_shared` SSOT를 재사용하며 절대 포크하지 않고(브리프 §5, U3 결함 회피), `LibraryItemMeta`는 `meta: Any`를 검증하는 U4-내부 검증기이지 와이어 DTO 재정의가 아니다.

---

## 5. 산출물 목록 (Artifacts)

본 계획이 게이트를 통과하면 다음 산출물을 작성합니다.

| 산출물 경로 | 내용 | 반영 질문 |
|---|---|---|
| `construction/u4-library/nfr-design/nfr-design-patterns.md` | rerun 게이트웨이 타임아웃·서킷·Fail-Closed 격리(Q1); 이력 컨슈머 멱등·비차단·graceful 미연결(Q2); Guard 위임 + INV-L1 데이터 백스톱 이중 방어심층 및 SEC-15 예외→HTTP 매핑(Q3·Q6); BR-L5 가용성 격리 스냅샷 패턴. | Q1, Q2, Q3, Q6 |
| `construction/u4-library/nfr-design/logical-components.md` | 포트 경계 3종 + 인메모리/프로덕션 교체 시임 구조도(Q4); `UserDataDTOAndValidation`(커서 코덱·키셋 정렬 키·limit REJECT·SEC-5)(Q5); SEC-9 직렬화 화이트리스트·`get_principal` DI 시임; PBT-09(차단성)·PBT-Cursor(advisory)·CI(드리프트 가드·ruff·Hypothesis) 통합 모델. | Q4, Q5, Q6 |

> 산출물 배치·문체는 U3 `nfr-design/`(두 파일)을 정확히 미러링하며, 전역·U3 확정 사항(풀·시크릿·CORS·Redis 복원력)은 부모 정본 참조로 처리하고 재정의하지 않습니다.

---

## 6. 참조한 공유 계약 (Referenced Shared Contracts)

- **와이어 DTO (재사용·포크 금지, 브리프 §5)**: `docsuri_shared.dtos` — `PageParams, SavedSearchCreateDTO, SavedSearchDTO, SavedSearchPageDTO, LibraryItemCreateDTO, LibraryItemDTO, LibraryPageDTO, HistoryEntry, HistoryPageDTO, SearchResultSetDTO`.
- **이벤트 (🔒FROZEN)**: `docsuri_shared.events.SearchExecutedEvent` (at-least-once 소비 → 디덥 멱등 기록, INV-L3).
- **인가/주체 (U3 SEC-8 단일 권위점, 재정의 금지)**: `backend.modules.accounts.models`(Principal/Action/AccountId/Decision) + `backend.modules.accounts.guard`(AuthorizationGuard).
- **app-shell 시임**: `backend/wiring.py`(`_mount_library`·`_INTEGRATIONS`·`MountResult.mounted`), `backend/app.py`(`create_app`), `backend/config.py`(Settings).
- **카드 필드 정합(가용성 격리, BR-L5)**: dtos.md §1.1 ResultCardVM(title·authors·year·arxivId·abstractSnippet·arxivUrl) — `LibraryItemMeta`가 미러링.
- **상위 NFR/Infra 정본(상속)**: `u3-accounts/nfr-design/{nfr-design-patterns,logical-components}.md`(풀·시크릿·CORS·Redis 복원력), `u4-library/infrastructure-design/infrastructure-design.md`(RDS 테이블 3개·인덱스·이벤트 버스 이연).

---

## 7. 추적성 요약 (Traceability)

| NFR Design 결정 | 반영 질문 | 근거 ID |
|---|---|---|
| rerun = SearchGatewayPort 경유 Fail-Closed(3.0초 타임아웃 + 서킷), 백도어 금지, rerun 경로 격리 | Q1 | D9/BR-L9, INV-L2 |
| 이력 컨슈머 멱등(exactly-once)·비차단·graceful 미연결, 버스/DLQ 이연 | Q2 | D6/BR-L6·D7/BR-L7, INV-L3, NFR-P1 |
| Guard 위임(SEC-8) + 구조적 owner-scoping(INV-L1) 이중 방어심층, DENY→404 일반화 | Q3 | D11, SEC-8, SEC-9, INV-L1, INV-L4 |
| 포트 3종(`typing.Protocol`) + DI 오버라이드 시임, 인메모리 기본 ↔ 프로덕션 어댑터 | Q4 | D10/D9/D12, 브리프 §7·§8 |
| 불투명 base64 키셋 커서 + limit REJECT(422) + owner-scoped 복합 인덱스 | Q5 | D8/BR-L8, SEC-5 |
| Fail-closed 예외→HTTP 일반화 매핑 + SEC-9 직렬화 화이트리스트 | Q6 | SEC-15/INV-L4, SEC-9, BR-L10, PBT-09 |
| 전역·U3 확정 사항(풀·시크릿·CORS·Redis 복원력) 상속·비재정의 | §1 상속 선언 | U3 `nfr-design/` 정본 |
