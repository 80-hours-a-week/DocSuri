# u4-library-code-generation-plan.md — U4 Library 코드 생성 계획서

**단계**: CONSTRUCTION → Code Generation (Part 1 - Planning) · **유닛**: U4 Library · **일자**: 2026-06-17
**근거(SSOT)**: `tmp/u4-design-brief.md` (D1~D12 결정 + BR-L1..L10 + INV-L1..L4 + PBT-09), `construction/u4-library/functional-design/` (도메인 엔티티, 비즈니스 규칙), `construction/u4-library/nfr-requirements/` (기술 스택), `construction/u4-library/infrastructure-design/` (영속화 전략), `shared/dtos/library.schema.json` + `shared/python/src/docsuri_shared/dtos.py` (와이어 DTO SSOT), `shared/events/search-executed.schema.json` (🔒FROZEN 이력 이벤트)
**소유**: Track 2 (@revenantonthemission) · Track 2 흐름 = U3 Accounts → **U4 Library** (최종 유닛)
**재사용 권위점**: 인가는 U3 `backend.modules.accounts.guard.AuthorizationGuard` + `backend.modules.accounts.models`(`Principal`/`Action`/`AccountId`/`Decision`)를 위임/재사용한다(SEC-8 단일 권위점 — 재정의 금지).
**문서 언어**: 한국어 (안정 ID·경로·약어는 영어)

---

## 1. 유닛 컨텍스트 및 구현 대상 (Step 1 & Step 3)

U4 Library 유닛은 인증된 사용자의 **소유자 비공개(owner-private)** 데이터 평면을 담당하는 핵심 CRUD + 이벤트 소비 모듈입니다. 저장 검색(Saved Searches), 라이브러리(Library), 검색 이력(Search History)의 세 서브도메인을 제공하며, 각 자원은 소유자 1인에게만 노출됩니다. 인가의 단일 권위점은 U3 `AuthorizationGuard`(SEC-8)이고, U4는 이를 재정의하지 않고 위임합니다. 와이어 DTO는 `docsuri_shared` SSOT를 재사용하며(포크 금지 — U3가 범한 결함을 회피), U4는 브리프 §3 정제(최대 limit 100, 타입 meta, 문자열 id, 커서 시맨틱)를 **자체 검증 계층**(`UserDataDTOAndValidation`)에서 강제합니다.

### 1.1. 구현 대상 스토리 (Story Mapping)
- **US-L1 (저장 검색 — FR-8)**: 검색 질의를 정규화·멱등 저장(`(owner_id, normalized_query)` 유일), 라벨 관리, 200개 쿼터, 목록 페이지네이션, 삭제, 게이트웨이 경유 재실행(rerun).
- **US-L2 (라이브러리 — FR-9)**: 논문을 `(owner_id, arxiv_id)` 단위 멱등 추가(메타 스냅샷 verbatim 보존 — 가용성 격리), 1000개 쿼터, 목록 페이지네이션, 삭제.
- **US-L3 (검색 이력 — FR-10)**: `SearchExecutedEvent`(🔒FROZEN) at-least-once 소비를 통한 디덥 멱등 기록, 최근 500건 롤링 보존, 목록 페이지네이션, 게이트웨이 경유 재실행, 전체 삭제(clear). 이력 WRITE는 이벤트 구동(consumer)이며 공개 POST가 아님.
- **US-H1 (히어로 스토리 — 통합 플로우 의존)**: 가입→검색→저장/이력 조회로 이어지는 엔드투엔드 흐름에서 U4가 인증된 주체(`Principal`)를 기반으로 소유자 데이터를 안전하게 제공.

