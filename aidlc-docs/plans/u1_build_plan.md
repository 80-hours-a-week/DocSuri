# U1 Discover 빌드 — 작업 계획 (Code Generation Phase)

> **Phase**: AIDLC Construction — Code Generation (U1 진입 라운드, 백엔드 분할)
> **입력 산출물**: [`unit-u1-discover.md`](../design-artifacts/units/unit-u1-discover.md) (빌드 가능 정의 §6) · [`component-model.md §3`](../design-artifacts/component-model.md) (U1 컴포넌트·`SearchResult` §3.7 — **동결**) · [`architecture_decision_record.md`](../design-artifacts/architecture_decision_record.md) (D1·D5·D6 등) · [`unit-u0-foundation.md`](../design-artifacts/units/unit-u0-foundation.md) (포트 계약)
> **입력 범위 제약**: `aidlc-docs/` 밖 문서는 참조하지 않는다. U0 포트 시그니처는 **호출만**, 변경 금지(U1 §8).
> **승인 게이트**: 본 계획은 사용자 승인 후에만 실행. ✅ 승인 완료(2026-06-11).
> **통과 기준**: [U1 §6 빌드 가능 정의](../design-artifacts/units/unit-u1-discover.md)의 *서버측* 부분 — U0 mock 위에서 DISC-01~04 동작·테스트.

---

## 사전 확인 (완료)

- [x] **S0. 입력 정독** — U1 §2 스토리 4건(DISC-01~04) AC, §3 입력 포트·출력 `SearchResult`, §6 Buildable 4항목 추출.
- [x] **S1. U0 전제 확인** — 포트 8종 + mock/aws 어댑터 + `build_u0`/`U0Ports` 완료. `SearchFilters`·`PaperHit`·`LlmGateway`·`SessionPort` 재사용 가능.

---

## 사용자 클래리피케이션 (실행 전 확인 완료, 2026-06-11)

- [x] **C1. 라운드 구성** — **단계분할: 백엔드 먼저**. 이번 라운드 = `docsuri/u1` 도메인 로직 + FastAPI 엔드포인트 + pytest. Next.js/shadcn 프론트(ResultListView·검색폼·카드 데스크톱6/모바일3·바텀시트·필터칩·URL 직렬화 UI)는 **다음 라운드**.
- [x] **C2. 스토리 커버리지** — **4개 전부** (DISC-01·02·03·04). units_plan §2.1 정의와 일치.
- [x] **C3. 브랜치** — `feature/aidlc-construction-u1-discover` 그대로(이미 분기).
- [x] **C4. DTO 경계** — `SearchResult`는 §3.7 그대로 동결. DISC-04 한→영 매핑 1줄은 UI 표시 전용이라 **API 엔벨로프(`SearchResponse.query_mapping`)**에 싣고 계약을 건드리지 않음(U3/U4 합의 회피).
- [x] **C5. 난이도 휴리스틱(A7)** — `abstract_len`·`field_tags`(↑난이도) + `citations`(↓난이도) 결정적 가중. 초기 휴리스틱, 정밀도 평가는 U1 책임(§7).

---

## 실행 단계 (완료)

### Part A — 골격 + DTO
- [x] **A1. 빌드 플랜 아티팩트** — 본 문서.
- [x] **A2. `docsuri/u1/dtos.py`** — `SearchResult`(§3.7 1:1)·`SearchResultPaper`·`ExpandedTerm`·`QueryMapping`·`SearchResponse`·`DifficultyLabel`/`SortKey`.

### Part B — 도메인 컴포넌트 (component-model §3)
- [x] **B1. `difficulty.py`** — DifficultyEstimator(LLM 미사용, A7 휴리스틱).
- [x] **B2. `query_mapper.py`** — KoEnQueryMapper(한글 비율 detect + KO_EN_SEED·LLM 보강 map_explain).
- [x] **B3. `keyword_expander.py`** — KeywordExpander(EXPANSION_SEED·LLM 보강). mock canned LLM은 파싱 실패 → 시드 구동.
- [x] **B4. `filter_sort.py`** — FilterSortController(SessionPort 위임 URL 왕복 + sort) + `sort_papers`(DISC-02 정렬, DISC-04 한국어 입문 가중).
- [x] **B5. `orchestrator.py`** — SearchOrchestrator(캐시 24h → 매핑 → embed → search k=20 → 난이도 → 정렬 → 조립 → Telemetry).

