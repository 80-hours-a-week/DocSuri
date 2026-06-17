# logical-components.md — U4 Library NFR 논리 컴포넌트 명세서

**단계**: CONSTRUCTION → NFR Design (유닛별 루프, Track 2 최종 유닛) · **유닛**: U4 Library · **일자**: 2026-06-17
**근거(SSOT)**: `tmp/u4-design-brief.md` (§1~§10, D1~D12 / BR-L1~L10 / INV-L1~L4 반영) · application-design `components.md`·`component-methods.md`·`services.md` (U4 절) · 공유 계약 `docsuri_shared.dtos`·`docsuri_shared.events`
**범위**: U4 Library의 논리 컴포넌트 지도(application-design 8 컴포넌트 → 구현 컴포넌트 매핑) + 의존성 주입(DI) 토폴로지 + app-shell 마운트 이음새. 동작 규칙·정책 수치는 FD/NFR-Req 문서에 위임하고, 본 문서는 **컴포넌트 경계·포트·주입 방향·교체 가능성**을 확정한다.

---

## 1. 논리 컴포넌트 지도 (mock-first 모듈형 모놀리스)

U4는 `backend/modules/library/` 패키지(accounts와 동일 네임스페이스)에 거주하는 동기 CRUD 도메인 모듈이며, 이력 쓰기 1건만 이벤트 드리븐이다. 모든 외부 의존성(영속화·검색·이벤트·감사)은 **포트(typing.Protocol)** 뒤에 두고, 기본 구현으로 **인메모리 mock**을 제공해 라이브 인프라 없이도 app-shell이 마운트되고 테스트가 그린으로 통과한다(§8, D10). 실 어댑터(SQL·U6 게이트웨이·이벤트 버스·ops 감사)는 동일 포트 시그니처로 스왑인된다.

```
                              ┌─────────────────────────────────────────────────────┐
   HTTP (FastAPI APIRouter)   │                  U4 Library 모듈                      │
   ─────────────────────────► │                                                      │
   /library/saved-searches    │  ┌──────────────────┐   ┌──────────────────────┐    │
   /library/items             │  │   Controllers     │   │  UserDataDTOAnd      │    │
   /library/history           │  │ (3 APIRouter)     │──▶│  Validation          │    │
                              │  │  +get_principal   │   │ (validate/to_dto/    │    │
                              │  └────────┬──────────┘   │  normalize/cursor)   │    │
                              │           │ Depends      └──────────────────────┘    │
                              │           ▼                                          │
                              │  ┌──────────────────┐         ┌─────────────────┐   │
   U3.AuthorizationGuard ◄────┼──│   Services (3)    │────────▶│   AuditSink      │   │
   (authorize, SEC-8)         │  │ SavedSearch/      │  emit   │ (InMemory 기본)  │   │
                              │  │ Library/History   │         └─────────────────┘   │
                              │  └───┬───────────┬───┘                               │
                              │      │           │ rerun()                           │
                              │      │ port      ▼                                   │
                              │      │      ┌─────────────────┐                      │
                              │      │      │ SearchGatewayPort│──▶ (U6 게이트웨이→U2) │
                              │      │      │ (StubSearchGW 기본)│                     │
                              │      ▼      └─────────────────┘                      │
                              │  ┌──────────────────────────────────────────┐       │
                              │  │  UserDataRepository (포트)               │       │
                              │  │   ├ SavedSearchRepository                │       │
                              │  │   ├ LibraryRepository                    │       │
                              │  │   └ SearchHistoryRepository              │       │
                              │  │  기본: InMemoryUserDataRepository         │       │
                              │  │  실  : SqlUserDataRepository (SQLAlchemy) │       │
                              │  └──────────────────────────────────────────┘       │
                              │                                                      │
   SearchExecutedEvent ───────┼─▶ history_consumer ──▶ SearchHistoryService.record   │
   (이벤트 버스, at-least-once)│   (멱등 dedupe_key)                                  │
                              └─────────────────────────────────────────────────────┘
```

