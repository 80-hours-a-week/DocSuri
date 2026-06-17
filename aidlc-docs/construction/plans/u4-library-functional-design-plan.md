# u4-library-functional-design-plan.md — Functional Design 계획 + 결정 게이트(답변 완료)

**단계**: CONSTRUCTION → Functional Design (유닛별 루프, Track 2 두 번째·최종 유닛) · **유닛**: U4 Library · **일자**: 2026-06-17
**소유**: Track 2 (@revenantonthemission). Track 2 흐름 = U3 Accounts → **U4 Library**(최종 유닛).
**근거(SSOT)**: `aidlc-docs/inception/` — `unit-of-work.md`, `unit-of-work-story-map.md`, `application-design/{components,component-methods,services,component-dependency}.md`, `user-stories/stories.md`(epic 3, US-L1/L2/L3), `requirements/requirements.md`; 공유 계약 `shared/dtos/library.schema.json`, `shared/events/search-executed.schema.json`, `construction/shared/dtos.md §3·§1.1`, `events.md §2`; 템플릿 `aidlc-docs/construction/u3-accounts/**` + `backend/modules/accounts/**`.
**원칙**: 이 단계는 **기술 무관(technology-agnostic)** — 비즈니스 로직·도메인 모델·비즈니스 규칙만 설계합니다. 구체적인 영속화 엔진(InMemory/SQLAlchemy/PostgreSQL), 커서 코덱 구현, 게이트웨이 바인딩은 **NFR Requirements/NFR Design/Infra Design**에서 확정합니다.
**상태 주의**: 본 계획서의 결정 게이트(D1~D12)는 모두 **권장 기본값으로 답변 완료(ANSWERED)** 상태로 기록합니다. 각 결정은 `aidlc-docs/.../u4-design-brief.md`(오케스트레이터 SSOT)에서 확정된 값을 그대로 반영하며, **리뷰 게이트에서 사용자 override가 가능**합니다.

---

## 1. 유닛 컨텍스트 (Step 1 — Analyze Unit Context)

- **책임**: 인증된 사용자의 **검색 저장(Saved Searches)·라이브러리(Library)·검색 이력(Search History)** 세 가지 소유자-사설(owner-private) 하위 도메인에 대한 동기 CRUD 및 검색 이력 이벤트 소비를 제공합니다. 모든 데이터는 소유자 단위로 격리되며(SEC-8 데이터 레이어 백스톱), 라이브러리는 추가 시점의 메타 스냅샷을 보존하여 **U2/라이브 인덱스에 비의존(가용성 격리)**으로 카드를 렌더링합니다.
- **스토리**:
  - **US-L1**: 검색 저장 (FR-8) — `SavedSearchController` / `SavedSearchService` / `SavedSearchRepository`
  - **US-L2**: 라이브러리(논문 보관) (FR-9) — `LibraryController` / `LibraryService` / `LibraryRepository`
  - **US-L3**: 검색 이력 (FR-10) — `SearchHistoryController` / `SearchHistoryService` / `SearchHistoryRepository`
- **하위 도메인(3) + 횡단 컴포넌트(2)**:
  - **Saved Searches** / **Library** / **Search History** — 각 컨트롤러·서비스·리포지토리 3계층.
  - **UserDataRepository**: 3개 서브-리포지토리를 집합하는 포트(소유자-스코핑 데이터 백스톱).
  - **UserDataDTOAndValidation**: DTO 매핑 + SEC-5 검증 + PBT-09 라운드트립 책임.