### 1.2. 타 모듈 의존성 및 인터페이스
- **`docsuri_shared.dtos`** (와이어 DTO SSOT, 재정의 금지): `PageParams`, `SavedSearchCreateDTO`, `SavedSearchDTO`, `SavedSearchPageDTO`, `LibraryItemCreateDTO`, `LibraryItemDTO`, `LibraryPageDTO`, `HistoryEntry`, `HistoryPageDTO`, `SearchResultSetDTO`. 모두 camelCase 필드(`createdAt`/`addedAt`/`executedAt`/`arXivId`/`nextCursor`/`resultCount`), `extra='forbid'`, `id`/`meta`=`Any`, `limit` `ge=1`(상한 없음).
- **`docsuri_shared.events`**: `SearchExecutedEvent` (🔒FROZEN — 이력 기록의 입력 이벤트).
- **U3 재사용** (`backend.modules.accounts`): `models.Principal`, `models.Action`, `models.AccountId`, `models.DomainException`(예외 베이스 관용구), `guard.AuthorizationGuard`, `guard.Decision`. SEC-8 단일 인가 권위점이므로 U4에서 절대 재정의하지 않음.
- **U6 (런타임 주입)**: `request.state.principal`은 U6 게이트웨이 미들웨어가 설정. `SearchGatewayPort`의 실제 바인딩(U6 `ApiGatewayMiddleware` → U2)도 U6/Infra에서 주입(U4는 `StubSearchGateway`만 탑재).

### 1.3. 소유 데이터 엔티티 및 스토어
- **InMemoryUserDataRepository** (기본): 프로세스 내 dict 기반 3개 서브-리포(saved/library/history) 집계. app-shell이 라이브 DB 없이 마운트 + 테스트 그린(mock-first, discovery와 동일 전략). (D10)
- **SqlUserDataRepository** (프로덕션 스캐폴드): SQLAlchemy 모델 + 구현. U3의 RDS PostgreSQL을 상속(NFR/Infra). 모든 질의는 구조적으로 owner-scoped (INV-L1, SEC-8 데이터 백스톱, NFR-R1).
- **DDL 마이그레이션**: `saved_searches` / `library_items` / `search_history` 3개 테이블 + owner-scope 인덱스 + 유일성 제약(`(owner_id, normalized_query)`, `(owner_id, arxiv_id)`, `dedupe_key`).

---

## 2. 상세 코드 생성 계획 (Step 2)

> 코드 작성 경로는 `backend/modules/library/`(패키지 namespace `backend.modules.library`) 및 `tests/library/`입니다.
> 모든 생성 작업은 아래 순서대로 차례로 진행되며, 완료 시 `[ ]` → `[x]` 처리됩니다.
> 규약: pydantic v2 · FastAPI `APIRouter` · `async` 엔드포인트 · `Depends` DI · 도메인 예외는 `DomainException` 서브클래스 · timezone-aware UTC(`datetime.now(UTC)`, `utcnow()` 금지) · ruff(line-length 100, select E/F/I/UP/B) · 신규 서드파티 의존성 없음(sqlalchemy/pydantic 기존, hypothesis는 dev dep).

### Phase 1: 패키지 스케폴딩 및 도메인 기반 (Foundation)

- [ ] **Step 1: 패키지 디렉터리 및 `__init__.py` 스케폴딩**
  - 경로: `backend/modules/library/__init__.py`, `backend/modules/library/repository/__init__.py`, `backend/modules/library/services/__init__.py`
  - 내용: 브리프 §7 파일 레이아웃대로 패키지 뼈대 생성. 최상위 `__init__.py`는 모듈 식별·버전 docstring만 두고 무거운 import는 피한다(app-shell의 lazy import 관용구와 호환).
  - 스토리: US-L1, US-L2, US-L3

- [ ] **Step 2: 도메인 엔티티 · 값 객체 · 도메인 예외 정의**
  - 경로: `backend/modules/library/models.py`
  - 내용: 와이어 DTO와 분리된 **내부 도메인 엔티티** 정의 — `SavedSearch`(`id`, `owner_id`, `query`, `label`, `normalized_query`, `created_at`), `LibraryItem`(`id`, `owner_id`, `arxiv_id`, `meta: LibraryItemMeta`, `added_at`), `HistoryEntry`(내부형: `id`, `owner_id`, `query`, `executed_at`, `result_count`, `dedupe_key`). 모든 datetime은 aware UTC. `id`는 `str(uuid4)`.
  - 도메인 예외(모두 `DomainException` 서브클래스 — U3 베이스 관용구 재사용 또는 로컬 `class DomainException(Exception)` 베이스 정의 후 일관 사용): `QuotaExceededError`(BR-L2/L4 → 409), `ValidationError`(SEC-5/BR-L8 → 422; pydantic `ValidationError`와 충돌 회피 위해 `LibraryValidationError` 명명), `CursorDecodeError`(BR-L8 변조 커서 → 422), `NotFoundError`(교차 소유자/미존재 일반화 → 404).
  - **재사용**: `Principal`/`Action`/`AccountId`/`Decision`는 절대 재정의하지 않고 `from backend.modules.accounts.models import ...` / `from backend.modules.accounts.guard import ...` 한다(브리프 §2, SEC-8).
  - 스토리: US-L1, US-L2, US-L3 / 근거: BR-L2, BR-L4, BR-L8, INV-L4, SEC-9

