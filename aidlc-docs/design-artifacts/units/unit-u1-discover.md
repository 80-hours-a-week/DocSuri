# Unit U1 — Discover (검색·발견)

> 참조: [`epics.md#e1`](../../requirements/epics.md#e1) · [`user_stories.md`](../../story-artifacts/user_stories.md) · [`unit-u0-foundation.md`](unit-u0-foundation.md)

---

## 1. 정체성

- **ID**: U1
- **이름**: Discover
- **미션 1줄**: 사용자의 자연어 의도(영문·한국어)를 의미 유사도 기반으로 논문 코퍼스에 매핑하고, **데스크톱·모바일 두 폼팩터**에서 결과를 적절히 보여 준다.
- **범위**:
  - **In**: 검색 쿼리 입력, 의미 검색, 키워드 자동 확장, 결과 정렬·필터, 난이도 추정 표시, 결과 카드 렌더(데스크톱 6 메타 / 모바일 3 메타).
  - **Out**: 요약·번역(→ [U2](unit-u2-comprehend.md)), 차별성 분석(→ [U3](unit-u3-differentiate.md)), 인용 그래프(→ [U4](unit-u4-trace.md)).

---

## 2. 포함 스토리

본 unit은 [E1 Discover](../../requirements/epics.md#e1)의 4개 스토리를 모두 포함한다.

### [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01) · 자연어 의미 검색 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈 (박사과정 연구자)
- **I want** 자신의 연구 의도를 자연어 문장(영문 가능)으로 입력해 의미 유사도 기반 상위 논문을 받기
- **so that** 키워드 노가다 없이 본인 주제와 가까운 선행 연구를 빠르게 발견한다.

**Acceptance Criteria**
```gherkin
# 데스크톱(≥768px)
Given 박지훈이 검색창에 "transformer-based retrieval-augmented summarization"을 입력
When 검색을 실행한다
Then 시스템은 의미 유사도 기준 상위 20건의 논문 카드를 3초 안에 반환한다
And 각 카드에는 제목, 저자, 연도, 인용수, 유사도, 난이도 6개 메타가 한 뷰에 표시된다
And 결과는 유사도/인용수/최신순으로 재정렬할 수 있다

# 모바일(<768px, 4G)
Given 박지훈이 모바일 디바이스에서 동일 검색을 실행한다
Then 시스템은 상위 20건의 논문 카드를 5초 안에 반환한다
And 각 카드 1뷰에는 제목·연도·유사도 3개 우선 메타만 표시되고, "더 보기" 펼침으로 저자·인용수·난이도가 노출된다
And 정렬·필터 컨트롤은 화면 상단의 단일 액션 바에서 1탭으로 도달 가능하다
```
**Priority**: Must · **SP**: 5 · **Dependencies**: — · **NFR**: [NFR-PERF-01](../../requirements/nfr.md#nfr-perf-01), [NFR-DATA-01](../../requirements/nfr.md#nfr-data-01)·[02](../../requirements/nfr.md#nfr-data-02), [NFR-UX-03](../../requirements/nfr.md#nfr-ux-03), [NFR-MOBILE-01](../../requirements/nfr.md#nfr-mobile-01)·[03](../../requirements/nfr.md#nfr-mobile-03)·[04](../../requirements/nfr.md#nfr-mobile-04)

### [US-DISC-02](../../story-artifacts/user_stories.md#us-disc-02) · 결과 정렬·필터 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈
- **I want** 검색 결과를 발표 연도·분야 태그로 필터하고 유사도/인용수/최신순으로 정렬하기
- **so that** 분야 트렌드를 빠르게 좁혀 본다.

**Acceptance Criteria**
```gherkin
Given 검색 결과 화면에 20건의 카드가 표시되어 있다
When "2023~2026" 연도 필터와 "NLP" 분야 태그를 선택하고 정렬을 "인용수 내림차순"으로 변경한다
Then 결과 목록은 두 필터를 모두 만족하는 카드로만 갱신되고 인용수 내림차순으로 재정렬된다
And 필터 상태는 URL 쿼리에 직렬화되어 새로고침에도 유지된다
```
**Priority**: Must · **SP**: 3 · **Dependencies**: [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01) · **NFR**: [NFR-UX-03](../../requirements/nfr.md#nfr-ux-03)

### [US-DISC-03](../../story-artifacts/user_stories.md#us-disc-03) · 키워드 자동 확장 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈
- **I want** 입력한 자연어를 시스템이 동의어·관련 용어로 자동 확장한 뒤 검색하기
- **so that** 표현 차이로 인한 누락을 줄인다.

**Acceptance Criteria**
```gherkin
Given 박지훈이 "RAG"를 검색어로 입력
When 검색을 실행한다
Then 시스템은 확장 키워드("retrieval-augmented generation", "retrieval augmented") 목록을 결과 상단에 표시한다
And 사용자는 각 확장 키워드를 체크/해제하여 즉시 재검색할 수 있다
```
**Priority**: Should · **SP**: 5 · **Dependencies**: [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01) · **NFR**: [NFR-PERF-01](../../requirements/nfr.md#nfr-perf-01)

### [US-DISC-04](../../story-artifacts/user_stories.md#us-disc-04) · 학부생 자연어 한국어 검색 — [P2](../../story-artifacts/personas.md#p2)

- **As a** 김민서 (AI 입문 학부생)
- **I want** 한국어 자연어 질문(예: "트랜스포머가 뭔가요?")으로 학부 수준 입문 논문 찾기
- **so that** 어디서 시작할지 모를 때도 진입 지점을 얻는다.

**Acceptance Criteria**
```gherkin
Given 김민서가 한국어로 "트랜스포머가 뭔가요"라고 입력
When 검색을 실행한다
Then 시스템은 난이도 추정 점수가 낮은 입문 적합 논문을 상위에 노출한다
And 결과 카드에는 난이도 라벨(입문/중급/고급)이 명시된다
And 입력 한국어가 영문 키워드로 어떻게 매핑되었는지 1줄로 표시한다
```
**Priority**: Should · **SP**: 5 · **Dependencies**: [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01) · **NFR**: [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01)·[02](../../requirements/nfr.md#nfr-lang-02)·[03](../../requirements/nfr.md#nfr-lang-03), [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01)

---

## 3. Cross-unit 의존 (인터페이스 계약)

### 입력 (← [U0 Foundation](unit-u0-foundation.md))

| 사용 포트 | 호출 형태 |
|---|---|
| `EmbeddingPort.embed(query, lang)` | 자연어 쿼리 임베딩 |
| `EmbeddingPort.search(vec, k=20, filters)` | 결과 검색 |
| `LlmPort.complete(...)` | 키워드 확장(DISC-03) · 한→영 매핑 설명(DISC-04) |
| `CachePort.get/set` | 동일 쿼리 24h 재사용 ([NFR-DATA-03](../../requirements/nfr.md#nfr-data-03)) |
| `SessionPort.session()` | 필터 URL 직렬화 |
| `Telemetry.record(...)` | 검색·확장 호출 로그 |

### 출력 (U1 → 다른 unit) — *유일한 약속*

| DTO | 사용 unit | 스키마(개념) |
|---|---|---|
| `SearchResult` | [U3 Differentiate](unit-u3-differentiate.md), [U4 Trace](unit-u4-trace.md) | `{ query, expanded_terms, papers: [{ id, title, authors, year, citations, similarity, difficulty }], filters, lang }` |

- mock 가능 — 의존 unit은 `SearchResult` 시드 JSON으로 *독립 빌드* 가능.

---

## 4. Cross-cutting NFRs

| NFR 키 | 본 unit의 책임 |
|---|---|
| [NFR-PERF-01](../../requirements/nfr.md#nfr-perf-01) (검색 P50<3s, P95<6s) | 검색 흐름의 *체감 시간*. U0의 raw 응답에 직렬화·렌더 시간 포함. |
| [NFR-MOBILE-03](../../requirements/nfr.md#nfr-mobile-03) (4G P95<5s) | 모바일 분기에서 결과 카드 1뷰 표시까지 |
| [NFR-UX-03](../../requirements/nfr.md#nfr-ux-03) (결과 카드 정보 밀도) | 데스크톱 6 메타 / 모바일 3 메타 + 펼침 |
| [NFR-MOBILE-01](../../requirements/nfr.md#nfr-mobile-01) (브레이크포인트 360/768/1280) | 카드·필터 컴포넌트가 3 폭에서 가로 스크롤 없이 동작 |
| [NFR-MOBILE-04](../../requirements/nfr.md#nfr-mobile-04) (최대 2탭 도달) | 정렬·필터 컨트롤은 모바일에서 1~2탭 이내 |
| [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01)·[02](../../requirements/nfr.md#nfr-lang-02) (출력 한국어, 영문 입력 허용) | 입력 폼·결과 카드의 표시 언어 |
| [NFR-A11Y-01](../../requirements/nfr.md#nfr-a11y-01) (WCAG 2.1 AA) | 검색 폼·결과 카드의 ARIA 라벨·콘트라스트 |

---

## 5. 데이터·외부 의존 (본 unit이 닫는 결정)

- [D5](../../story-artifacts/handoff.md#d-5) **프론트엔드 프레임워크** — 결과 카드·필터 컨트롤 컴포넌트 구현이 본 unit에서 시작.
- [D6](../../story-artifacts/handoff.md#d-6) **컴포넌트 라이브러리·디자인 시스템** — 카드·바텀시트·필터 칩 패턴.
- *난이도 추정 점수* 알고리즘 ([A7](../../story-artifacts/handoff.md#a-7) 가정 — 분야 태그 + 인용수 + 길이 + 어휘 빈도 휴리스틱).

---

## 6. 빌드 가능 정의 (Definition of Buildable)

- [ ] [U0](unit-u0-foundation.md) 포트를 mock으로 대체했을 때도 검색 폼 + 결과 카드 데스크톱·모바일 렌더가 동작
- [ ] [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01) AC 데스크톱·모바일 두 컨텍스트가 통과
- [ ] [US-DISC-02](../../story-artifacts/user_stories.md#us-disc-02) URL 쿼리 직렬화 검증 (새로고침 시 필터 유지)
- [ ] [US-DISC-04](../../story-artifacts/user_stories.md#us-disc-04) 한국어 입력 → 한→영 매핑 표시 확인

---

## 7. 미해결 위험 (본 unit이 닫는 위험)

- [R1](../../story-artifacts/handoff.md#r-1) 일부 — DISC-02·03 모바일 UX(슬라이드업 필터, 확장 키워드 칩)의 와이어프레임 보강.
- 난이도 추정 모델 정밀도 ([A7](../../story-artifacts/handoff.md#a-7))는 본 unit의 평가 책임.

---

## 8. 변경 정책

- **단독 변경**: 검색 UI 레이아웃, 정렬·필터 옵션, 카드 메타 펼침 패턴.
- **cross-unit 영향**: `SearchResult` 스키마 변경 (U3·U4 입력) → 합의 갱신 필요.
- **금지**: U0 포트 시그니처 직접 변경. (포트 *기능 요구*가 생기면 U0 변경 정책 따른다.)