- **재사용 컴포넌트(U3 단일 권위)**: `Principal`, `Action`, `AccountId`, `Decision`는 `backend.modules.accounts.models` + `backend.modules.accounts.guard`에서 **재사용**합니다. U3는 SEC-8 소유권 인가의 단일 권위점이므로 U4에서 재정의하지 않습니다.
- **공유 계약(재사용 — 포크 금지)**: `shared/dtos/library.schema.json`(언어중립 SSOT) → `docsuri_shared.dtos`의 생성 pydantic 모델(`PageParams, SavedSearchCreateDTO, SavedSearchDTO, SavedSearchPageDTO, LibraryItemCreateDTO, LibraryItemDTO, LibraryPageDTO, HistoryEntry, HistoryPageDTO, SearchResultSetDTO`), `shared/events/search-executed.schema.json` → `docsuri_shared.events.SearchExecutedEvent`(🔒FROZEN).
- **핵심 트레이스**: FR-8, FR-9, FR-10, SEC-5(입력 검증), SEC-8(소유권 인가/소유자 스코핑), SEC-9(존재 비노출·내부 필드 비직렬화), SEC-13(감사 이벤트), SEC-15(Fail-Closed), QT-4(멱등성), PBT-09(DTO 라운드트립 — Partial 프로파일에서 advisory이나 U4 component-methods가 핀하므로 구현).

---

## 2. Functional Design 실행 계획 (Step 2)

> 결정 게이트(§4) 답변이 모두 확정되었으므로, 아래 3개 FD 산출물을 `aidlc-docs/construction/u4-library/functional-design/` 디렉터리에 작성합니다. (U3 FD 산출물 구조를 그대로 미러링)

- [ ] **domain-entities.md** — U4 도메인 엔티티 및 값 객체(Value Object) 정의 (기술 무관, 와이어 DTO와 분리)
  - 검색 저장 도메인: `SavedSearch`(`id`, `owner_id`, `query`, `label?`, `normalized_query`, `created_at`)
  - 라이브러리 도메인: `LibraryItem`(`id`, `owner_id`, `arxiv_id`, `meta: LibraryItemMeta`, `added_at`), 값 객체 `LibraryItemMeta`(`title`, `authors`, `year?`, `arxiv_id`, `abstract_snippet?`, `arxiv_url?` — U2 ResultCardVM 카드 필드 미러)
  - 이력 도메인: `HistoryEntry`(`id`, `owner_id`, `query`, `executed_at`, `result_count`, `dedupe_key`)
  - 재사용 값 객체(정의 금지·참조만): `Principal`, `Action`, `AccountId`, `Decision`(U3)
  - 도메인 예외: `DomainException` 하위 — `QuotaExceededError`, `NotFoundError`, `ValidationError`(SEC-5), `InvalidCursorError`
- [ ] **business-logic-model.md** — 서비스 및 컴포넌트 알고리즘 설계
  - `SavedSearchService.save`: `normalized_query` 산출 → `(owner_id, normalized_query)` 멱등 조회 → 신규 시 쿼터(200) 검사 → 영속화 → 감사 이벤트(D12). (BR-L1, BR-L2)
  - `SavedSearchService.list / delete / rerun`: 커서 키셋 페이지네이션(최근순), 소유권 위임(D11), rerun은 `SearchGatewayPort` 경유(D9, INV-L2).
  - `LibraryService.add`: `arxiv_id` 정규화 → `(owner_id, arxiv_id)` 멱등 조회(기존 스냅샷 미덮어쓰기) → 쿼터(1000) 검사 → 메타 검증(SEC-5) → 영속화 → 감사. (BR-L3, BR-L4, BR-L5)
  - `LibraryService.list / remove`: 보존 메타 스냅샷만 반환(가용성 격리), 소유권 위임.
  - `SearchHistoryService.record`(이벤트 소비): `dedupe_key = sha256(owner_id|executed_at.isoformat()|query)` → 멱등 기록(at-least-once → exactly-once) → 캡(500) 초과 시 최오래된 항목 프루닝. (BR-L6, BR-L7, INV-L3)
  - `SearchHistoryService.list / rerun / clear`: rerun은 게이트웨이 경유, clear는 소유자 전체 삭제.
  - `UserDataDTOAndValidation`: `validate_and_map`(생성 DTO→도메인), `to_dto`(도메인→와이어 DTO, 내부 필드 비노출), `normalize`, 커서 인코딩/디코딩 코덱, SEC-5 검증.
  - `SearchGatewayPort` / `StubSearchGateway`: rerun 재진입 계약(게이트웨이-프런티드), 실 바인딩은 U6/Infra 대기.