- [ ] **Step 3: 와이어 DTO 재export 및 `LibraryItemMeta` 값 객체 정의**
  - 경로: `backend/modules/library/schemas.py`
  - 내용: `docsuri_shared.dtos`에서 §1.2의 10개 DTO를 import하여 **thin re-export**(U4 내부 코드가 일관된 import 표면을 갖도록)하고, `docsuri_shared.events.SearchExecutedEvent`를 re-export한다. **DTO를 절대 재정의하지 않는다**(브리프 §5 — 포크 = U3 결함).
  - `LibraryItemMeta`(pydantic v2 모델, U4 내부 validator) 정의: `title: str`(필수 ≤500), `authors: list[str]`(각 ≤200, 길이 ≤50), `year: int | None`(1900..2100), `arxiv_id: str`, `abstract_snippet: str | None`(≤1000), `arxiv_url: str | None`. `model_config = ConfigDict(extra='forbid')`. U2 `ResultCardVM` 카드 필드(dtos.md §1.1)를 미러링 — 가용성 격리. 이는 `meta: Any`의 **검증기**이지 와이어 DTO의 재정의가 아님(브리프 §5).
  - 스토리: US-L1, US-L2, US-L3 / 근거: BR-L5, SEC-5, 브리프 §5

- [ ] **Step 4: `UserDataDTOAndValidation` — 검증·매핑·정규화·커서 코덱 (SEC-5)**
  - 경로: `backend/modules/library/validation.py`
  - 내용: U4의 검증/매핑 단일 계층. 다음을 구현한다.
    - **SEC-5 검증**: `query` ≤ 500, `label` ≤ 200, `arxiv_id` 정규형 `^\d{4}\.\d{4,5}(v\d+)?$` **또는** 레거시 `^[a-z\-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$`, page `limit` 1..100, `meta`는 `LibraryItemMeta` 경계. 위반 → `LibraryValidationError`(컨트롤러가 422 + 일반화 메시지로 매핑).
    - **정규화(BR-L1)**: `normalize_query(q) = casefold(collapse_ws(strip(NFC(q))))`. `arxiv_id` 정규화 = NFC + strip(표시형·버전 보존, BR-L3).
    - **`validate_and_map`**: 생성 DTO(`SavedSearchCreateDTO`/`LibraryItemCreateDTO`) → 검증 → 내부 도메인 엔티티 매핑. `to_dto`: 내부 엔티티 → 와이어 DTO(공개 필드만; **내부 필드 `owner_id`/`dedupe_key`/`normalized_query` 비누출** — SEC-9).
    - **커서 코덱(BR-L8)**: `encode_cursor({"ts": <sort instant ISO>, "id": <id>}) -> URL-safe base64`, `decode_cursor(token) -> dict`. 디코드/스키마 검증 실패 → `CursorDecodeError`(→ 422). 첫 페이지는 cursor 부재, 마지막 페이지는 `nextCursor` 부재.
    - **`PageParams` 정제**: shared `limit ge=1`(상한 없음) 위에 U4가 **max 100 REJECT**(클램프 아님 → 422)와 `limit < 1` → 422를 강제.
  - 스토리: US-L1, US-L2, US-L3 / 근거: SEC-5, BR-L1, BR-L3, BR-L8, SEC-9, PBT-09

