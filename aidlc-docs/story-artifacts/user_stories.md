# DocSuri MVP — 사용자 스토리 (마스터)

- **결정 근거**: [`aidlc-docs/plans/user_stories_plan.md`](../plans/user_stories_plan.md) 부록 A
- **포맷**: Connextra + Gherkin AC + MoSCoW + 피보나치 SP
- **ID 규칙**: `US-<EPIC>-<NN>` (EPIC = DISC | COMP | DIFF | TRACE)
- **출처**: [`aidlc-docs/prompts.md`](../prompts.md) § [Prompt 2](../prompts.md#prompt-2)
- **참조 페르소나**: [`personas.md`](personas.md) ([P1](personas.md#p1) 박지훈 / [P2](personas.md#p2) 김민서)
- **NFR 키 참조**: [`requirements/nfr.md`](../requirements/nfr.md)

---

## Epic [E1](../requirements/epics.md#e1) — Discover (검색·발견)

<a id="us-disc-01"></a>
### US-DISC-01 · 자연어 의미 검색 ([P1](personas.md#p1))

- **As a** 박사과정 연구자 박지훈
- **I want** 자신의 연구 의도를 자연어 문장(영문 가능)으로 입력해 의미 유사도 기반 상위 논문을 받기
- **so that** 키워드 노가다 없이 본인 주제와 가까운 선행 연구를 빠르게 발견한다.

**Acceptance Criteria**
```gherkin
Given 박지훈이 검색창에 "transformer-based retrieval-augmented summarization"을 입력
When 검색을 실행한다
Then 시스템은 의미 유사도 기준 상위 20건의 논문 카드를 3초 안에 반환한다
And 각 카드에는 제목, 저자, 연도, 인용수, 유사도 점수가 표시된다
And 결과는 유사도/인용수/최신순으로 재정렬할 수 있다
```

| 필드 | 값 |
|---|---|
| Epic | [E1](../requirements/epics.md#e1) Discover |
| Persona | [P1](personas.md#p1) 박지훈 |
| Priority | **Must** |
| Estimate (SP) | 5 |
| Dependencies | — |
| NFR Keys | [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01), [NFR-DATA-01](../requirements/nfr.md#nfr-data-01), [NFR-DATA-02](../requirements/nfr.md#nfr-data-02), [NFR-UX-03](../requirements/nfr.md#nfr-ux-03) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-disc-02"></a>
### US-DISC-02 · 결과 정렬·필터 ([P1](personas.md#p1))

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

| 필드 | 값 |
|---|---|
| Epic | [E1](../requirements/epics.md#e1) |
| Persona | [P1](personas.md#p1) |
| Priority | **Must** |
| Estimate (SP) | 3 |
| Dependencies | [US-DISC-01](#us-disc-01) |
| NFR Keys | [NFR-UX-03](../requirements/nfr.md#nfr-ux-03) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-disc-03"></a>
### US-DISC-03 · 키워드 자동 확장 ([P1](personas.md#p1))

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

| 필드 | 값 |
|---|---|
| Epic | [E1](../requirements/epics.md#e1) |
| Persona | [P1](personas.md#p1) |
| Priority | **Should** |
| Estimate (SP) | 5 |
| Dependencies | [US-DISC-01](#us-disc-01) |
| NFR Keys | [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-disc-04"></a>
### US-DISC-04 · 학부생 자연어 한국어 검색 ([P2](personas.md#p2))

- **As a** AI 입문 학부생 김민서
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

| 필드 | 값 |
|---|---|
| Epic | [E1](../requirements/epics.md#e1) |
| Persona | [P2](personas.md#p2) |
| Priority | **Should** |
| Estimate (SP) | 5 |
| Dependencies | [US-DISC-01](#us-disc-01) |
| NFR Keys | [NFR-LANG-01](../requirements/nfr.md#nfr-lang-01)·[02](../requirements/nfr.md#nfr-lang-02)·[03](../requirements/nfr.md#nfr-lang-03), [NFR-UX-01](../requirements/nfr.md#nfr-ux-01) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

## Epic [E2](../requirements/epics.md#e2) — Comprehend (이해·해독)

<a id="us-comp-01"></a>
### US-COMP-01 · 전문 모드 핵심 요약 ([P1](personas.md#p1))

- **As a** 박지훈
- **I want** 논문 PDF나 arXiv URL을 입력해 전문 어휘를 유지한 한국어 핵심 요약을 받기
- **so that** 본문 정독 전 가치 가늠에 드는 시간을 줄인다.

**Acceptance Criteria**
```gherkin
Given 박지훈이 arXiv URL을 입력하고 "전문 모드"를 선택
When 요약을 요청한다
Then 시스템은 20초 안에 한국어 요약을 반환한다
And 요약은 "연구 질문 / 방법 / 결과 / 한계" 4개 섹션으로 구분된다
And 학술 전문 어휘는 원형 그대로 보존되고 한국어 표현이 함께 제공된다
```

| 필드 | 값 |
|---|---|
| Epic | [E2](../requirements/epics.md#e2) |
| Persona | [P1](personas.md#p1) |
| Priority | **Must** |
| Estimate (SP) | 5 |
| Dependencies | — |
| NFR Keys | [NFR-PERF-02](../requirements/nfr.md#nfr-perf-02), [NFR-UX-02](../requirements/nfr.md#nfr-ux-02), [NFR-LANG-01](../requirements/nfr.md#nfr-lang-01), [NFR-DATA-02](../requirements/nfr.md#nfr-data-02), [NFR-COST-01](../requirements/nfr.md#nfr-cost-01)·[02](../requirements/nfr.md#nfr-cost-02) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-comp-02"></a>
### US-COMP-02 · 요약 섹션 토글 ([P1](personas.md#p1))

- **As a** 박지훈
- **I want** 요약의 "방법 / 결과 / 한계" 섹션을 접고 펼치기
- **so that** 관심 섹션만 빠르게 비교한다.

**Acceptance Criteria**
```gherkin
Given 전문 모드 요약이 표시된다
When 박지훈이 "방법" 섹션 헤더를 클릭한다
Then 해당 섹션이 접혀 사라지고 다른 섹션 위치가 즉시 갱신된다
And 접힘 상태는 동일 세션 내 다른 요약에도 기본값으로 유지된다
```

| 필드 | 값 |
|---|---|
| Epic | [E2](../requirements/epics.md#e2) |
| Persona | [P1](personas.md#p1) |
| Priority | **Should** |
| Estimate (SP) | 2 |
| Dependencies | [US-COMP-01](#us-comp-01) |
| NFR Keys | [NFR-UX-03](../requirements/nfr.md#nfr-ux-03), [NFR-A11Y-02](../requirements/nfr.md#nfr-a11y-02) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-comp-03"></a>
### US-COMP-03 · 학부 모드 풀어쓰기 요약 ([P2](personas.md#p2))

- **As a** 김민서
- **I want** 학부 1~2학년 수준 한국어로 풀어쓴 요약을 받기 (수식·약어 자동 풀이 포함)
- **so that** 개념과 본질을 정확히 잡는다.

**Acceptance Criteria**
```gherkin
Given 김민서가 동일 논문에 대해 "학부 모드"를 선택
When 요약을 요청한다
Then 시스템은 한국어 능력시험 4급 이하 어휘로 요약을 반환한다
And 본문에 등장한 약어(예: "MLM")는 처음 등장 시 한국어 풀이를 괄호로 제공한다
And 핵심 수식 1~2개에는 한 줄짜리 한국어 자연어 해석이 붙는다
```

| 필드 | 값 |
|---|---|
| Epic | [E2](../requirements/epics.md#e2) |
| Persona | [P2](personas.md#p2) |
| Priority | **Must** |
| Estimate (SP) | 5 |
| Dependencies | [US-COMP-01](#us-comp-01) |
| NFR Keys | [NFR-UX-01](../requirements/nfr.md#nfr-ux-01), [NFR-LANG-01](../requirements/nfr.md#nfr-lang-01)·[03](../requirements/nfr.md#nfr-lang-03) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-comp-04"></a>
### US-COMP-04 · 본문 부분 번역 ([P2](personas.md#p2))

- **As a** 김민서
- **I want** 영문 본문에서 마우스로 선택한 단락을 즉시 한국어로 번역받기
- **so that** 처음 보는 단락도 학습이 끊기지 않는다.

**Acceptance Criteria**
```gherkin
Given 영문 본문 단락이 표시된 상태
When 김민서가 단락을 드래그하여 "번역" 버튼을 누른다
Then 선택 단락의 한국어 번역이 동일 화면 인접 패널에 5초 안에 표시된다
And 학술 용어 사전에 등록된 용어는 일관 번역된다
```

| 필드 | 값 |
|---|---|
| Epic | [E2](../requirements/epics.md#e2) |
| Persona | [P2](personas.md#p2) |
| Priority | **Must** |
| Estimate (SP) | 3 |
| Dependencies | — |
| NFR Keys | [NFR-LANG-01](../requirements/nfr.md#nfr-lang-01)·[03](../requirements/nfr.md#nfr-lang-03), [NFR-PERF-02](../requirements/nfr.md#nfr-perf-02) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-comp-05"></a>
### US-COMP-05 · 시각자료 한 줄 설명 ([P2](personas.md#p2))

- **As a** 김민서
- **I want** 논문에 첨부된 그림/표를 클릭하면 한 줄 한국어 설명을 받기
- **so that** 시각자료의 역할을 빠르게 이해한다.

**Acceptance Criteria**
```gherkin
Given 논문 뷰어에 그림 캡션이 표시된다
When 김민서가 그림을 클릭한다
Then 시스템은 캡션과 주변 문맥을 바탕으로 1~2문장 한국어 설명을 표시한다
```

| 필드 | 값 |
|---|---|
| Epic | [E2](../requirements/epics.md#e2) |
| Persona | [P2](personas.md#p2) |
| Priority | **Could** |
| Estimate (SP) | 5 |
| Dependencies | [US-COMP-01](#us-comp-01) |
| NFR Keys | [NFR-UX-01](../requirements/nfr.md#nfr-ux-01), [NFR-LANG-01](../requirements/nfr.md#nfr-lang-01) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

## Epic [E3](../requirements/epics.md#e3) — Differentiate (차별화·연구 공백)

<a id="us-diff-01"></a>
### US-DIFF-01 · 졸업논문 novelty 검증 ([P1](personas.md#p1))

- **As a** 박지훈
- **I want** 자기 연구 주제 초안을 입력하면 상위 유사 5편과의 차별성 노트를 받기
- **so that** 주제가 중복인지, 어디가 새로운지 판단한다.

**Acceptance Criteria**
```gherkin
Given 박지훈이 연구 주제 초안(200~500자)을 입력
When "차별성 분석"을 요청한다
Then 시스템은 임베딩 유사도 상위 5편 논문을 표시한다
And 각 논문에 대해 "공통점 1줄 / 차이점 1줄" 노트를 제공한다
And 최종 한 문단의 "전반적 novelty 평가"가 함께 출력된다
```

| 필드 | 값 |
|---|---|
| Epic | [E3](../requirements/epics.md#e3) |
| Persona | [P1](personas.md#p1) |
| Priority | **Must** |
| Estimate (SP) | 8 |
| Dependencies | [US-DISC-01](#us-disc-01), [US-COMP-01](#us-comp-01) |
| NFR Keys | [NFR-DATA-02](../requirements/nfr.md#nfr-data-02), [NFR-COST-01](../requirements/nfr.md#nfr-cost-01)·[02](../requirements/nfr.md#nfr-cost-02), [NFR-UX-02](../requirements/nfr.md#nfr-ux-02) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-diff-02"></a>
### US-DIFF-02 · 연구 공백 후보 제안 ([P1](personas.md#p1))

- **As a** 박지훈
- **I want** 자기 주제 초안과 유사 논문을 바탕으로 "다루지 않은 연구 공백 3개" 제안을 받기
- **so that** 주제를 차별화할 후보를 빠르게 얻는다.

**Acceptance Criteria**
```gherkin
Given US-DIFF-01의 차별성 분석 결과가 존재
When 박지훈이 "연구 공백 제안"을 요청한다
Then 시스템은 후보 3개를 짧은 제목과 한 문단 설명으로 제공한다
And 각 후보에 대해 근거가 된 논문 ID를 명시한다
```

| 필드 | 값 |
|---|---|
| Epic | [E3](../requirements/epics.md#e3) |
| Persona | [P1](personas.md#p1) |
| Priority | **Should** |
| Estimate (SP) | 8 |
| Dependencies | [US-DIFF-01](#us-diff-01) |
| NFR Keys | [NFR-DATA-02](../requirements/nfr.md#nfr-data-02), [NFR-COST-01](../requirements/nfr.md#nfr-cost-01) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-diff-03"></a>
### US-DIFF-03 · 학부 수준 가벼운 중복 점검 ([P2](personas.md#p2))

- **As a** 김민서
- **I want** 졸업프로젝트 주제 아이디어를 한국어 자연어로 입력하면 "학부 수준에서 흔한 시도인지 / 차별점 한 줄"을 받기
- **so that** 프로젝트 시작 전에 방향을 가볍게 점검한다.

**Acceptance Criteria**
```gherkin
Given 김민서가 자기 졸업프로젝트 아이디어를 한국어 3~5문장으로 입력
When "가벼운 점검"을 요청한다
Then 시스템은 "비슷한 학부 수준 시도가 있는지" 한 문단 평가를 제공한다
And 자신의 아이디어가 가져갈 수 있는 차별점 1줄 제안을 함께 표시한다
```

| 필드 | 값 |
|---|---|
| Epic | [E3](../requirements/epics.md#e3) |
| Persona | [P2](personas.md#p2) |
| Priority | **Could** |
| Estimate (SP) | 5 |
| Dependencies | [US-DISC-04](#us-disc-04), [US-COMP-03](#us-comp-03) |
| NFR Keys | [NFR-UX-01](../requirements/nfr.md#nfr-ux-01), [NFR-LANG-01](../requirements/nfr.md#nfr-lang-01) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

## Epic [E4](../requirements/epics.md#e4) — Trace (인용 흐름, MVP는 1-hop)

<a id="us-trace-01"></a>
### US-TRACE-01 · 1-hop 인용 그래프 ([P1](personas.md#p1))

- **As a** 박지훈
- **I want** 선택한 논문을 중심으로 직접 인용과 피인용을 1-hop 그래프로 보기
- **so that** 핵심 선행 연구와 영향력 후속 연구를 한눈에 파악한다.

**Acceptance Criteria**
```gherkin
Given 박지훈이 결과 목록에서 한 논문을 선택
When "인용 흐름 보기"를 요청한다
Then 시스템은 중심 노드 + 직접 인용 노드 + 피인용 노드를 5초 안에 표시한다
And 각 노드를 클릭하면 해당 논문 카드가 사이드 패널에 열린다
And 그래프는 최대 30개 노드로 제한되어 가독성을 확보한다
```

| 필드 | 값 |
|---|---|
| Epic | [E4](../requirements/epics.md#e4) |
| Persona | [P1](personas.md#p1) |
| Priority | **Should** |
| Estimate (SP) | 8 |
| Dependencies | [US-DISC-01](#us-disc-01) |
| NFR Keys | [NFR-PERF-03](../requirements/nfr.md#nfr-perf-03), [NFR-DATA-01](../requirements/nfr.md#nfr-data-01)·[02](../requirements/nfr.md#nfr-data-02) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

<a id="us-trace-02"></a>
### US-TRACE-02 · 학부 모드 영향력 Top-3 ([P2](personas.md#p2))

- **As a** 김민서
- **I want** 한 논문에 대해 "이 논문이 영향을 준 후속 논문 Top 3"을 그래프 대신 카드 리스트로 받기
- **so that** 학습 경로를 직선적으로 따라간다.

**Acceptance Criteria**
```gherkin
Given 김민서가 학부 모드에서 한 논문을 선택
When "후속 영향 보기"를 요청한다
Then 시스템은 피인용 수 가중치로 정렬된 후속 논문 3개 카드를 보여 준다
And 그래프 시각화는 표시하지 않는다 (인지 부담 최소화)
```

| 필드 | 값 |
|---|---|
| Epic | [E4](../requirements/epics.md#e4) |
| Persona | [P2](personas.md#p2) |
| Priority | **Could** |
| Estimate (SP) | 3 |
| Dependencies | [US-TRACE-01](#us-trace-01) |
| NFR Keys | [NFR-UX-01](../requirements/nfr.md#nfr-ux-01), [NFR-PERF-03](../requirements/nfr.md#nfr-perf-03) |
| Source-Prompt | [prompts.md#prompt-2](../prompts.md#prompt-2) |

---

## 합계

- **스토리 수**: 14
- **Must 합산 SP**: 29 — [US-DISC-01](#us-disc-01)(5) · [US-DISC-02](#us-disc-02)(3) · [US-COMP-01](#us-comp-01)(5) · [US-COMP-03](#us-comp-03)(5) · [US-COMP-04](#us-comp-04)(3) · [US-DIFF-01](#us-diff-01)(8)
- **Should 합산 SP**: 28 — [US-DISC-03](#us-disc-03)(5) · [US-DISC-04](#us-disc-04)(5) · [US-COMP-02](#us-comp-02)(2) · [US-DIFF-02](#us-diff-02)(8) · [US-TRACE-01](#us-trace-01)(8)
- **Could 합산 SP**: 13 — [US-COMP-05](#us-comp-05)(5) · [US-DIFF-03](#us-diff-03)(5) · [US-TRACE-02](#us-trace-02)(3)
- **MVP 총합 (Must+Should)**: **57 SP / 11 스토리** — 단일 데모 사이클 적정 범위로 평가