- [ ] **business-rules.md** — 결정 규칙, 제약, 불변식, 보안 규칙, PBT 속성
  - **BR-L1**(검색 저장 dedup·멱등 / D1), **BR-L2**(검색 저장 쿼터 200 / D2), **BR-L3**(라이브러리 멱등 / D3), **BR-L4**(라이브러리 쿼터 1000 / D4), **BR-L5**(라이브러리 메타 스냅샷 / D5), **BR-L6**(이력 보존 500 롤링 / D6), **BR-L7**(이력 멱등 / D7), **BR-L8**(커서 키셋 페이지네이션 / D8), **BR-L9**(rerun 게이트웨이 경유 / D9), **BR-L10**(감사 이벤트 / D12)
  - **불변식**: INV-L1(소유자 스코핑 백스톱), INV-L2(rerun 백도어 금지), INV-L3(이력 멱등 exactly-once), INV-L4(Fail-Closed authz)
  - **보안 규칙**: SEC-9(존재 비노출·내부 필드 비직렬화), SEC-5(입력 검증·일반화 422)
  - **PBT 속성**: PBT-09(DTO 라운드트립 — 블로킹 핀), 커서 속성(advisory — 키셋 안정성)
- [ ] **추적성 매트릭스** — U4 컴포넌트/규칙/속성 → 요구사항·스토리 ID 역추적 (FR-8/9/10, SEC-5/8/9/13/15, QT-4, PBT-09).

---

## 3. 가정 (Assumptions)

- **AS-1**: 본 단계에서는 코드를 생성하지 않으며 구체 기술(InMemory vs SQLAlchemy/PostgreSQL, 커서 base64 구현, 감사 싱크 백엔드)은 NFR/Infra 단계로 위임합니다. 단, 영속화 포트는 **mock-first 기본값(InMemoryUserDataRepository)**으로 설계하여 라이브 인프라 없이도 app-shell 마운트 및 테스트가 그린이 되도록 합니다(D10).
- **AS-2**: 소유권 인가는 U3 `AuthorizationGuard.authorize(principal, action, AccountId(owner_id))`(Stateless 단일 권위)에 위임합니다. U4 비즈니스 레이어가 리소스 소유자 식별자를 조회하여 Guard에 넘기며, U4는 인가 결정 로직을 재구현하지 않습니다(D11).
- **AS-3**: 인증된 `Principal`은 U6 게이트웨이 미들웨어가 `request.state.principal`에 주입한 것을 `get_principal` 디펜던시로 읽습니다. 조립된 모놀리스가 아닌 테스트/스탠드얼론에서는 이 디펜던시를 override합니다. 미들웨어 부재 시 401(D11).
- **AS-4**: 검색 재실행(rerun)의 실제 검색 비용·근거화 훅 재적용은 **U6 ApiGatewayMiddleware → U2** 경로가 책임지며, U4는 `SearchGatewayPort` 계약과 `StubSearchGateway`(결정적 플레이스홀더)만 정의합니다. 실 바인딩은 U6/Infra 통합 시점에 주입됩니다(D9, INV-L2).
- **AS-5**: `SearchExecutedEvent`는 🔒FROZEN 공유 계약이며 at-least-once 전달을 가정합니다. 이력 쓰기는 공개 POST가 아니라 이벤트 소비자(`history_consumer`)로만 발생합니다(D7).
- **AS-6**: 와이어 DTO는 `docsuri_shared.dtos`의 생성 모델을 **재사용**하며 U4에서 재정의(포크)하지 않습니다. §3 정제값(limit max 100, typed meta, string id, 커서 시맨틱)은 U4 자체 검증 레이어(`UserDataDTOAndValidation`)에서 강제하여 재생성 바인딩 설치 여부와 무관하게 정합성을 보장합니다.

---

## 4. 결정 게이트 (Step 3 — D1~D12, `[Answer]:` 태그로 답변 완료)