논리 계층은 4단으로 고정한다. **Controller(HTTP 경계·인증 주체 해석) → Service(도메인 오케스트레이션·정책·인가 위임·감사 발행) → Port(Repository/SearchGateway/AuditSink) → Adapter(InMemory 기본 / SQL·U6·이벤트버스 실)**. Controller는 Repository를 직접 호출하지 않으며(서비스 경유), Service는 HTTP 타입을 모른다(DTO 매핑은 Controller가 `UserDataDTOAndValidation`을 경유). 이 경계가 INV-L1(owner-scoping 백스톱)·INV-L2(rerun 백도어 금지)·INV-L4(fail-closed authz)를 구조적으로 강제한다.

---

## 2. application-design U4 8 컴포넌트 → 구현 컴포넌트 매핑

application-design(`components.md` U4 절)의 추상 컴포넌트 8종을 본 NFR Design의 구체 구현 컴포넌트로 1:1(또는 1:N 분해)로 매핑한다. 추상 이름·trace는 보존하고, 구현 파일·기본 구현체를 확정한다(§7 file layout 정합).

| # | application-design 컴포넌트 | 구현 컴포넌트 | 구현 위치 | 기본 구현체 / 비고 | Trace |
|---|---|---|---|---|---|
| 1 | **SavedSearchController** | `SavedSearchController` 라우터 (`APIRouter(prefix="/library/saved-searches")`) | `controller.py` | FastAPI 비동기 라우터; `get_principal`·서비스 `Depends` 주입 | FR-8, US-L1, BR-L1/L2/L9 |
| 2 | **LibraryController** | `LibraryController` 라우터 (`APIRouter(prefix="/library/items")`) | `controller.py` | 멱등 add(201/200); 카드 호환 직렬화 | FR-9, US-L2, BR-L3/L4/L5 |
| 3 | **SearchHistoryController** | `SearchHistoryController` 라우터 (`APIRouter(prefix="/library/history")`) | `controller.py` | WRITE는 공개 POST 없음(이벤트 구동); list/rerun/clear만 노출 | FR-10, US-L3, BR-L6/L7/L9 |
| 4 | **SavedSearchService** | `SavedSearchService` | `services/saved_search.py` | dedup(D1)·quota(D2)·rerun via port(D9)·audit(D12) | FR-8, SEC-8, SEC-13 |
| 5 | **LibraryService** | `LibraryService` | `services/library.py` | idempotency(D3)·quota(D4)·meta 스냅샷 보존(D5)·audit | FR-9, SEC-8, SEC-13 |
| 6 | **SearchHistoryService** | `SearchHistoryService` | `services/history.py` | record(이벤트)·retention(D6)·dedupe(D7)·rerun(D9)·clear | FR-10, SEC-8, NFR-P1 |
| 7 | **UserDataRepository** | `UserDataRepository` 포트 + `InMemoryUserDataRepository`(기본) + `SqlUserDataRepository`(실); 하위 3 sub-repo | `ports.py`, `repository/memory.py`, `repository/sql.py` | 모든 질의 owner-scoped(INV-L1, SEC-8 데이터 백스톱) | SEC-8, SEC-1, RES-9, D10 |
| 8 | **UserDataDTOAndValidation** | `UserDataDTOAndValidation` (검증·매핑·정규화·커서 코덱) + `LibraryItemMeta`(value-object 검증기) | `validation.py`, `schemas.py` | SEC-5 검증·to_dto·정규화(D1)·커서(D8)·PBT-09 라운드트립 | SEC-5, SEC-9, PBT-09 |

**신설(추상에 명시되지 않은 구현 보조 컴포넌트)** — application-design은 capability 수준만 기술하므로, 구체 NFR 결정으로 다음 3개를 1급 컴포넌트로 승격한다(브리프 §2/§3/§7 정합):