- [ ] **Step 5: 포트 정의 (`typing.Protocol`)**
  - 경로: `backend/modules/library/ports.py`
  - 내용: 세 포트를 `typing.Protocol`로 정의(런타임 의존성 역전 — discovery 포트 관용구와 동일).
    - **`UserDataRepository`**: 3개 서브도메인 read/write 집계(save/get/list/delete saved-search; add/get/list/delete library; record/list/clear history; count_* for quota). 모든 메서드 시그니처에 `owner_id`를 명시 인자로 받아 owner-scoping을 구조적으로 강제(INV-L1).
    - **`SearchGatewayPort`**: `async def search(query: str, principal: Principal) -> SearchResultSetDTO`. 게이트웨이-프론트 재실행 단일 경로(INV-L2 — U2 직접 import 금지).
    - **`AuditSink`**: `def emit(event_name: str, owner_id: str, payload: dict) -> None` (또는 async) — 변이 연산 감사(BR-L10). 민감/내부 필드 비포함(SEC-9).
  - 스토리: US-L1, US-L2, US-L3 / 근거: INV-L1, INV-L2, BR-L10, D10

### Phase 2: 영속화 계층 (Repository)

- [ ] **Step 6: `InMemoryUserDataRepository` — 기본 구현 (mock-first)**
  - 경로: `backend/modules/library/repository/memory.py`
  - 내용: `UserDataRepository` 포트의 in-memory 기본 구현 + 3개 내부 서브-리포(saved/library/history). 프로세스 내 dict(`owner_id` → 정렬된 컬렉션)로 보관. **모든 read/write는 `owner_id`로 구조적 필터링**(INV-L1; 타 소유자 행 반환 불가).
    - 저장 검색: `(owner_id, normalized_query)` 유일성 인덱스로 멱등 upsert(BR-L1), `count`로 200 쿼터 검사(BR-L2).
    - 라이브러리: `(owner_id, arxiv_id)` 멱등 add(기존 반환·메타 비덮어쓰기, BR-L3/L5), `count`로 1000 쿼터(BR-L4).
    - 이력: `dedupe_key` 멱등 insert(INV-L3/BR-L7), 기록 시 소유자별 최근 500 초과분 oldest 프루닝(BR-L6), `clear`로 전체 삭제.
    - 키셋 페이지네이션: `(sort instant DESC, id DESC)` 정렬로 최신순, cursor 이후 limit건 슬라이스(BR-L8).
  - 스토리: US-L1, US-L2, US-L3 / 근거: D10, INV-L1, BR-L1~L8

- [ ] **Step 7: `SqlUserDataRepository` — SQLAlchemy 프로덕션 스캐폴드**
  - 경로: `backend/modules/library/repository/sql.py`
  - 내용: SQLAlchemy ORM 모델(`SavedSearchRow`/`LibraryItemRow`/`HistoryEntryRow`) + `UserDataRepository` 포트 구현. U3 `repository/credential.py`의 세션 주입 관용구를 따른다(`get_db_session` 시드 DI). **모든 쿼리는 `.filter(owner_id == ...)`로 owner-scoped**(INV-L1). 유일성/멱등은 DB 제약(unique index)으로도 백업하되, in-memory와 동일 의미를 보장. JSON 컬럼에 `meta` 스냅샷 저장(verbatim). 키셋 페이지네이션은 `(sort_col, id) < (cursor_ts, cursor_id)` 조건 + `ORDER BY ... DESC LIMIT`.
  - 스토리: US-L1, US-L2, US-L3 / 근거: D10(프로덕션), INV-L1, NFR-R1

- [ ] **Step 8: DDL 마이그레이션 스크립트 작성**
  - 경로: `backend/modules/library/migrations/001_create_library_tables.sql`
  - 내용: 3개 테이블 DDL — `saved_searches`(+ `UNIQUE(owner_id, normalized_query)`), `library_items`(+ `UNIQUE(owner_id, arxiv_id)`, `meta JSONB`), `search_history`(+ `UNIQUE(owner_id, dedupe_key)`). 각 테이블에 owner-scope 조회용 복합 인덱스(`(owner_id, <sort_col> DESC, id DESC)`)로 키셋 페이지네이션 성능 확보. U3 `001_create_accounts_table.sql` 스타일/주석 관용구 일치.
  - 스토리: US-L1, US-L2, US-L3 / 근거: D10, NFR-R1, INV-L1

### Phase 3: 비즈니스 로직 서비스 (3 Services)