> 각 결정은 질문 형태로 제시하고 **권장 기본값(recommended default)**을 `[Answer]:`로 기록합니다. 모든 답변은 **리뷰 게이트에서 사용자 override 가능**하며, 기본값은 U4 design brief §3(D1~D12)에서 확정된 값입니다. 비즈니스 규칙 매핑은 1:1입니다(BR-L1=D1 … BR-L10=D12).

### D1 — 검색 저장 중복 제거(dedup) 및 멱등성 정책 (US-L1 / SavedSearchService / BR-L1)
동일 사용자가 의미상 같은 쿼리를 반복 저장할 때, 중복 판정 기준과 재저장 동작은 어떻게 구성합니까?

A) 원본 `query` 문자열 완전 일치만 중복으로 보고, 그 외에는 항상 신규 행을 생성한다(정규화 없음 — 공백·대소문자·유니코드 차이가 중복을 유발).

B) `(owner_id, normalized_query)` 단위로 유일성을 강제한다. `normalized_query` = 유니코드 NFC → 양끝 strip → 내부 연속 공백 1칸 축약 → casefold. 재저장은 **멱등**: 기존 SavedSearch를 반환하되, 새로운 non-null `label`이 주어지면 `label`만 갱신하고 `created_at`은 보존한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 사용자가 체감하는 "같은 검색"은 표기상의 공백·대소문자·유니코드 합자 차이를 흡수해야 하므로 정규화(NFC→strip→공백 축약→casefold) 후 `(owner_id, normalized_query)` 유일성으로 판정한다. 재저장을 신규 행 생성 대신 멱등 반환으로 처리하여 쿼터(D2) 낭비와 목록 오염을 막고, 신규 `label`만 갱신·`created_at` 보존으로 사용자의 명시적 의도(라벨 갱신)만 반영한다.


### D2 — 검색 저장 쿼터(Quota) 정책 (US-L1 / SavedSearchService / BR-L2)
소유자별 저장 검색의 상한과 초과 시 동작은 어떻게 구성합니까?

A) 무제한(쿼터 미적용) — 저장 검색은 경량 데이터이므로 상한을 두지 않는다.

B) 소유자당 최대 **200**개로 제한하고, 상한 초과 저장 시도는 `QuotaExceededError`로 거부하여 HTTP **409 Conflict**로 일반화한다. (단, D1 멱등 재저장은 신규 행을 만들지 않으므로 쿼터에 영향을 주지 않는다.)

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 단일 사용자 데이터의 무한 증가는 페이지네이션·스토리지·악용 표면을 키운다. 200개는 정상 사용 패턴을 충분히 수용하면서 남용을 차단하는 합리적 상한이며, 초과 시 401/404가 아닌 409(Conflict)로 자원 상태 충돌임을 명시한다. 멱등 재저장은 쿼터를 소모하지 않는다.


### D3 — 라이브러리 추가 멱등성 정책 (US-L2 / LibraryService / BR-L3 / QT-4)
동일 논문을 라이브러리에 반복 추가할 때, 중복 판정 기준과 재추가 동작은 어떻게 구성합니까?

A) 매 추가마다 신규 행을 생성한다(중복 허용).

B) `(owner_id, arxiv_id)` 단위로 멱등하게 처리한다. `arxiv_id`는 NFC+strip된 표시 형태(버전 포함)를 사용한다. 재추가는 기존 `LibraryItem`을 동형(same shape)으로 반환(**200**)하며, **저장된 메타 스냅샷을 덮어쓰지 않는다**.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 라이브러리는 "내 논문 목록"이므로 같은 논문이 중복 표시되어선 안 된다. `(owner_id, arxiv_id)` 멱등으로 처리하되, 재추가 시 **기존 스냅샷을 보존**(미덮어쓰기)하여 사용자가 처음 담은 시점의 메타(가용성 격리 산출물)를 안정적으로 유지한다. 신규/기존 모두 동형 200을 반환하여 클라이언트가 분기 없이 처리할 수 있다. (QT-4 멱등 트레이스)


