# u4-library-code-summary.md — U4 Library 코드 생성 요약

**단계**: CONSTRUCTION → Code Generation (Track 2, **U4 = Track 2 최종 유닛**) · **일자**: 2026-06-17
**근거(SSOT)**: `construction/plans/u4-library-code-generation-plan.md`, `construction/u4-library/{functional-design,nfr-requirements,nfr-design,infrastructure-design}/`, `shared/dtos/library.schema.json`, `shared/events/search-executed.schema.json`
**검증**: `pytest tests backend/tests` → **64 passed**(library 41 + accounts 15 + app-shell 8) · `ruff check` → clean(library 레인 + app-shell)

---

## 1. 생성 산출물 (backend/modules/library/)

| 파일 | 책임 | 핵심 불변식/결정 |
|---|---|---|
| `models.py` | 도메인 엔티티(SavedSearch·LibraryItem·HistoryEntry)·예외 | 내부 필드(owner_id·normalized_query·dedupe_key) 보유; aware UTC |
| `schemas.py` | **shared DTO 재사용**(docsuri_shared.dtos) + `LibraryItemMeta` | SSOT 포크 금지; meta는 U4 로컬 검증 타입(BR-L5) |
| `validation.py` | `UserDataDTOAndValidation` — SEC-5 검증·정규화·커서 코덱·엔티티→DTO 매핑·`build_page` | SEC-9 내부필드 비직렬화; 정규화 dedup(BR-L1); 키셋 커서(BR-L8) |
| `ports.py` | Protocol: UserDataRepository(3 서브레포)·SearchGatewayPort·AuditSink | 모든 repo 메서드 owner-scoped(INV-L1) |
| `repository/memory.py` | InMemory 어댑터(기본 mock-first) | owner-scoped 딕셔너리; 키셋 페이지; 롤링 prune(BR-L6) |
| `repository/sql.py` | SQLAlchemy 프로덕션 스캐폴드 | owner-scoped 쿼리; `tuple_(...) < cursor` 키셋; 3 테이블 |
| `services/saved_search.py` | 저장검색 save/list/delete/rerun | dedup 멱등(BR-L1)·정원 200(BR-L2)·SEC-8 위임 |
| `services/library.py` | 라이브러리 add/list/remove | `(owner,arxivId)` 멱등(BR-L3)·정원 1000(BR-L4)·meta 스냅샷(BR-L5) |
| `services/history.py` | 이력 record_search(소비)/list/rerun/clear | at-least-once dedupe_key 멱등(BR-L7/INV-L3)·롤링 500(BR-L6) |
| `gateway.py` | `StubSearchGateway`(SearchGatewayPort) | rerun=게이트웨이-프런티드(INV-L2 백도어 차단) |
| `history_consumer.py` | `SearchExecutedEvent` 소비자 seam | 🔒FROZEN 이벤트 검증→record_search; userId→owner_id |
| `controller.py` | 3 라우터 + `get_principal` + DI seam | DomainException→HTTP(404 일반화 SEC-9·401 fail-closed·409·422) |
| `authz.py` | `authorize_owned` — U3 AuthorizationGuard 위임 | DENY/오류→일반화 404(INV-L4/SEC-9) |
| `audit.py` | AuditEvent + InMemoryAuditSink(SEC-13) | 민감/내부 필드 미포함 |
| `migrations/001_create_library_tables.sql` | DDL(saved_searches·library_items·search_history) | `UNIQUE(owner_id, normalized_query/arxiv_id/dedupe_key)` + 키셋 인덱스 |

## 2. 통합 (app-shell)
- `backend/wiring.py`에 **`_mount_library`** 추가(`_INTEGRATIONS` 등록). mock-first InMemory 어댑터로 **live DB 없이 마운트**; 3 라우터 include; 이력 소비자(`app.state.library_history_consumer`)가 읽기 라우터와 **동일 repo 공유**. 프로덕션은 `get_user_data_repo` override로 `SqlUserDataRepository` 주입.
- `backend/tests/test_app_shell.py` 모듈 레지스트리 단언에 `library` 추가.
- `backend/pyproject.toml` dev deps에 `hypothesis`·`pytest-asyncio` 선언(재현성).

## 3. 테스트 (tests/library/, 41건)
service(saved/library/history) 단위 + 키셋 페이지네이션 + **PBT-09 DTO 라운드트립 & SEC-9 비노출**(Hypothesis) + controller HTTP(상태코드·401·cross-owner 404·422) + **app-shell 마운트 E2E**.

## 4. 후속/유의
- ⚠️ `shared/dtos/library.schema.json` PROVISIONAL → 정제(limit max=100·`LibraryItemMeta` $def·string id·커서 의미)는 **코디네이션 존 변경**이라 별도 shared/ PR(Track3 @kyjness 사인오프)로 분리 권고. U4 코드는 로컬 검증(option-d)으로 무관하게 정상.
- rerun 실제 바인딩은 U6 게이트웨이; 이력 이벤트버스 구독은 U6/EventBridge; SQL 어댑터는 RDS 통합 시 활성. 전부 포트/seam만 제공(mock-first).
