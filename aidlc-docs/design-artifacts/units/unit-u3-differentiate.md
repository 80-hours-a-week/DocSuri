# Unit U3 — Differentiate (차별화·연구 공백)

> 참조: [`epics.md#e3`](../../requirements/epics.md#e3) · [`user_stories.md`](../../story-artifacts/user_stories.md) · [`unit-u0-foundation.md`](unit-u0-foundation.md)

---

## 1. 정체성

- **ID**: U3
- **이름**: Differentiate
- **미션 1줄**: 사용자의 *연구 주제 초안*과 기존 논문 간의 유사·차이·공백을 드러내, [P1](../../story-artifacts/personas.md#p1)은 졸업논문 novelty를, [P2](../../story-artifacts/personas.md#p2)는 학부 수준 가벼운 중복 검토를 얻게 한다.
- **범위**:
  - **In**: 주제 초안 입력, 유사 5편 차별성 노트, 연구 공백 후보 3개 제안, 학부 모드 가벼운 점검.
  - **Out**: 검색(→ [U1](unit-u1-discover.md)), 요약·번역(→ [U2](unit-u2-comprehend.md)), 인용 그래프(→ [U4](unit-u4-trace.md)).

---

## 2. 포함 스토리

본 unit은 [E3 Differentiate](../../requirements/epics.md#e3)의 3개 스토리를 모두 포함한다.

### [US-DIFF-01](../../story-artifacts/user_stories.md#us-diff-01) · 졸업논문 novelty 검증 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈
- **I want** 자기 연구 주제 초안을 입력하면 상위 유사 5편과의 차별성 노트를 받기
- **so that** 주제가 중복인지, 어디가 새로운지 판단한다.

```gherkin
Given 박지훈이 연구 주제 초안(200~500자)을 입력
When "차별성 분석"을 요청한다
Then 시스템은 임베딩 유사도 상위 5편 논문을 표시한다
And 각 논문에 대해 "공통점 1줄 / 차이점 1줄" 노트를 제공한다
And 최종 한 문단의 "전반적 novelty 평가"가 함께 출력된다
```
**Priority**: Must · **SP**: 8 · **Dependencies**: [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01), [US-COMP-01](../../story-artifacts/user_stories.md#us-comp-01) · **NFR**: [NFR-DATA-02](../../requirements/nfr.md#nfr-data-02), [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01)·[02](../../requirements/nfr.md#nfr-cost-02), [NFR-UX-02](../../requirements/nfr.md#nfr-ux-02)

### [US-DIFF-02](../../story-artifacts/user_stories.md#us-diff-02) · 연구 공백 후보 제안 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈
- **I want** 자기 주제 초안과 유사 논문을 바탕으로 "다루지 않은 연구 공백 3개" 제안을 받기
- **so that** 주제를 차별화할 후보를 빠르게 얻는다.

```gherkin
Given US-DIFF-01의 차별성 분석 결과가 존재
When 박지훈이 "연구 공백 제안"을 요청한다
Then 시스템은 후보 3개를 짧은 제목과 한 문단 설명으로 제공한다
And 각 후보에 대해 근거가 된 논문 ID를 명시한다
```
**Priority**: Should · **SP**: 8 · **Dependencies**: [US-DIFF-01](../../story-artifacts/user_stories.md#us-diff-01) · **NFR**: [NFR-DATA-02](../../requirements/nfr.md#nfr-data-02), [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01)

### [US-DIFF-03](../../story-artifacts/user_stories.md#us-diff-03) · 학부 수준 가벼운 중복 점검 — [P2](../../story-artifacts/personas.md#p2)

- **As a** 김민서
- **I want** 졸업프로젝트 주제 아이디어를 한국어 자연어로 입력하면 "학부 수준에서 흔한 시도인지 / 차별점 한 줄"을 받기
- **so that** 프로젝트 시작 전에 방향을 가볍게 점검한다.

```gherkin
Given 김민서가 자기 졸업프로젝트 아이디어를 한국어 3~5문장으로 입력
When "가벼운 점검"을 요청한다
Then 시스템은 "비슷한 학부 수준 시도가 있는지" 한 문단 평가를 제공한다
And 자신의 아이디어가 가져갈 수 있는 차별점 1줄 제안을 함께 표시한다
```
**Priority**: Could · **SP**: 5 · **Dependencies**: [US-DISC-04](../../story-artifacts/user_stories.md#us-disc-04), [US-COMP-03](../../story-artifacts/user_stories.md#us-comp-03) · **NFR**: [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01), [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01)

---

## 3. Cross-unit 의존 (인터페이스 계약)

### 입력 (← 다른 unit)

| 출처 | DTO/포트 | 사용 |
|---|---|---|
| [U1 Discover](unit-u1-discover.md) | `SearchResult` (mock 가능) | 유사 5편의 메타데이터 |
| [U2 Comprehend](unit-u2-comprehend.md) | `SummaryResult` (mock 가능) | 차별성 노트 생성용 핵심 요약 |
| [U0 Foundation](unit-u0-foundation.md) | `EmbeddingPort.embed`, `LlmPort.complete`, `Telemetry`, `Glossary` | 본 unit의 모든 임베딩·LLM 호출 |

### 출력 (U3 → UI/다음 단계)

| DTO | 사용 | 스키마(개념) |
|---|---|---|
| `NoveltyReport` | UI 렌더 | `{ user_topic, similar_papers: [{ paper, common, diff }], overall_novelty, gap_proposals: [{ title, body, evidence_ids }], persona_mode }` |

---

## 4. Cross-cutting NFRs

| NFR 키 | 본 unit의 책임 |
|---|---|
| [NFR-UX-02](../../requirements/nfr.md#nfr-ux-02) (전문 어휘 보존) | DIFF-01·02 출력 톤 |
| [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01) (학부 가독성) | DIFF-03 출력 톤 |
| [NFR-DATA-02](../../requirements/nfr.md#nfr-data-02) (출처 표시) | gap_proposals.evidence_ids → 원문 링크 |
| [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01)·[02](../../requirements/nfr.md#nfr-cost-02) | DIFF-01·02는 다중 LLM 호출, 청크 압축 강제 |
| [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01)·[03](../../requirements/nfr.md#nfr-lang-03) | 본문 한국어 + 학술 용어 사전 적용 |

---

## 5. 데이터·외부 의존 (본 unit이 닫는 결정)

- *차별성 노트* 프롬프트 설계 — 공통점/차이점 1줄, novelty 한 문단의 톤 일관성.
- *연구 공백 제안* 휴리스틱 — 유사 5편의 *방법·데이터셋·평가지표* 차이에서 공백 추출.
- DIFF-01의 SP 8 분해 가능성 ([R2](../../story-artifacts/handoff.md#r-2)) — 본 unit 진입 시 *임베딩 비교*와 *LLM 차별성 노트*를 두 sub-스토리로 쪼갤지 결정.

---

## 6. 빌드 가능 정의 (Definition of Buildable)

- [ ] [U1](unit-u1-discover.md) `SearchResult` mock JSON + [U2](unit-u2-comprehend.md) `SummaryResult` mock JSON으로 3개 스토리 AC 통과
- [ ] [US-DIFF-01](../../story-artifacts/user_stories.md#us-diff-01) 출력에 공통점·차이점 1줄, novelty 한 문단이 모두 존재
- [ ] [US-DIFF-02](../../story-artifacts/user_stories.md#us-diff-02) 공백 후보 3개 각각에 *evidence_ids*가 들어 있음
- [ ] [US-DIFF-03](../../story-artifacts/user_stories.md#us-diff-03) 한국어 톤이 [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01) 통과
- [ ] [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01) — DIFF-01·02 호출 평균 비용 시뮬레이션

---

## 7. 미해결 위험 (본 unit이 닫는 위험)

- [R1](../../story-artifacts/handoff.md#r-1) 일부 — DIFF-01·02 모바일 입력 폼 가정(*읽기 전용 결과 확인만*)의 실증 또는 폐기.
- [R2](../../story-artifacts/handoff.md#r-2) **SP 8 분해** — DIFF-01·02를 두 sub-스토리로 쪼개는 결정.
- [R3](../../story-artifacts/handoff.md#r-3) 일부 — DIFF-01·02가 *비용 폭증의 주범*이 될 수 있어 본 unit이 비용 가드 1차 책임.

---

## 8. 변경 정책

- **단독 변경**: 차별성 노트 프롬프트, 공백 후보 휴리스틱, 출력 카드 디자인.
- **cross-unit 영향**: U1 `SearchResult` / U2 `SummaryResult` 스키마 의존 — 의존하는 필드가 사라지면 합의 갱신.
- **금지**: 본 unit 내부에서 검색 인덱스를 *재구현*하는 것. 임베딩 검색은 U0가 단일 진입.