- [ ] **Step 9: `SavedSearchService` 구현 (US-L1)**
  - 경로: `backend/modules/library/services/saved_search.py`
  - 내용: `save`(정규화→멱등 upsert, 쿼터 200 검사, 신규 시 감사 발행 / 멱등 재저장 시 라벨만 갱신·`created_at` 보존), `list`(키셋 페이지), `delete`(소유 검증 후 삭제·감사), `rerun`(저장 질의 resolve → `SearchGatewayPort.search` 호출 — **U2 직접 호출 금지**, INV-L2). 모든 메서드는 `Principal`을 받아 변이/조회 전에 `AuthorizationGuard.authorize(principal, action, AccountId(owner_id))`로 위임 검증.
  - 스토리: US-L1 / 근거: BR-L1, BR-L2, BR-L9, BR-L10, INV-L2, SEC-8

- [ ] **Step 10: `LibraryService` 구현 (US-L2)**
  - 경로: `backend/modules/library/services/library.py`
  - 내용: `add`(`meta` SEC-5 검증 → `(owner_id, arxiv_id)` 멱등 add; 재추가 시 기존 LibraryItem 동일 shape 200 반환·**메타 스냅샷 비덮어쓰기**; 신규 시 쿼터 1000 검사 + 감사), `list`(키셋 페이지, 저장된 메타 verbatim 반환 — 가용성 격리), `remove`(소유 검증 삭제·감사). 인가 위임 동일.
  - 스토리: US-L2 / 근거: BR-L3, BR-L4, BR-L5, BR-L10, SEC-8

- [ ] **Step 11: `SearchHistoryService` 구현 (US-L3)**
  - 경로: `backend/modules/library/services/history.py`
  - 내용: `record_search`(이벤트 → 내부 엔티티; `dedupe_key = sha256(owner_id|executed_at.isoformat()|query)` 계산; **디덥 멱등 insert** — 재전달 시 중복 행 없음, INV-L3/BR-L7; 기록 후 최근 500 초과분 프루닝, BR-L6), `list`(키셋 페이지), `rerun`(이력 질의 resolve → `SearchGatewayPort.search`, INV-L2), `clear`(소유자 이력 전체 삭제·감사). consumer가 호출하는 `record_search`는 멱등·예외 안전.
  - 스토리: US-L3 / 근거: BR-L6, BR-L7, BR-L9, BR-L10, INV-L2, INV-L3

### Phase 4: 게이트웨이 스텁 및 이력 컨슈머

- [ ] **Step 12: `StubSearchGateway` — `SearchGatewayPort` 스텁 구현 (D9)**
  - 경로: `backend/modules/library/gateway.py`
  - 내용: `SearchGatewayPort`의 결정론적 placeholder. `search(query, principal)`은 고정/결정론적 `SearchResultSetDTO`(shared `SearchResultSetDTO` = gateway-fronted `SearchResultPageDTO` shape)를 반환. **실제 바인딩(U6 `ApiGatewayMiddleware` → U2)은 미주입** — 동일 포트 시그니처로 후속 교체. U2를 직접 import하지 않음(INV-L2 — 백도어 부재). discovery의 mock-first 관용구와 정합.
  - 스토리: US-L1, US-L3 / 근거: BR-L9, INV-L2, D9

- [ ] **Step 13: `SearchExecutedEvent` 컨슈머 구현 (이벤트 구동 WRITE)**
  - 경로: `backend/modules/library/history_consumer.py`
  - 내용: 🔒FROZEN `SearchExecutedEvent`(at-least-once)를 소비해 `SearchHistoryService.record_search`로 디덥 멱등 기록(INV-L3). 이벤트 필드(`userId`→`owner_id`/`query`/`timestamp`→`executed_at`/`resultCount`→`result_count`)를 내부 엔티티로 매핑(🔒FROZEN `search-executed.schema.json`의 소유자 키는 `userId`). 재전달 안전(동일 `dedupe_key` → no-op). 이력 WRITE는 공개 POST가 **아님**(브리프 §6) — 컨슈머만이 유일한 WRITE 경로. 실제 메시지 브로커 바인딩은 U6/Infra 주입, U4는 `SearchHistoryEventConsumer.consume(event)` 진입점만 제공(app.state.library_history_consumer).
  - 스토리: US-L3 / 근거: BR-L7, INV-L3, D7, 🔒FROZEN 이벤트