### Part C — 조립 + HTTP
- [x] **C1. `service.py`** — `build_u1(u0) -> U1Services`(U0 `build_u0` 미러링).
- [x] **C2. `api.py`** — `POST /api/search`(SearchResponse) · `GET /healthz`.
- [x] **C3. `app.py`** — `create_app()`: settings → build_u0 → build_u1 → include_router.

### Part D — 검증
- [x] **D1. pytest** — `test_u1_discover.py`(DISC-01~04 + 캐시 적중 + 난이도) · `test_u1_api.py`(TestClient 엔벨로프). **전체 26/26 통과**(U0 14 + U1 12).
- [x] **D2. 시연** — `scripts/u1_demo.py` **4/4 통과**(mock, 자격 증명 불필요).
- [x] **D3. 사용자 최종 리뷰** — 코드 리뷰 피드백 반영 완료(임베딩 언어·BFF 에러 표면화·URL NaN 가드·델리미터 대소문자·healthz 분리·캐시 손상 가드·테스트 강화).

### Part E — 마무리
- [x] **E1. README** — U1 모듈·엔드포인트·실행법 추가.
- [x] **E2. 커밋/PR** — `develop` 위로 rebase 후 PR #24 생성(백엔드·프론트 포함).

---

## 범위 밖 (다음 라운드)

- ~~프론트엔드(Next.js App Router + shadcn/ui)~~ — ✅ **별도 프론트 라운드에서 완료**(`frontend/`):
  검색폼·결과카드(데스크톱6/모바일3 "더 보기")·정렬/필터(모바일 vaul Drawer)·확장칩·한→영 매핑·URL 직렬화.
  BFF(`/api/search`) 프록시↔mock 폴백. lint·tsc·build 통과 + 런타임 스모크(mock·실연결) 검증.
- 배포·IaC·Lambda 패키징, AWS 실호출 통합 테스트(환경 구축 라운드, ADR §14).
- `SearchResult` 계약 확장(한→영 매핑 DTO 편입 등 U3·U4 합의 사안).
- 난이도 추정 정밀도 평가·튜닝(A7) — 본 unit 책임이나 별도 사이클.

---

## 후속 과제 (이번 라운드에서 의식적으로 남긴 기술 부채)

코드 리뷰(2026-06-11)에서 식별. 지금은 닫지 않되 추적한다.

- **관측 op 세분화 + 실패 텔레메트리** (component-model §8.2 / 관측가능성) —
  현재 `op="search"`만 기록하고 `expand`·`ko_en_map`은 `LlmGateway`의 `op="llm.complete"`로만
  찍힌다. 또한 LLM 보강 실패(query_mapper·keyword_expander의 `_llm_*`)는 **조용히 삼켜져**
  오류율이 어디에도 안 남는다. → **관측 스택(EMF/X-Ray) 환경구축 라운드**에서 구간 record +
  실패 이벤트 기록으로 닫는다. (지금 로거 신설은 소비처 없는 오버엔지니어링.)
- **LLM 구조적 출력(structured output / tool use)으로 키워드 파싱 견고화** (LLM 호출 견고성·환각 방지) —
  현재 `query_mapper`/`keyword_expander`는 LLM 자유텍스트를 `_parse_terms` 휴리스틱으로 긁는다.
  Bedrock Converse `toolConfig`로 스키마 강제 출력을 받으면 파싱이 사라진다. 단, 이는 U0
  `LlmPort.complete(prompt, persona, budget_tokens) -> Completion(text)` **시그니처 확장**이 필요 →
  [handoff §6](../story-artifacts/handoff.md) 4단계로 **U0 소유자와 합의**해야 함(U1 단독 변경 금지, U1 §8).
  중간책: U0 변경 없이 "JSON만" 프롬프트 + `json.loads` + 폴백(정규식보다 견고하나 API 강제는 아님).
