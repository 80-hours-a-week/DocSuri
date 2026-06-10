# Units Overview — DocSuri MVP 단위 분해

> 산출 근거: [`../../plans/units_plan.md`](../../plans/units_plan.md) · Prompt 17·18

본 페이지는 5개 unit이 어떻게 *독립 빌드 가능*하고 *느슨하게 결합*되어 있는지를 한눈에 보여 준다.

---

## 1. Unit 매트릭스

| Unit | 이름 | Epic | 포함 스토리 | 페르소나 | SP 합 |
|---|---|---|---|---|---|
| [U0](unit-u0-foundation.md) | Foundation (공통 인프라) | — | (없음 — 인프라 unit) | [P1](../../story-artifacts/personas.md#p1)·[P2](../../story-artifacts/personas.md#p2) | — |
| [U1](unit-u1-discover.md) | Discover | [E1](../../requirements/epics.md#e1) | [DISC-01](../../story-artifacts/user_stories.md#us-disc-01)·[02](../../story-artifacts/user_stories.md#us-disc-02)·[03](../../story-artifacts/user_stories.md#us-disc-03)·[04](../../story-artifacts/user_stories.md#us-disc-04) | [P1](../../story-artifacts/personas.md#p1)·[P2](../../story-artifacts/personas.md#p2) | 18 |
| [U2](unit-u2-comprehend.md) | Comprehend | [E2](../../requirements/epics.md#e2) | [COMP-01](../../story-artifacts/user_stories.md#us-comp-01)·[02](../../story-artifacts/user_stories.md#us-comp-02)·[03](../../story-artifacts/user_stories.md#us-comp-03)·[04](../../story-artifacts/user_stories.md#us-comp-04)·[05](../../story-artifacts/user_stories.md#us-comp-05) | [P1](../../story-artifacts/personas.md#p1)·[P2](../../story-artifacts/personas.md#p2) | 20 |
| [U3](unit-u3-differentiate.md) | Differentiate | [E3](../../requirements/epics.md#e3) | [DIFF-01](../../story-artifacts/user_stories.md#us-diff-01)·[02](../../story-artifacts/user_stories.md#us-diff-02)·[03](../../story-artifacts/user_stories.md#us-diff-03) | [P1](../../story-artifacts/personas.md#p1)·[P2](../../story-artifacts/personas.md#p2) | 21 |
| [U4](unit-u4-trace.md) | Trace | [E4](../../requirements/epics.md#e4) | [TRACE-01](../../story-artifacts/user_stories.md#us-trace-01)·[02](../../story-artifacts/user_stories.md#us-trace-02) | [P1](../../story-artifacts/personas.md#p1)·[P2](../../story-artifacts/personas.md#p2) | 11 |

**합계**: 14 스토리 (원본과 정확히 일치) / 70 SP.

> **정합 검증**: [`coverage_matrix.md`](../../story-artifacts/coverage_matrix.md) §1의 스토리 14개가 U1~U4에 *누락·중복 0*으로 매핑되었다.

---

## 2. Cross-unit 의존 다이어그램

```
              ┌──────────────────────────────┐
              │   U0 Foundation              │
              │                              │
              │  EmbeddingPort  LlmPort      │
              │  CachePort      Glossary     │
              │  SessionPort    Telemetry    │
              │  CitationApi                 │
              └────┬────┬────┬────┬──────────┘
                   │    │    │    │
       (모든 포트 사용)│    │    │    │
                   ▼    ▼    ▼    ▼
              ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
              │ U1  │ │ U2  │ │ U3  │ │ U4  │
              │Disc │ │Comp │ │Diff │ │Trace│
              └──┬──┘ └──┬──┘ └─▲─▲─┘ └─▲───┘
                 │       │      │ │     │
                 └───────┴─SR───┘ │     │  SR = SearchResult
                                  │     │  SM = SummaryResult
                         SM ──────┘     │
                                        │
                 └─SR (paper_id) ───────┘

  화살표 ▼·▶: 의존 방향 (호출자 → 피호출자)
  실선     : Foundation 포트 의존 (모든 unit이 U0를 향함)
  굵은 화살표: Domain unit 간 DTO 의존 (U1→U3, U2→U3, U1→U4)
```

**검증 — Acyclic ✅**: U0를 단방향 의존하고, 도메인 unit 간에는 *U1→U3*, *U2→U3*, *U1→U4* 한 방향뿐. 순환 의존 0건.

---

## 3. 추천 빌드 순서

| 순서 | Unit | 사유 | 다른 unit 차단 여부 |
|---|---|---|---|
| 1 | [U0](unit-u0-foundation.md) | 모든 domain unit이 의존. 포트 시그니처가 안정화되어야 mock도 안정. | **차단** — U0 시그니처 변경은 곧 전체 영향. |
| 2 | [U1](unit-u1-discover.md), [U2](unit-u2-comprehend.md) | 두 unit은 서로 의존하지 않는다 (mock 가능). 별도 팀이 *병렬* 진행. | U3·U4 차단(U1·U2 DTO 의존) |
| 3 | [U3](unit-u3-differentiate.md), [U4](unit-u4-trace.md) | U1·U2의 DTO가 완성 또는 mock이 안정화된 뒤 진입. 두 unit은 서로 독립이라 *병렬*. | — |

> *완전 병렬*도 가능 — 각 팀이 cross-unit DTO를 mock fixture로 시작하면 U3·U4도 1단계부터 시작 가능. 다만 *통합 시점*에 DTO 합의가 정합인지 검증해야 함.

---

## 4. 인터페이스 합의 (단일 진실 표)

이 표가 unit 간 *유일한 합의 지점*. 변경 시 모든 의존 unit과 동기.

| 인터페이스 | 정의 unit | 사용 unit | 한 줄 요약 |
|---|---|---|---|
| `EmbeddingPort.embed/search` | [U0](unit-u0-foundation.md) | U1·U3 | 텍스트 → 벡터 + 인덱스 검색 |
| `LlmPort.complete` | [U0](unit-u0-foundation.md) | U2·U3 | 페르소나·예산 토큰 명시 LLM 호출 |
| `CachePort` | [U0](unit-u0-foundation.md) | U1·U2·U4 | get/set + TTL |
| `SessionPort` | [U0](unit-u0-foundation.md) | U1~U4 | 익명 세션 + 필터 URL 직렬화 |
| `Telemetry.record` | [U0](unit-u0-foundation.md) | U1~U4 | 모든 외부 호출 자동 기록 |
| `Glossary.lookup` | [U0](unit-u0-foundation.md) | U2·U3 | 학술 용어 정규 번역 |
| `CitationApi.oneHop` | [U0](unit-u0-foundation.md) | U4 | 외부 Semantic Scholar 래퍼 |
| `SearchResult` (DTO) | [U1](unit-u1-discover.md) | U3·U4 | 검색 결과 + 메타데이터 + 확장 키워드 |
| `SummaryResult` (DTO) | [U2](unit-u2-comprehend.md) | U3 | 모드별 요약 + vocab 풀이 + 비용 |

---

## 5. 미해결 위험 · 결정의 unit 책임 매핑

[`handoff.md`](../../story-artifacts/handoff.md)에 등재된 위험·결정 중 **본 unit 분해가 닫는 책임**의 위치.

### 5.1 위험 ([handoff.md §2](../../story-artifacts/handoff.md))

| 위험 | 닫는 unit |
|---|---|
| [R1](../../story-artifacts/handoff.md#r-1) Mobile UX 미확정 5건 | [U1](unit-u1-discover.md) (DISC-02·03), [U2](unit-u2-comprehend.md) (COMP-01), [U3](unit-u3-differentiate.md) (DIFF-01·02) |
| [R2](../../story-artifacts/handoff.md#r-2) SP 8 분해 3건 | [U3](unit-u3-differentiate.md) (DIFF-01·02), [U4](unit-u4-trace.md) (TRACE-01) |
| [R3](../../story-artifacts/handoff.md#r-3) LLM 비용 변동성 | [U0](unit-u0-foundation.md) (게이트웨이 상한) + [U2](unit-u2-comprehend.md)·[U3](unit-u3-differentiate.md) (호출 측 압축) |
| [R4](../../story-artifacts/handoff.md#r-4) 인용 그래프 API 의존 | [U0](unit-u0-foundation.md) (캐시·폴백), [U4](unit-u4-trace.md) (사용·실증) |
| [R5](../../story-artifacts/handoff.md#r-5) 학술 용어 사전 | [U0](unit-u0-foundation.md) (`Glossary`), [U2](unit-u2-comprehend.md) (적중률 보고) |
| [R6](../../story-artifacts/handoff.md#r-6) 오프라인 24h 캐시 | [U0](unit-u0-foundation.md) (`CachePort` 클라이언트 구현) |
| [R7](../../story-artifacts/handoff.md#r-7) Won't 항목 재요청 | (제품 관리 — unit 분해 밖) |

### 5.2 결정 ([handoff.md §4](../../story-artifacts/handoff.md))

| 결정 | 닫는 unit |
|---|---|
| [D1](../../story-artifacts/handoff.md#d-1) 백엔드 언어 | [U0](unit-u0-foundation.md) |
| [D2](../../story-artifacts/handoff.md#d-2) 임베딩 인덱스 | [U0](unit-u0-foundation.md) |
| [D3](../../story-artifacts/handoff.md#d-3) 임베딩 모델 | [U0](unit-u0-foundation.md) |
| [D4](../../story-artifacts/handoff.md#d-4) LLM 모델 | [U0](unit-u0-foundation.md) |
| [D5](../../story-artifacts/handoff.md#d-5) 프론트엔드 프레임워크 | [U1](unit-u1-discover.md) (UI 최초 진입) |
| [D6](../../story-artifacts/handoff.md#d-6) 컴포넌트 라이브러리 | [U1](unit-u1-discover.md) |
| [D7](../../story-artifacts/handoff.md#d-7) 그래프 라이브러리 | [U4](unit-u4-trace.md) |
| [D8](../../story-artifacts/handoff.md#d-8) 오프라인 캐시 메커니즘 | [U0](unit-u0-foundation.md) |
| [D9](../../story-artifacts/handoff.md#d-9) 호스팅 환경 | [U0](unit-u0-foundation.md) |
| [D10](../../story-artifacts/handoff.md#d-10) 관찰가능성 스택 | [U0](unit-u0-foundation.md) |

> **D1~D4·D8·D9·D10**(7개)은 [U0](unit-u0-foundation.md)에 집중되어 있다 — 이 unit의 진입 직후 결정 라운드를 한꺼번에 닫는 것이 합리적.

---

## 6. 정합 검증 (units_plan §6)

- **6.1 독립 빌드 가능성**: 각 unit md §6 "빌드 가능 정의"에 mock 입력만으로 AC 통과 가능 여부 명시 ✅
- **6.2 Acyclic 의존**: §2 다이어그램 참조. 순환 0건 ✅
- **6.3 스토리 매핑 정합**: §1 합계 14 = 원본 14 ✅

---

## 7. 변경 정책 요약

- 각 unit md §8의 "변경 정책"이 단일 진실. 본 overview는 *현재 상태의 스냅샷*.
- unit 추가/삭제·인터페이스 시그니처 변경은 [`handoff.md §6`](../../story-artifacts/handoff.md) 4단계(prompt → plan → 승인 → 동기 갱신)를 따른다.