| 신설 컴포넌트 | 역할 | 구현 위치 | 근거 |
|---|---|---|---|
| **SearchGatewayPort** + `StubSearchGateway` | rerun 재실행을 게이트웨이-프런티드 검색 계약(`search(query, principal) -> SearchResultSetDTO`)으로 위임하는 포트. 기본은 결정적 placeholder 스텁. | `ports.py`, `gateway.py` | D9, BR-L9, INV-L2 |
| **history_consumer** | `SearchExecutedEvent`(🔒FROZEN, at-least-once)를 구독해 `SearchHistoryService.record`로 멱등 기록. | `history_consumer.py` | D7, BR-L7, INV-L3 |
| **AuditSink** + `InMemoryAuditSink` | mutating op(save/delete·add/remove·clear) 감사 발행 포트. 기본은 no-op/인메모리. | `audit.py` | D12, BR-L10, SEC-13 |

> **참고**: `Principal`/`Action`/`AccountId`/`Decision`/`AuthorizationGuard`는 신설하지 않고 `backend.modules.accounts`(U3)에서 재사용한다(SEC-8 단일 권위, 브리프 §2). U4는 이를 import 의존만 하며 재정의하지 않는다.

---

## 3. 의존성 주입(DI) 토폴로지

accounts(U3)의 컨트롤러 DI 패턴(`get_db_session` 스텁 → app-shell 오버라이드, 서비스 조립 디펜던시)을 그대로 따른다. 차이점은 U4의 기본 어댑터가 **RDBMS가 아니라 프로세스 단위 인메모리 싱글톤**이라는 점이다(mock-first, D10/§8).

### 3.1. 주입 시드(seam) — 컨트롤러가 선언하는 오버라이더블 디펜던시

`controller.py`는 다음 5개 provider 함수를 디펜던시 시드로 노출한다. 기본 구현은 mock-first로 동작하고, app-shell(`wiring.py`)이 `app.dependency_overrides`로 교체하거나 동일 기본을 재사용한다.

| Provider (디펜던시 시드) | 반환 | 기본 구현 (mock-first) | app-shell / 테스트 오버라이드 |
|---|---|---|---|
| `get_user_data_repository()` | `UserDataRepository` | 프로세스 단위 `InMemoryUserDataRepository` 싱글톤(`lru_cache(maxsize=1)`, accounts `get_session_repo` 패턴) | `SqlUserDataRepository`(실 RDS) 또는 테스트 격리용 신규 인메모리 |
| `get_search_gateway()` | `SearchGatewayPort` | `StubSearchGateway`(결정적 placeholder) | U6 게이트웨이-프런티드 실 어댑터 |
| `get_audit_sink()` | `AuditSink` | `InMemoryAuditSink`(no-op 수집) | U6/ops 실 감사 싱크 |
| `get_principal(request)` | `Principal` | `request.state.principal` 판독; 부재 시 401 (INV-L4) | 테스트/standalone는 고정 `Principal` 주입으로 오버라이드 |
| `get_*_service(...)` | 3개 서비스 | 위 포트들을 `Depends`로 조립해 생성 | 보통 미오버라이드(포트 교체로 충분) |

### 3.2. 조립 그래프 (Depends 체인)

```
get_principal(request)            get_user_data_repository()   get_search_gateway()   get_audit_sink()
        │                                  │                          │                    │
        │                                  └────────────┬─────────────┴────────────────────┘
        │                                               ▼
        │                          get_saved_search_service(repo, gateway, audit)
        │                          get_library_service(repo, audit)
        │                          get_search_history_service(repo, gateway, audit)
        ▼                                               │
   [Controller endpoint] ◄───────── Depends ───────────┘
        │
        ├─ DTO 검증/매핑: UserDataDTOAndValidation (모듈 내 직접 호출; LibraryItemMeta로 meta:Any 검증)
        └─ 인가 결정: services → AuthorizationGuard.authorize(principal, action, AccountId(owner_id))  [U3, SEC-8]
```