### Phase 5: API 라우터 · DI 시임 · 감사 싱크 (Controllers)

- [ ] **Step 14: 컨트롤러 — 3개 라우터 + `get_principal` + DI 시임 구현**
  - 경로: `backend/modules/library/controller.py`
  - 내용: 세 개의 FastAPI `APIRouter`(`async` 엔드포인트):
    - **`SavedSearchController`** `/library/saved-searches`: `POST /`(create), `GET /`(list, paged), `DELETE /{id}`, `POST /{id}/rerun`.
    - **`LibraryController`** `/library/items`: `POST /`(add, 멱등 200), `GET /`(list, paged), `DELETE /{id}`.
    - **`SearchHistoryController`** `/library/history`: `GET /`(list, paged), `POST /{id}/rerun`, `DELETE /`(clear). WRITE는 컨슈머 전용(공개 POST 없음).
    - **`get_principal` 의존성**: `request.state.principal`(U6 게이트웨이 미들웨어 설정) 판독; 부재 시 **401**. 테스트/스탠드얼론은 `app.dependency_overrides`로 오버라이드(브리프 §3 D11).
    - **DI 시임**: U3 `get_db_session` 스타일로 오버라이드 가능한 provider — `get_user_data_repo`, `get_search_gateway`, `get_audit_sink`, 그리고 이를 조립하는 `get_saved_search_service`/`get_library_service`/`get_history_service`. 기본 구현은 in-memory(NotImplementedError 시드 대신 in-memory 기본을 둘 수 있으나, app-shell 오버라이드와의 정합을 위해 U3 시임 관용구를 따른다).
    - **예외 → HTTP 매핑(부록 A 일반화 규칙)**: `LibraryValidationError`/`CursorDecodeError` → 422(일반화 메시지), `QuotaExceededError` → 409, Guard `DENY`/`NotFoundError` → **404**(교차 소유자/미존재 비노출, SEC-9), principal 부재 → 401, 미지 예외 → 500 fail-closed(내부 비노출). DTO에 `owner_id`/`dedupe_key`/`normalized_query` 등 내부 필드 절대 미직렬화(SEC-9).
  - 스토리: US-L1, US-L2, US-L3 / 근거: 브리프 §6, D11, INV-L4, SEC-5, SEC-9, SEC-15

- [ ] **Step 15: `AuditSink` 포트 + `InMemoryAuditSink` 구현 (SEC-13)**
  - 경로: `backend/modules/library/audit.py`
  - 내용: `AuditSink` 포트(Step 5에서 정의 시 ports.py에 둘 수도 있으나, 브리프 §7 레이아웃대로 `audit.py`에 포트 + `InMemoryAuditSink`(in-memory/no-op 기본) 동거)와 기본 구현. 변이 연산(save/delete, add/remove, clear)에서 서비스가 호출. **감사 페이로드에 민감/내부 필드(`owner_id` 원문/`dedupe_key`/`normalized_query`/scores/내부 audit meta) 비포함**(SEC-9). 실제 와이어링은 U6/ops 주입.
  - 스토리: US-L1, US-L2, US-L3 / 근거: BR-L10, SEC-13, SEC-9

### Phase 6: App-Shell 와이어링 (브리프 §8)

- [ ] **Step 16: `_mount_library` app-shell 통합 시임 추가**
  - 경로: `backend/wiring.py` (셸 소유 파일 — 라이브러리 레인만 추가)
  - 내용: `_mount_library(app, settings, result)` 추가 —
    1. `from backend.modules.library import controller as library` (부재 시 `ModuleNotFoundError` → `mount_modules`가 graceful skip).
    2. 기본 **`InMemoryUserDataRepository`** 싱글톤 + `StubSearchGateway` + `InMemoryAuditSink` 빌드(mock-first — **라이브 DB 불요로 마운트**).
    3. 컨트롤러의 repo/gateway/audit DI provider를 `app.dependency_overrides`로 오버라이드.
    4. 세 라우터 모두 `app.include_router`.
    5. `result.mounted.append("library")`.
    - `_INTEGRATIONS` 튜플에 `_mount_library` 추가. accounts의 DB 엔진 재사용 패턴은 가용하게 두되 library는 in-memory 기본(PostgreSQL을 마운트 전제로 두지 않음).
  - 스토리: US-L1, US-L2, US-L3 / 근거: 브리프 §8, D10(mock-first), app-shell graceful-skip 관용구