### D4 — 라이브러리 쿼터(Quota) 정책 (US-L2 / LibraryService / BR-L4)
소유자별 라이브러리 항목의 상한과 초과 시 동작은 어떻게 구성합니까?

A) 무제한(쿼터 미적용).

B) 소유자당 최대 **1000**개 항목으로 제한하고, 초과 추가 시도는 `QuotaExceededError` → HTTP **409**로 일반화한다. (D3 멱등 재추가는 신규 행을 만들지 않으므로 쿼터에 영향 없음.)

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 라이브러리 항목은 메타 스냅샷을 포함해 저장 검색보다 무겁다. 1000개는 적극적 사용자도 수용하면서 저장소·페이지네이션 비용과 남용을 통제하는 상한이며, 초과 시 409로 일관 처리한다. 저장 검색(200)보다 큰 상한을 둔 것은 라이브러리가 핵심 누적 자산이라는 사용 특성을 반영한다.


### D5 — 라이브러리 메타 스냅샷 형상 및 검증 정책 (US-L2 / LibraryService / BR-L5 / SEC-5)
라이브러리 항목이 보존하는 논문 메타(`meta`)의 형상과 검증·재조회 정책은 어떻게 구성합니까?

A) 추가 시점에 `meta`를 보존하지 않고, 목록 조회 시마다 U2/라이브 인덱스에서 최신 메타를 재조회(refetch)하여 표시한다.

B) 추가 시점의 카드 필드를 `LibraryItemMeta` 값 객체로 **스냅샷 보존**한다: `title`(필수, ≤500), `authors`(각 ≤200, 최대 50), `year?`(1900..2100), `arxiv_id`, `abstract_snippet?`(≤1000), `arxiv_url?`. 추가 시 SEC-5로 검증하고, 저장·반환은 **verbatim**(절대 U2/인덱스에서 재조회하지 않음 — 가용성 격리). 형상은 U2 ResultCardVM 카드 필드(dtos.md §1.1)를 미러링한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 라이브러리의 핵심 가치는 검색 인덱스의 가용성·변동과 무관하게 "내가 담은 논문"을 안정적으로 보여주는 것이다(가용성 격리). 따라서 추가 시점의 카드 필드를 `LibraryItemMeta`로 스냅샷 보존하고 verbatim 반환하며, U2/인덱스를 런타임에 의존하지 않는다. 와이어 DTO의 `meta: Any`는 U4-내부 pydantic 모델 `LibraryItemMeta`로 검증하되, 이는 공유 DTO의 재정의가 아니라 검증기다(SSOT 포크 금지 — D-DTO).


### D6 — 검색 이력 보존(Retention) 정책 (US-L3 / SearchHistoryService / BR-L6)
소유자별 검색 이력의 보존 규모와 정리(clear/prune) 정책은 어떻게 구성합니까?

A) 모든 이력을 영구 보존(무제한)한다.

B) 소유자당 **최근 500개**를 롤링 보존한다. 캡을 초과해 기록할 때 가장 오래된 항목을 프루닝(prune)한다. `clearHistory`는 해당 소유자의 모든 이력을 삭제한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 이력은 빈번히 추가되는 고빈도 데이터로 무제한 보존 시 스토리지·페이지네이션 비용이 선형 증가한다. 최근 500개 롤링 보존은 "최근 활동" UX 가치를 유지하면서 비용을 상한한다. 초과 시 최오래된 항목을 자동 프루닝하고, 사용자가 명시적으로 전체를 비울 수 있도록 `clearHistory`(소유자 전체 삭제)를 제공한다.


### D7 — 검색 이력 멱등성(Idempotency) 및 이벤트 소비 정책 (US-L3 / SearchHistoryService / BR-L7 / INV-L3)
`SearchExecutedEvent`(🔒FROZEN, at-least-once 전달)를 소비해 이력을 기록할 때, 중복 전달에 대한 멱등성은 어떻게 보장합니까?

A) 수신한 이벤트마다 무조건 행을 생성한다(중복 전달이 중복 이력을 만든다).