- **Service → Repository**: 서비스는 포트 타입(`UserDataRepository`)만 의존하고 구현(InMemory/SQL)을 모른다. owner_id를 모든 호출에 명시 전달해 INV-L1 백스톱을 구조적으로 보장한다.
- **Service → SearchGatewayPort**: `rerun*`만 이 포트를 호출한다. U2를 직접 import/호출하지 않는다(INV-L2). 저장된 query를 해석한 뒤 `search(query, principal)`을 호출하므로 U6 근거화·비용 후크가 동일 적용된다(D9).
- **Service → AuditSink**: mutating op 직후 발행. 페이로드에 민감/내부 필드(owner_id, dedupe_key, normalized_query, scores) 비포함(SEC-9, D12).
- **Controller → UserDataDTOAndValidation**: 입력 DTO 검증·정규화·커서 디코드(요청측), 도메인→DTO 매핑·커서 인코드(응답측). 내부 필드 비직렬화(SEC-9). `LibraryItemMeta`로 `meta: Any`를 타입 검증.

### 3.3. 인메모리 싱글톤 수명주기 (accounts 패턴 재사용)

`get_user_data_repository`는 `lru_cache(maxsize=1)`로 프로세스 단위 단일 인스턴스를 보장한다. 이는 accounts의 `get_session_repo` 싱글톤 의도(요청마다 새 인스턴스 생성 방지)와 동일하다. 인메모리 어댑터는 외부 리소스를 점유하지 않으므로 shutdown cleanup은 no-op이지만, SQL 어댑터로 스왑인 시 app-shell이 accounts와 동일하게 엔진/세션 팩토리 cleanup을 등록한다(§4).

---

## 4. app-shell 마운트 이음새 (`backend/wiring.py` — `_mount_library`)

브리프 §8에 따라 `wiring.py`에 `_mount_library(app, settings, result)`를 추가하고 `_INTEGRATIONS` 튜플에 등록한다. accounts/discovery와 동일한 **선택적 마운트(optional-mount)** 규약을 따른다: 모듈 부재 시 `ModuleNotFoundError`가 `mount_modules`로 버블되어 스킵으로 강등되므로, app-shell이 트랙 PR보다 먼저 develop에 안착할 수 있다.

### 4.1. 마운트 시퀀스

```
_mount_library(app, settings, result):
    from backend.modules.library import controller as library      # 부재 시 ModuleNotFoundError → skip

    # 1) mock-first 싱글톤 구성 (라이브 DB 불필요)
    repo    = InMemoryUserDataRepository()       # 3 sub-repo 포함, owner-scoped
    gateway = StubSearchGateway()                # 결정적 placeholder
    audit   = InMemoryAuditSink()                # no-op 수집

    # 2) 컨트롤러 DI 시드 오버라이드
    app.dependency_overrides[library.get_user_data_repository] = lambda: repo
    app.dependency_overrides[library.get_search_gateway]       = lambda: gateway
    app.dependency_overrides[library.get_audit_sink]           = lambda: audit

    # 3) 3개 라우터 마운트
    app.include_router(library.saved_search_router)
    app.include_router(library.library_router)
    app.include_router(library.history_router)

    # 4) 마운트 결과 기록
    result.mounted.append("library")
```

- **mock-first 강제**: discovery의 `build_mock_orchestrator()` 마운트 의도와 동일하게, U4는 PostgreSQL/이벤트 버스/U6 게이트웨이 없이 마운트된다. accounts의 DB 엔진 재사용 패턴(`make_engine`/`make_session_factory`)은 **가용 상태로 유지**하되, U4 기본은 인메모리이므로 `_mount_library`는 RDBMS를 요구하지 않는다.
- **실 어댑터 스왑인**: 운영 전환 시 `_mount_library`에서 `repo`만 `SqlUserDataRepository(session_factory)`로, `gateway`만 U6 실 어댑터로, `audit`만 ops 싱크로 교체한다. 컨트롤러/서비스 코드는 불변(포트 시그니처 동일). SQL 경로 채택 시 accounts와 동일한 엔진/세션 cleanup을 `result.cleanups`에 등록한다.
- **`get_principal` 미오버라이드**: 조립된 모놀리스에서 인증 주체는 U6 게이트웨이 미들웨어가 `request.state.principal`에 세팅한다(D11). app-shell은 이를 오버라이드하지 않으며, standalone/테스트만 고정 Principal로 오버라이드한다.

### 4.2. history_consumer 등록

