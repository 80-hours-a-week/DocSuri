# Unit U4 — Trace (인용 흐름)

> 참조: [`epics.md#e4`](../../requirements/epics.md#e4) · [`user_stories.md`](../../story-artifacts/user_stories.md) · [`unit-u0-foundation.md`](unit-u0-foundation.md)

---

## 1. 정체성

- **ID**: U4
- **이름**: Trace
- **미션 1줄**: 선택된 논문을 중심으로 *직접 인용*(outgoing)과 *피인용*(incoming) 1-hop을 디바이스 폼팩터에 맞게 보여 — 데스크톱은 그래프, 모바일·학부 모드는 간소화 리스트.
- **범위**:
  - **In**: 1-hop 인용 그래프 (≤30 노드, 데스크톱), 영향력 Top-3 리스트 (모바일·학부 모드).
  - **Out**: 다단계 인용 트리·시간 축 애니메이션·분야 군집 컬러링 (후속 사이클).

---

## 2. 포함 스토리

본 unit은 [E4 Trace](../../requirements/epics.md#e4) (MVP는 1-hop만)의 2개 스토리를 모두 포함한다.

### [US-TRACE-01](../../story-artifacts/user_stories.md#us-trace-01) · 1-hop 인용 그래프 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈
- **I want** 선택한 논문을 중심으로 직접 인용과 피인용을 1-hop 그래프로 보기
- **so that** 핵심 선행 연구와 영향력 후속 연구를 한눈에 파악한다.

```gherkin
Given 박지훈이 결과 목록에서 한 논문을 선택
When "인용 흐름 보기"를 요청한다
Then 시스템은 중심 노드 + 직접 인용 노드 + 피인용 노드를 5초 안에 표시한다
And 각 노드를 탭 또는 클릭하면 해당 논문 카드가 사이드 패널에 열린다
And 그래프는 최대 30개 노드로 제한되어 가독성을 확보한다

# 모바일 분기 (NFR-MOBILE-05 정합)
Given 박지훈이 모바일 디바이스(<768px)에서 동일 요청을 수행한다
When "인용 흐름 보기"를 요청한다
Then 시스템은 그래프 대신 "중심 / 인용(outgoing) / 피인용(incoming)" 3개 섹션의 간소화 리스트를 7초 안에 표시한다
And 리스트 상단에는 노드 검색창이 노출되어 제목·저자로 즉시 필터할 수 있다
And 각 항목 우측에는 1탭 거리에 "논문 카드 열기" 버튼이 있고 터치 타깃은 44 CSS px 이상이다
```
**Priority**: Should · **SP**: 8 · **Dependencies**: [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01) · **NFR**: [NFR-PERF-03](../../requirements/nfr.md#nfr-perf-03), [NFR-DATA-01](../../requirements/nfr.md#nfr-data-01)·[02](../../requirements/nfr.md#nfr-data-02), [NFR-MOBILE-03](../../requirements/nfr.md#nfr-mobile-03)·[05](../../requirements/nfr.md#nfr-mobile-05), [NFR-A11Y-03](../../requirements/nfr.md#nfr-a11y-03)

### [US-TRACE-02](../../story-artifacts/user_stories.md#us-trace-02) · 학부 모드 영향력 Top-3 — [P2](../../story-artifacts/personas.md#p2)

- **As a** 김민서
- **I want** 한 논문에 대해 "이 논문이 영향을 준 후속 논문 Top 3"을 그래프 대신 카드 리스트로 받기
- **so that** 학습 경로를 직선적으로 따라간다.

```gherkin
Given 김민서가 학부 모드에서 한 논문을 선택
When "후속 영향 보기"를 요청한다
Then 시스템은 피인용 수 가중치로 정렬된 후속 논문 3개 카드를 보여 준다
And 그래프 시각화는 표시하지 않는다 (인지 부담 최소화)
```
**Priority**: Could · **SP**: 3 · **Dependencies**: [US-TRACE-01](../../story-artifacts/user_stories.md#us-trace-01) · **NFR**: [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01), [NFR-PERF-03](../../requirements/nfr.md#nfr-perf-03)

---

## 3. Cross-unit 의존 (인터페이스 계약)

### 입력 (← 다른 unit)

| 출처 | DTO/포트 | 사용 |
|---|---|---|
| [U1 Discover](unit-u1-discover.md) | `SearchResult.papers[i].id` | 사용자가 선택한 중심 논문 ID |
| [U0 Foundation](unit-u0-foundation.md) | `CitationApi.oneHop(paper_id)` | 외부 Semantic Scholar API 래퍼 — *캐시·폴백 포함* |
| [U0 Foundation](unit-u0-foundation.md) | `CachePort.get/set` | 1-hop 결과 24h 재사용 |
| [U0 Foundation](unit-u0-foundation.md) | `Telemetry.record(...)` | API 호출·지연·실패 기록 |

### 출력 (U4 → UI)

| DTO | 사용 | 스키마(개념) |
|---|---|---|
| `CitationView` | 데스크톱 그래프 / 모바일·학부 리스트 | `{ center, outgoing: [PaperHit], incoming: [PaperHit], render: 'graph'\|'list', max_nodes: 30 }` |

---

## 4. Cross-cutting NFRs

| NFR 키 | 본 unit의 책임 |
|---|---|
| [NFR-PERF-03](../../requirements/nfr.md#nfr-perf-03) (데스크톱 P95<5s) | 그래프 렌더 완료까지 |
| [NFR-MOBILE-03](../../requirements/nfr.md#nfr-mobile-03) (4G P95<7s) | 모바일 리스트 표시까지 |
| [NFR-MOBILE-05](../../requirements/nfr.md#nfr-mobile-05) (<768px 그래프 대신 리스트) | 폼팩터 분기 강제 |
| [NFR-DATA-01](../../requirements/nfr.md#nfr-data-01)·[02](../../requirements/nfr.md#nfr-data-02) | Semantic Scholar 출처 노출 |
| [NFR-A11Y-03](../../requirements/nfr.md#nfr-a11y-03) | 노드/카드 터치 타깃 44px |
| [NFR-A11Y-02](../../requirements/nfr.md#nfr-a11y-02) | 그래프 노드 키보드 내비 (포커스 링) |

---

## 5. 데이터·외부 의존 (본 unit이 닫는 결정)

- [D7](../../story-artifacts/handoff.md#d-7) **그래프 시각화 라이브러리** — react-flow / Sigma.js / Cytoscape 중 선택. 모바일 분기는 그래프 불필요이므로 *데스크톱 전용 라이브러리 도입 가능*.
- 1-hop 캐시 키 설계 — paper_id + API 버전 + 시간 윈도우.

---

## 6. 빌드 가능 정의 (Definition of Buildable)

- [ ] [U0](unit-u0-foundation.md) `CitationApi.oneHop`을 JSON fixture로 mock해도 두 스토리 AC 통과
- [ ] 동일 paper_id에서 데스크톱은 그래프, 모바일은 리스트 두 렌더가 분기
- [ ] 노드 클릭/탭 → 논문 카드 사이드 패널/바텀시트 열림
- [ ] [NFR-PERF-03](../../requirements/nfr.md#nfr-perf-03)·[NFR-MOBILE-03](../../requirements/nfr.md#nfr-mobile-03) 목표가 fixture 기반 측정에서 만족

---

## 7. 미해결 위험 (본 unit이 닫는 위험)

- [R4](../../story-artifacts/handoff.md#r-4) **인용 그래프 API 의존** — 본 unit이 캐시 적중률·폴백 전략 실증.
- [R2](../../story-artifacts/handoff.md#r-2) 일부 — TRACE-01 SP 8 분해 가능성 (그래프 렌더 vs 데이터 fetch를 두 sub-스토리로).

---

## 8. 변경 정책

- **단독 변경**: 그래프 레이아웃 알고리즘, 모바일 리스트 정렬 가중치, 노드 카드 디자인.
- **cross-unit 영향**: `CitationApi` 시그니처(예: hop 깊이 옵션 추가) → U0 포트 변경 필요.
- **금지**: 다단계 인용 트리 구현 (MVP 비범위, 후속 사이클).