B) `dedupe_key = sha256(owner_id | executed_at.isoformat() | query)`로 멱등 키를 산출하여, **재전달이 중복 행을 만들지 않도록**(at-least-once → exactly-once) 보장한다. 이력 쓰기는 공개 POST가 아니라 이벤트 소비자에서만 발생한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). `SearchExecutedEvent`는 FROZEN 계약이며 메시징은 at-least-once를 가정하므로, 소비자는 중복 전달에 견고해야 한다. `dedupe_key = sha256(owner_id|executed_at.isoformat()|query)`로 동일 검색 실행을 결정적으로 식별하여 exactly-once 기록을 보장한다(INV-L3). 이력 쓰기를 공개 API에서 배제하고 이벤트 경로로만 한정하여 위·변조 표면을 줄인다.


### D8 — 페이지네이션(Pagination) 정책 (US-L1/L2/L3 / 모든 list 엔드포인트 / BR-L8)
컬렉션 조회(저장 검색·라이브러리·이력)의 페이지네이션 방식·한계·커서 형식은 어떻게 구성합니까?

A) 오프셋 기반(offset/limit) — 페이지 번호로 임의 접근.

B) 커서 기반 **키셋(keyset)** 페이지네이션, **최근순(most-recent-first)**. `limit` 기본 **20**, **최대 100**. 100 초과는 **REJECT → 422**(명시성 우선; 클램프 대신 거부). `cursor` = `{"ts": <정렬 기준 시각 iso>, "id": <id>}`의 URL-safe base64(불투명). 첫 페이지는 cursor 생략, 마지막 페이지는 `nextCursor` 부재. 변조·잘못된 커서 → **422**.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 고빈도로 증가하는 컬렉션에서 오프셋 페이지네이션은 깊은 페이지에서 성능이 저하되고 동시 삽입 시 중복/누락이 발생한다. 정렬 기준 시각+id를 묶은 불투명 커서 키셋으로 안정적 최근순 순회를 보장한다(advisory 커서 속성: limit L로 순회 시 모든 항목을 중복·누락 없이 정확히 1회 수집). limit>100은 클램프하지 않고 422로 거부하여 클라이언트 계약을 명시적으로 강제하며, 변조 커서도 422로 일관 처리한다.


### D9 — 검색 재실행(Rerun) 경로 정책 (US-L1/L3 / SearchGatewayPort / BR-L9 / INV-L2)
저장 검색·이력 항목의 "다시 실행(rerun)"은 어떤 경로로 검색을 수행합니까?

A) U4가 U2 검색 컴포넌트를 직접 import/호출하여 결과를 반환한다.

B) U4는 U2를 직접 호출하지 않고 **`SearchGatewayPort`**(`search(query, principal) -> SearchResultSetDTO`)를 경유한다. 이는 게이트웨이-프런티드 검색 계약(U6 ApiGatewayMiddleware → U2)이므로 비용·근거화 훅이 재적용된다(백도어 없음). U4는 결정적 플레이스홀더 `StubSearchGateway`를 제공하고, 실 바인딩은 U6/Infra를 대기한다. `rerunSavedSearch`/`rerunHistoryEntry`는 저장된 쿼리를 해석한 뒤 포트를 호출한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). rerun이 U2를 직접 호출하면 게이트웨이의 비용 상한·근거화(grounding) 훅을 우회하는 백도어가 되어 NFR(비용 캡)·정책 일관성을 깨뜨린다(INV-L2). 따라서 rerun은 `SearchGatewayPort`를 통해 정규 검색 경로로 재진입하며, U4는 포트만 정의하고 `StubSearchGateway`로 결정적 동작을 보장한다. 실 바인딩 주입은 U6/Infra 통합 시점에 수행된다.


### D10 — 영속화(Persistence) 모델 및 소유자 스코핑 정책 (전 하위도메인 / UserDataRepository / INV-L1)
세 하위 도메인의 영속화 어댑터 구성과 소유자 스코핑 백스톱은 어떻게 구성합니까?