### Phase 7: 단위 · 속성 기반(PBT) · 통합 테스트

> 테스트 경로는 `tests/library/`(루트 스위트, `tests/accounts`와 동일 위치)입니다. app-shell 마운트 테스트는 `backend/tests/`에 둡니다.

- [ ] **Step 17: PBT-09 — DTO 라운드트립 무결성 테스트 (차단성)**
  - 경로: `tests/library/test_dto_roundtrip_pbt.py`
  - 내용: **Hypothesis** 기반 PBT-09 3속성 검증 —
    - 속성 1(엔티티→DTO 안정성): 임의 유효 엔티티 `e`의 `to_dto(e)`가 공유 DTO 검증을 항상 통과하고 결정론적.
    - 속성 2(생성 DTO 라운드트립): 유효 생성 DTO → `validate_and_map` → `to_dto` 시 공개 필드 보존(가역).
    - 속성 3(내부 필드 비누출): 두 경로 출력 어디에도 `owner_id`/`dedupe_key`/`normalized_query`/scores/audit meta 미포함(SEC-9).
    - 도메인 제너레이터(query/label/arxiv_id/meta 경계 포함), shrinking, 시드 재현성.
  - 스토리: US-L1, US-L2, US-L3 / 근거: PBT-09(차단성), QT-4, SEC-9

- [ ] **Step 18: PBT-Cursor — 키셋 페이지네이션 전수 순회 테스트 (advisory)**
  - 경로: `tests/library/test_cursor_pbt.py`
  - 내용: Hypothesis로 임의 항목 리스트를 `limit = L`로 반복 페이지네이션 시 **모든 항목 정확히 한 번씩 최신순** 수집(중복·누락 없음), 마지막 페이지 `nextCursor` 부재, 변조/손상 커서 → 422(`CursorDecodeError`) 검증.
  - 스토리: US-L1, US-L2, US-L3 / 근거: BR-L8, QT-4(advisory)

- [ ] **Step 19: 멱등성 단위 테스트 (저장 검색 · 라이브러리 · 이력)**
  - 경로: `tests/library/test_idempotency.py`
  - 내용: BR-L1(저장 검색 정규화 멱등 — 재저장 시 신규 행 없음·라벨 갱신·`created_at` 보존), BR-L3(라이브러리 `(owner,arxiv_id)` 멱등 200·메타 비덮어쓰기), BR-L7/INV-L3(이력 `dedupe_key` 재전달 시 exactly-once 행) 검증. 정규화 파이프라인(NFC/strip/collapse/casefold) 경계 케이스 포함.
  - 스토리: US-L1, US-L2, US-L3 / 근거: BR-L1, BR-L3, BR-L7, INV-L3, QT-4

- [ ] **Step 20: 소유자 범위(owner-scoping) · 일반화 404 보안 테스트**
  - 경로: `tests/library/test_owner_scoping.py`
  - 내용: INV-L1(저장소 read/write가 타 소유자 행 반환 불가) + INV-L4/SEC-9(교차 소유자 자원 접근 → **404**(403 아님), 미인증 → 401, fail-closed). `AuthorizationGuard` 위임 경로(`DENY` → 404 일반화)와 DTO 내부 필드 비누출(`owner_id` 부재)을 단언.
  - 스토리: US-L1, US-L2, US-L3 / 근거: INV-L1, INV-L4, SEC-8, SEC-9

- [ ] **Step 21: 서비스 통합 단위 테스트 (쿼터 · 보존 · 게이트웨이 재실행)**
  - 경로: `tests/library/test_services.py`
  - 내용: BR-L2/L4(쿼터 200/1000 초과 → `QuotaExceededError` → 409), BR-L6(이력 최근 500 롤링 프루닝 + clear), BR-L9/INV-L2(rerun이 `SearchGatewayPort` 경유 — U2 직접 호출 부재; `StubSearchGateway`로 결정론 검증), BR-L8(`limit > 100` REJECT 422·`limit < 1` 422), BR-L10(변이 연산 시 `AuditSink` 발행·민감 필드 비포함). in-memory 리포 기반.
  - 스토리: US-L1, US-L2, US-L3 / 근거: BR-L2, BR-L4, BR-L6, BR-L8, BR-L9, BR-L10, INV-L2