`history_consumer`는 HTTP 라우터가 아니라 이벤트 구독자다. mock-first 단계에서는 이벤트 버스가 없으므로 app-shell은 라우터만 마운트하고 consumer는 **테스트/실 이벤트 버스에서 직접 구동**한다(브리프 §8은 라우터 3종 마운트만 규정). 실 이벤트 버스 연결 시 별도 워커/구독 이음새로 `SearchHistoryService.record`에 배선하며, at-least-once → exactly-once(dedupe_key) 멱등을 보장한다(INV-L3).

---

## 5. U3 AuthorizationGuard 의존 (SEC-8 단일 권위)

U4는 객체 단위 소유권 인가를 **자체 구현하지 않고** U3 `AuthorizationGuard`에 위임한다(브리프 D11, components.md "SEC-8 객체 소유권 단일 권위"). U4 Repository의 owner-scoped 질의는 가드 결정 하위의 **데이터 계층 백스톱(심층 방어)** 이지 독자 인가 결정이 아니다(INV-L1).

### 5.1. 호출 형태

```
from backend.modules.accounts.guard import AuthorizationGuard, Decision
from backend.modules.accounts.models import Action, AccountId

decision = AuthorizationGuard.authorize(
    principal,                       # get_principal이 해석 (부재 시 401, INV-L4)
    Action.READ | WRITE | DELETE | RERUN,
    AccountId(owner_id),             # 리소스 소유자 (서비스가 먼저 조회)
)
if decision is Decision.DENY:
    raise NotFoundException(...)     # 교차 소유/부재 → 404 일반화 (SEC-9, INV-L4)
```

- **Stateless 위임**: U3 가드는 `principal`과 호출측이 먼저 조회한 `resource_owner_id`를 명시 인자로 받는 stateless 결정점이다(guard.py). U4 서비스는 리소스를 owner-scoped로 조회(또는 소유자 확정)한 뒤 가드에 결정을 위임한다.
- **fail-closed 일반화(INV-L4, SEC-9)**: `Decision.DENY`(교차 소유 또는 principal/owner 부재) → **404 NotFound** 로 일반화해 존재 여부를 비노출. principal 자체가 없으면(미세션) **401**. 어떤 authz/principal 오류도 fail-open되지 않는다(SEC-15).
- **Action 매핑**: list/get→`READ`, create/add→`WRITE`, delete/remove/clear→`DELETE`, rerun→`RERUN`(U3 `Action` enum 재사용; 신설 금지).

### 5.2. 컨트롤러 예외→HTTP 매핑 (accounts 규약 정합)

도메인 예외는 U4 `DomainException` 하위로 정의하고, 컨트롤러가 HTTP로 일반화 매핑한다(브리프 §9, accounts 컨트롤러 패턴).

| 도메인 조건 | 예외 | HTTP | 비고 |
|---|---|---|---|
| 입력 검증 실패 / 커서 변조 / limit>100 | `ValidationError` | 422 | SEC-5, D8 (REJECT) |
| 쿼터 초과(저장 200 / 라이브러리 1000) | `QuotaExceededError` | 409 | D2, D4 |
| 교차 소유 / 미존재 리소스 | `NotFoundException` (DENY 일반화) | 404 | SEC-9, INV-L4 |
| principal 부재(미세션) | — (`get_principal` 발생) | 401 | D11, INV-L4 |
| 알 수 없는 장애 | (catch-all) | 500 | fail-closed (SEC-15) |

---

## 6. 공유 계약 재사용 (SSOT 포크 금지)

U4는 wire DTO를 재정의하지 않고 `docsuri_shared`에서 import한다(브리프 §5; U3 포크 결함 회피). 본 NFR Design은 다음 계약을 컴포넌트 경계에 고정한다.