A) 단일 구체 구현(예: SQLAlchemy/PostgreSQL)만 두고, 마운트·테스트가 라이브 DB를 요구하도록 한다.

B) **포트 기반**으로 설계한다. 기본 구현은 **InMemoryUserDataRepository**(app-shell 마운트 + 테스트가 라이브 인프라 없이 그린 — discovery처럼 mock-first), 프로덕션 구현은 **SqlUserDataRepository**(SQLAlchemy 스캐폴드) + DDL 마이그레이션 SQL. U3의 RDS PostgreSQL을 상속(NFR/Infra). **모든 쿼리는 owner_id로 구조적으로 스코핑**한다(SEC-8 데이터 레이어 백스톱, NFR-R1 — 다른 소유자의 행을 절대 반환할 수 없음).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 포트 기반 + mock-first InMemory 기본값은 라이브 DB 없이도 app-shell 마운트와 테스트를 그린으로 유지하여(discovery 패턴) 통합 마찰을 제거하고, `SqlUserDataRepository` 스캐폴드 + DDL로 프로덕션 경로를 함께 준비한다. 모든 리포지토리 읽기/쓰기를 owner_id로 구조적 필터링(INV-L1)하여, AuthorizationGuard 결정 위에 데이터 레이어 방어선을 두는 심층 방어를 구현한다.


### D11 — 인가 위임 및 Principal 획득 정책 (전 컨트롤러 / AuthorizationGuard 위임 / INV-L4 / SEC-8 / SEC-9)
소유권 인가 결정과 인증 주체(Principal) 획득은 어떻게 구성하며, 거부·미인증 시 응답은 어떻게 일반화합니까?

A) U4가 자체 인가 규칙(소유자 비교)을 구현하고, 교차 소유자 접근은 403으로 응답한다.

B) 소유권 결정은 **U3 `AuthorizationGuard.authorize(principal, action, AccountId(owner_id))`**(단일 권위, SEC-8)에 위임한다. 교차 소유자 또는 missing principal → DENY → **HTTP 404 NotFound**로 일반화(SEC-9, 존재 비노출). 컨트롤러는 `get_principal` 디펜던시로 `request.state.principal`(U6 게이트웨이 미들웨어가 주입)을 읽으며, 부재 시 **401**. 테스트/스탠드얼론은 이 디펜던시를 override한다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 인가 로직을 U4가 재구현하면 SEC-8 단일 권위가 깨지고 정책 드리프트가 발생한다. U3 Guard에 위임(U4는 소유자 식별자만 조회·전달 — Stateless 인가)하여 결합도를 낮춘다. 교차 소유자/미인증을 403이 아닌 404로 일반화하여 리소스 존재 자체를 비노출하고(SEC-9), 어떤 인가·주체 오류도 DENY로 종결하는 Fail-Closed(INV-L4, SEC-15)를 보장한다. 세션 부재는 404가 아닌 401로 구분한다.


### D12 — 감사(Audit) 이벤트 정책 (전 서비스 / AuditSink / BR-L10 / SEC-13)
변경 연산(저장/삭제, 추가/제거, clear)에 대한 감사 로깅은 어떻게 구성합니까?

A) 감사 로깅을 두지 않는다.

B) 서비스가 변경 연산 시 **`AuditSink` 포트**를 통해 감사 이벤트를 발행한다(SEC-13). 기본 구현은 in-memory/no-op이며, 실 wiring은 U6/ops에서 주입한다. 감사 페이로드에는 **민감/내부 필드(owner userId, dedupe_key, normalized_query, 점수, 감사 메타 등)를 포함하지 않는다**(SEC-9).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (권장 기본값 — 리뷰 게이트에서 사용자 override 가능). 변경 연산의 감사 추적(SEC-13)은 보안·운영 요건이므로 `AuditSink` 포트로 일관 발행하되, 기본값은 no-op으로 두어 라이브 인프라 없이도 동작하고 실 바인딩을 U6/ops로 위임한다. 감사 페이로드에서 내부·민감 식별자를 배제하여 로그 노출 표면을 최소화한다(SEC-9). 이는 D10/D9/D12의 일관된 포트-기반·mock-first·실배선-지연 패턴을 따른다.

