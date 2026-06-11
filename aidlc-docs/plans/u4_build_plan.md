# U4 Trace 빌드 — 작업 계획 (Code Generation Phase)

> **Phase**: AIDLC Construction — Code Generation (U4 진입 라운드, U1~U3은 타 팀원 병렬 진행)
> **입력 산출물**: [`unit-u4-trace.md`](../design-artifacts/units/unit-u4-trace.md) (빌드 가능 정의 §6) · [`component-model.md §6`](../design-artifacts/component-model.md) (U4 컴포넌트 5종 + `CitationView` DTO — **동결**) · [`ADR §12`](../design-artifacts/architecture_decision_record.md) · [`u0-code-review.md`](../reviews/u0-code-review.md) (M2 — "U4 진입 전" 배치)
> **병렬 진입 근거**: [units-overview §3](../design-artifacts/units/units-overview.md) "완전 병렬" 옵션 — U4 의존은 U0 포트(빌드 완료) + `SearchResult.papers[i].id`(mock 가능)뿐. U2·U3 의존 0.
> **승인 게이트**: 사용자 승인 후 실행, 단계별 체크박스 갱신.

---

## 사전 확인 (완료)

- [x] **S0. 입력 정독** — U4 §2 스토리 2건(TRACE-01 Should·SP8 / TRACE-02 Could·SP3), §3 계약(입력: `CitationApi.oneHop`·`CachePort`·`Telemetry`·중심 논문 ID / 출력: `CitationView`), §5 캐시 키 설계(`paper_id + api_ver + window`), §6 빌드 가능 정의 4항목, §8 금지(다단계 인용 트리).
- [x] **S1. U0 자산 확인** — `FixtureCitation`(mock)·`SemanticScholarCitation`(실제+캐시+폴백) 어댑터 존재. `corpus_seed.json` 100편이 실제 arXiv ID라 중심 논문 fixture로 사용 가능.

---

## 사용자 클래리피케이션 (실행 전 확인 필요)

> ✅ 3건 모두 사용자 확인 완료 (2026-06-11).

- [x] **C1. 분기 기점·PR 전략** — **#14 머지 후 develop에서 분기** 확정. 확인 결과 PR #14·#20 모두 이미 MERGED → `feature/aidlc-construction-u4-trace`를 `origin/develop`에서 분기 (stacked 불필요해짐). PR도 develop 대상.
- [x] **C2. 이번 라운드 범위** — **백엔드 전용** 확정. 그래프/리스트 UI(React Flow)는 U1 스캐폴드 머지 후 **U4-UI 후속 라운드**. U4 §6의 UI 항목은 후속에 위임, 이번엔 데이터·분기 로직 수준까지.
- [x] **C3. R2 분해 결정** — **TRACE-01을 2개 sub-스토리로 분할 기록** 확정: **TRACE-01a** "1-hop 데이터 확보·캐시·폴백" (이번 라운드) / **TRACE-01b** "그래프·리스트 렌더" (U4-UI 후속). 동결 스토리 원문 불변 — 본 기록이 R2(SP 8 분해)의 U4 몫 결정이다. TRACE-02는 분할 불요(SP 3).

> 기본 포함(질문 생략): **M2 패치** — 코드 리뷰가 "U4 진입 전"으로 배치한 Semantic Scholar 429 보강(429 재시도 + User-Agent + API 키 환경 변수) + Low 소정리(L1 데드 코드, L3 타입, L4 주석). U0 파일 패치이며 U4가 첫 소비자라 본 라운드 선두에 둔다.

---

## 실행 단계 (승인 후 진행)

### Part A — U0 선행 패치 (리뷰 후속)

- [x] **A1. M2 패치** — `http_policy.py` 429 재시도 추가 · SemanticScholarCitation에 User-Agent + `DOCSURI_SS_API_KEY`(있으면 `x-api-key`) 배선. 폴백 유지.
- [x] **A2. Low 소정리** — L1 데드 코드 삭제 · L3 `default_persona: Persona` 타입화(type: ignore 0건) · L4 스레드 비안전 주석.

### Part B — U4 컴포넌트 (component-model §6 그대로)

- [x] **B1. `CitationView` DTO** — `docsuri/u4/views.py` (§6.6 시그니처 그대로, MAX_NODES=30).
- [x] **B2. CitationFetcher** — 캐시 키 `cite:{id}:v1:{일 단위 window}`(U4 §5)·24h TTL·시계 주입·`op=citation_fetch` Telemetry.
- [x] **B3. FormFactorRouter** — `<768px` 또는 `undergrad` → list (NFR-MOBILE-05 + TRACE-02). 경계값 768=graph.
- [x] **B4. TopInfluenceSelector** — 피인용 내림차순 Top-3.
- [x] **B5. 뷰 조립기** — 그래프 모드 center 포함 ≤30 인용수 가중 절단, 리스트 모드 무절단(검색창 필터 몫). 중심 메타는 호출자 전달(unit 경계).

### Part C — 검증 (U4 §6 백엔드 범위와 1:1)

- [x] **C1-T. pytest** — U4 신규 6건 포함 **전체 20/20 통과** (TRACE-01a 구조·캐시 적중→만료·폴백 / 렌더 분기 / TRACE-02 Top-3 / ≤30 절단 / Telemetry 키).
- [x] **C2-T. 시연 스크립트** — `scripts/u4_demo.py` 실행: ①~③ 통과, ④ UI 항목은 후속 라운드 표기.
- [x] **C3-T. 계획·문서 갱신** — U4 §6 체크박스는 UI 잔여로 미갱신(전체 통과 시 일괄). 커밋·PR(develop 대상 — C1 결정대로 stacked 아님).
- [ ] **C4-T. 사용자 최종 리뷰** — 결과 제출 완료, **피드백 대기**.

---

## 범위 밖 (Out of Scope)

- React Flow 그래프·모바일 리스트 UI, 노드 검색창, 바텀시트 — **U4-UI 후속 라운드** (U1 스캐폴드 머지 후).
- 다단계 인용 트리 (U4 §8 금지 — 후속 사이클).
- Semantic Scholar 실호출 통합 테스트 — 환경 구축 라운드 (mock fixture로 검증).
- U4 §6 체크박스 갱신 — UI 포함 전체 통과 시점에.