- **`docsuri_shared.dtos`** 에서 import: `PageParams, SavedSearchCreateDTO, SavedSearchDTO, SavedSearchPageDTO, LibraryItemCreateDTO, LibraryItemDTO, LibraryPageDTO, HistoryEntry, HistoryPageDTO, SearchResultSetDTO`. (camelCase·`extra='forbid'`·`id`/`meta`=Any·`limit` ge=1)
- **`docsuri_shared.events`** 에서 import: `SearchExecutedEvent` (🔒FROZEN, at-least-once) — `history_consumer` 입력.
- **U4 자체 검증 레이어(`UserDataDTOAndValidation`)** 가 §3 정밀화(limit max 100·typed meta·string id·커서 시맨틱)를 강제한다. 따라서 재생성 바인딩 설치 여부와 무관하게 U4가 정확하다. `LibraryItemMeta`는 wire DTO 재정의가 아니라 `meta: Any`의 **U4 내부 검증기**다.
- **재사용 코드 의존**: `backend.modules.accounts.models`(`Principal/Action/AccountId/Decision`) + `backend.modules.accounts.guard`(`AuthorizationGuard`).

---

## 7. mock-first ↔ 실 어댑터 교체 매트릭스

포트별 기본(mock)·실 구현을 한눈에 고정한다. **교체는 포트 시그니처를 보존한 어댑터 치환**이며, Controller/Service 코드는 어떤 경우에도 불변이다.

| 포트 (ports.py) | 기본 구현 (mock-first, 마운트/테스트 그린) | 실 구현 (운영 스왑인) | 교체 지점 | 근거 |
|---|---|---|---|---|
| `UserDataRepository` (+3 sub-repo) | `InMemoryUserDataRepository` (`repository/memory.py`) | `SqlUserDataRepository` (`repository/sql.py`, SQLAlchemy) + `migrations/001_create_library_tables.sql` | `_mount_library` / `get_user_data_repository` 오버라이드 | D10, INV-L1, SEC-1 |
| `SearchGatewayPort` | `StubSearchGateway` (`gateway.py`, 결정적 placeholder) | U6 게이트웨이-프런티드 검색 어댑터(ApiGatewayMiddleware→U2) | `_mount_library` / `get_search_gateway` 오버라이드 | D9, BR-L9, INV-L2 |
| `AuditSink` | `InMemoryAuditSink` (`audit.py`, no-op 수집) | U6/ops 감사 싱크(ObservabilityHub append-only) | `_mount_library` / `get_audit_sink` 오버라이드 | D12, BR-L10, SEC-13 |
| 이벤트 입력(`SearchExecutedEvent`) | 테스트/직접 호출 (`history_consumer`) | 실 이벤트 버스 구독 워커 | 별도 구독 이음새(§4.2) | D7, INV-L3 |

이 토폴로지는 discovery(U2)의 "real OpenSearch/Bedrock 어댑터와 U6 근거화 후크가 동일 생성자 인자로 나중에 스왑인" 원칙과 동형이며, accounts(U3)의 DI-seam 오버라이드 패턴과 동일하다. U4의 차별점은 **기본값이 인메모리라 라이브 인프라 없이 마운트·테스트 그린**이라는 것뿐이다.

---

## 8. PBT 및 검증 통합 (PBT-09 블로킹)

- **PBT-09 (DTO 라운드트립, 블로킹)**: 임의의 유효 도메인 엔티티에 대해 `to_dto(entity)`가 공유 DTO 검증을 안정 통과하고, 유효 create DTO의 `validate_and_map`이 공개 필드를 라운드트립하며 **내부 필드를 절대 누출하지 않음**을 Hypothesis로 검증한다. `validation.py`/`schemas.py`의 매핑 경계가 검증 대상이다. (브리프 §4; Partial 프로파일에서 advisory지만 U4 component-methods가 pin → 구현)
- **커서 속성(advisory)**: limit L 키셋 페이지네이션이 most-recent-first 순서로 전 항목을 중복·누락 없이 정확히 1회 수집(D8 키셋 안정성). `validation.py` 커서 코덱 대상.
- **테스트 위치**: `tests/library/` (root suite, `tests/accounts`와 동형). app-shell 마운트 검증은 `backend/tests`에 `_mount_library` 테스트로 추가(브리프 §7/§8).
- **규약 준수**: pydantic v2, async 엔드포인트, `Depends` DI, timezone-aware UTC(`datetime.now(UTC)`), ruff(line-length 100, E/F/I/UP/B). 신규 third-party 의존 없음(sqlalchemy·pydantic 기존, hypothesis는 dev 의존).