---

## 5. FD 산출물 목록 및 범위 (FD Artifacts & Scope)

본 FD 단계는 다음 **3개 산출물**을 생성합니다 (`aidlc-docs/construction/u4-library/functional-design/`):

| 산출물 | 내용 | 핵심 트레이스 |
|---|---|---|
| **domain-entities.md** | `SavedSearch`, `LibraryItem`, `HistoryEntry` 엔티티 + `LibraryItemMeta` 값 객체 + 도메인 예외; U3 재사용 값 객체(`Principal`/`Action`/`AccountId`/`Decision`) 참조 | FR-8/9/10, SEC-5, SEC-9 |
| **business-logic-model.md** | `SavedSearchService`/`LibraryService`/`SearchHistoryService` 알고리즘, `UserDataDTOAndValidation`(매핑·정규화·커서 코덱·SEC-5), `SearchGatewayPort`/`StubSearchGateway`, 이력 이벤트 소비자 | FR-8/9/10, SEC-8, D1~D12 |
| **business-rules.md** | BR-L1~BR-L10, 불변식 INV-L1~L4, 보안 규칙(SEC-5/9), PBT 속성(PBT-09 블로킹 + 커서 advisory), 추적성 매트릭스 | FR-8/9/10, SEC-5/8/9/13/15, QT-4, PBT-09 |

**범위(In-Scope)**: 세 하위 도메인의 동기 CRUD 비즈니스 로직, 멱등·쿼터·보존·페이지네이션 규칙, 이력 이벤트 멱등 소비, rerun 게이트웨이 경유 계약, 소유자 스코핑·인가 위임·감사 포트 설계(기술 무관).
**범위 외(Out-of-Scope, 후속 단계 위임)**: 구체 영속화 엔진·DDL·SQLAlchemy 모델(NFR/Infra), 커서 base64 구현 디테일(NFR Design), `StubSearchGateway`의 실 게이트웨이 바인딩(U6/Infra), `AuditSink` 실 백엔드(U6/ops), `get_principal` 미들웨어 주입의 물리적 배선(U6), app-shell `_mount_library` 코드(Code Generation).

---

## 6. 추적성 요약 (Decision → BR → 요구사항)

| 결정 | 비즈니스 규칙 | 불변식 | 요구사항/스토리 | 보안 트레이스 |
|---|---|---|---|---|
| D1 검색 저장 dedup·멱등 | BR-L1 | — | FR-8, US-L1 | — |
| D2 검색 저장 쿼터 200 | BR-L2 | — | FR-8, US-L1 | — |
| D3 라이브러리 멱등 | BR-L3 | — | FR-9, US-L2 | QT-4 |
| D4 라이브러리 쿼터 1000 | BR-L4 | — | FR-9, US-L2 | — |
| D5 라이브러리 메타 스냅샷 | BR-L5 | — | FR-9, US-L2 | SEC-5 |
| D6 이력 보존 500 롤링 | BR-L6 | — | FR-10, US-L3 | — |
| D7 이력 멱등 소비 | BR-L7 | INV-L3 | FR-10, US-L3 | — |
| D8 커서 키셋 페이지네이션 | BR-L8 | — | FR-8/9/10, US-L1/L2/L3 | SEC-5 |
| D9 rerun 게이트웨이 경유 | BR-L9 | INV-L2 | FR-8/10, US-L1/L3 | — |
| D10 포트 기반 영속화·소유자 스코핑 | — | INV-L1 | FR-8/9/10 | SEC-8 |
| D11 인가 위임·Principal 획득 | — | INV-L4 | FR-8/9/10, US-L1/L2/L3 | SEC-8, SEC-9, SEC-15 |
| D12 감사 이벤트 | BR-L10 | — | FR-8/9/10 | SEC-13, SEC-9 |