- [ ] **Step 22: app-shell 마운트 통합 테스트**
  - 경로: `backend/tests/test_app_shell.py` (기존 파일 보강) — 마운트 레지스트리 단언에 `"library"` 추가
  - 내용: `_mount_library`가 라이브 DB 없이 마운트되어 `/readyz`의 `mounted`에 `"library"`가 포함되고(기존 `{"accounts", "discovery"}` → `{"accounts", "discovery", "library"}`로 갱신), 세 라우터(`/library/saved-searches`, `/library/items`, `/library/history`)가 OpenAPI에 노출됨을 확인. 미존재 모듈 graceful-skip 불변(`mount_modules` never-raises)은 유지. `get_principal` 오버라이드로 인증 경로 스모크.
  - 스토리: US-L1, US-L2, US-L3 / 근거: 브리프 §8, app-shell 모듈 레지스트리 불변

### Phase 8: 문서화 및 코드 요약

- [ ] **Step 23: 모듈 README 작성**
  - 경로: `backend/modules/library/README.md`
  - 내용: 세 서브도메인 엔드포인트 요약(브리프 §6), 와이어 DTO 재사용 정책(포크 금지), in-memory 기본 / SQL 스캐폴드 전환, `get_principal` 오버라이드(테스트/스탠드얼론), `StubSearchGateway`·`InMemoryAuditSink` 교체 지점(U6/ops), HTTP 상태 매핑(부록 A) 가이드. U3 README 스타일 일치.
  - 스토리: US-L1, US-L2, US-L3

- [ ] **Step 24: 코드 생성 요약(code-summary) 작성**
  - 경로: `aidlc-docs/construction/u4-library/code/code-summary.md`
  - 내용: 생성 산출물 인벤토리(파일별 책임·근거 ID), BR-L1..L10 / INV-L1..L4 / SEC-5·8·9·13·15 / PBT-09 충족 매트릭스, 미주입 시임(SearchGatewayPort 실 바인딩·메시지 브로커·실 AuditSink·SQL 리포 프로덕션 배선)과 후속 통합(U6/Infra) 책임 경계 명시. 테스트 커버리지(PBT 2종 + 멱등/소유범위/서비스/마운트) 요약.
  - 스토리: US-L1, US-L2, US-L3

---

## 3. 완료 기준 (Completion Criteria)

1. `backend/modules/library/`에 브리프 §7 파일 레이아웃의 24개 코드 생성 단계가 모두 완료되어 체크박스 `[x]` 표시됨(foundation → repository → 3 services → gateway stub → history consumer → controllers → audit → app-shell wiring → tests → code-summary).
2. 와이어 DTO는 `docsuri_shared`에서 재사용(재정의/포크 금지). U4 정제(max limit 100, 타입 `LibraryItemMeta`, 문자열 id, 커서 시맨틱)는 `UserDataDTOAndValidation` 자체 검증 계층에서 강제 — 재생성 바인딩 설치 여부와 무관하게 정합.
3. 인가는 U3 `AuthorizationGuard`(SEC-8 단일 권위점)에 위임하고 `Principal`/`Action`/`AccountId`/`Decision`을 재사용(재정의 금지). 교차 소유자/미존재 → 404 일반화(SEC-9), 미인증 → 401, fail-closed(INV-L4/SEC-15).
4. `tests/library/`에 Hypothesis PBT 2종(PBT-09 차단성 + PBT-Cursor advisory) + 멱등성·소유자범위·서비스·일반화 404 단위 테스트가 작성되고, `backend/tests/test_app_shell.py`에 `library` 마운트(라이브 DB 불요)가 검증됨.
5. 모든 컴포넌트가 INV-L1(owner-scoping 백스톱)·INV-L2(재실행 백도어 부재)·INV-L3(이력 멱등)·INV-L4(fail-closed 인가)와 SEC-5/SEC-9/SEC-13 불변식을 충족하고, ruff(line-length 100, E/F/I/UP/B) clean·신규 서드파티 의존성 없음·aware UTC 규약을 준수함.
