# Unit U2 — Comprehend (이해·해독)

> 참조: [`epics.md#e2`](../../requirements/epics.md#e2) · [`user_stories.md`](../../story-artifacts/user_stories.md) · [`unit-u0-foundation.md`](unit-u0-foundation.md)

---

## 1. 정체성

- **ID**: U2
- **이름**: Comprehend
- **미션 1줄**: 발견된 논문을 페르소나에 맞게 *요약·번역·풀어쓰기·시각자료 설명* 형태로 변환해, [P1](../../story-artifacts/personas.md#p1)·[P2](../../story-artifacts/personas.md#p2) 모두 본문 정독 전에 가치를 가늠하도록 한다.
- **범위**:
  - **In**: 논문 PDF/URL 입력, 전문 모드/학부 모드 분기 요약, 본문 부분 번역(터치 롱프레스/마우스 드래그), 시각자료 한 줄 설명.
  - **Out**: 검색(→ [U1](unit-u1-discover.md)), 차별성(→ [U3](unit-u3-differentiate.md)), 인용 그래프(→ [U4](unit-u4-trace.md)).

---

## 2. 포함 스토리

본 unit은 [E2 Comprehend](../../requirements/epics.md#e2)의 5개 스토리를 모두 포함한다.

### [US-COMP-01](../../story-artifacts/user_stories.md#us-comp-01) · 전문 모드 핵심 요약 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈
- **I want** 논문 PDF나 arXiv URL을 입력해 전문 어휘를 유지한 한국어 핵심 요약을 받기
- **so that** 본문 정독 전 가치 가늠에 드는 시간을 줄인다.

```gherkin
Given 박지훈이 arXiv URL을 입력하고 "전문 모드"를 선택
When 요약을 요청한다
Then 시스템은 20초 안에 한국어 요약을 반환한다
And 요약은 "연구 질문 / 방법 / 결과 / 한계" 4개 섹션으로 구분된다
And 학술 전문 어휘는 원형 그대로 보존되고 한국어 표현이 함께 제공된다
```
**Priority**: Must · **SP**: 5 · **Dependencies**: — · **NFR**: [NFR-PERF-02](../../requirements/nfr.md#nfr-perf-02), [NFR-UX-02](../../requirements/nfr.md#nfr-ux-02), [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01), [NFR-DATA-02](../../requirements/nfr.md#nfr-data-02), [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01)·[02](../../requirements/nfr.md#nfr-cost-02)

### [US-COMP-02](../../story-artifacts/user_stories.md#us-comp-02) · 요약 섹션 토글 — [P1](../../story-artifacts/personas.md#p1)

- **As a** 박지훈
- **I want** 요약의 "방법 / 결과 / 한계" 섹션을 접고 펼치기
- **so that** 관심 섹션만 빠르게 비교한다.

```gherkin
Given 전문 모드 요약이 표시된다
When 박지훈이 "방법" 섹션 헤더를 탭(터치) 또는 클릭한다
Then 해당 섹션이 접혀 사라지고 다른 섹션 위치가 즉시 갱신된다
And 접힘 상태는 동일 세션 내 다른 요약에도 기본값으로 유지된다
```
**Priority**: Should · **SP**: 2 · **Dependencies**: [US-COMP-01](../../story-artifacts/user_stories.md#us-comp-01) · **NFR**: [NFR-UX-03](../../requirements/nfr.md#nfr-ux-03), [NFR-A11Y-02](../../requirements/nfr.md#nfr-a11y-02)

### [US-COMP-03](../../story-artifacts/user_stories.md#us-comp-03) · 학부 모드 풀어쓰기 요약 — [P2](../../story-artifacts/personas.md#p2)

- **As a** 김민서
- **I want** 학부 1~2학년 수준 한국어로 풀어쓴 요약을 받기 (수식·약어 자동 풀이 포함)
- **so that** 개념과 본질을 정확히 잡는다.

```gherkin
Given 김민서가 동일 논문에 대해 "학부 모드"를 선택
When 요약을 요청한다
Then 시스템은 한국어 능력시험 4급 이하 어휘로 요약을 반환한다
And 본문에 등장한 약어(예: "MLM")는 처음 등장 시 한국어 풀이를 괄호로 제공한다
And 핵심 수식 1~2개에는 한 줄짜리 한국어 자연어 해석이 붙는다
```
**Priority**: Must · **SP**: 5 · **Dependencies**: [US-COMP-01](../../story-artifacts/user_stories.md#us-comp-01) · **NFR**: [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01), [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01)·[03](../../requirements/nfr.md#nfr-lang-03)

### [US-COMP-04](../../story-artifacts/user_stories.md#us-comp-04) · 본문 부분 번역 — [P2](../../story-artifacts/personas.md#p2)

- **As a** 김민서
- **I want** 영문 본문에서 단락을 **터치 롱프레스(모바일) 또는 마우스 드래그(데스크톱)** 로 선택해 즉시 한국어로 번역받기
- **so that** 노트북이든 스마트폰이든 처음 보는 단락에서도 학습이 끊기지 않는다.

```gherkin
Given 영문 본문 단락이 표시된 상태

When 김민서가 데스크톱에서는 단락을 드래그한 뒤 "번역" 버튼을 누른다
Then 선택 단락의 한국어 번역이 동일 화면 인접 패널에 5초 안에 표시된다
And 학술 용어 사전에 등록된 용어는 일관 번역된다

When 김민서가 모바일에서 단락을 약 500ms 롱프레스한다
Then 선택 핸들이 등장하여 단락 경계를 보정할 수 있다
And "번역" 액션이 컨텍스트 메뉴와 바텀시트의 1탭 위치에 노출된다
And 번역 결과는 동일 화면 하단 바텀시트에 5초 안에 표시되고 위로 스와이프하여 전체 화면으로 확장 가능하다
```
**Priority**: Must · **SP**: 3 · **Dependencies**: — · **NFR**: [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01)·[03](../../requirements/nfr.md#nfr-lang-03), [NFR-PERF-02](../../requirements/nfr.md#nfr-perf-02), [NFR-MOBILE-02](../../requirements/nfr.md#nfr-mobile-02)·[04](../../requirements/nfr.md#nfr-mobile-04), [NFR-A11Y-03](../../requirements/nfr.md#nfr-a11y-03)

### [US-COMP-05](../../story-artifacts/user_stories.md#us-comp-05) · 시각자료 한 줄 설명 — [P2](../../story-artifacts/personas.md#p2)

- **As a** 김민서
- **I want** 논문에 첨부된 그림/표를 탭(모바일) 또는 클릭(데스크톱)하면 한 줄 한국어 설명을 받기
- **so that** 시각자료의 역할을 빠르게 이해한다.

```gherkin
Given 논문 뷰어에 그림 캡션이 표시된다
When 김민서가 그림 영역을 탭 또는 클릭한다
Then 시스템은 캡션과 주변 문맥을 바탕으로 1~2문장 한국어 설명을 표시한다
And 그림 영역의 터치 타깃은 가로/세로 모두 44 CSS px 이상이다
```
**Priority**: Could · **SP**: 5 · **Dependencies**: [US-COMP-01](../../story-artifacts/user_stories.md#us-comp-01) · **NFR**: [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01), [NFR-LANG-01](../../requirements/nfr.md#nfr-lang-01), [NFR-MOBILE-02](../../requirements/nfr.md#nfr-mobile-02), [NFR-A11Y-03](../../requirements/nfr.md#nfr-a11y-03)

---

## 3. Cross-unit 의존 (인터페이스 계약)

### 입력 (← [U0 Foundation](unit-u0-foundation.md))

| 사용 포트 | 호출 형태 |
|---|---|
| `LlmPort.complete(prompt, persona)` | 요약·풀어쓰기·번역·캡션 설명 |
| `Glossary.lookup(term)` | 학술 용어 일관 번역 ([NFR-LANG-03](../../requirements/nfr.md#nfr-lang-03)) |
| `CachePort.get/set` | 요약 결과 7d 재사용 ([NFR-DATA-03](../../requirements/nfr.md#nfr-data-03)) |
| `Telemetry.record(...)` | LLM 호출·토큰·비용 누적 |

### 입력 (← 운영자/사용자)

- PDF 파일 또는 arXiv URL 입력 → 본 unit 내부의 PDF 텍스트 추출기.

### 출력 (U2 → 다른 unit) — *유일한 약속*

| DTO | 사용 unit | 스키마(개념) |
|---|---|---|
| `SummaryResult` | [U3 Differentiate](unit-u3-differentiate.md) | `{ paper_id, mode: 'pro'\|'undergrad', sections: { question, method, result, limit }, vocab_explanations: [...], cost: { tokens_in, tokens_out } }` |
| `TranslationResult` | (UI 내부) | `{ source_excerpt, target_text, glossary_hits }` |

---

## 4. Cross-cutting NFRs

| NFR 키 | 본 unit의 책임 |
|---|---|
| [NFR-PERF-02](../../requirements/nfr.md#nfr-perf-02) (단건 요약 P95<20s 데스크톱) | LLM 호출 + 텍스트 추출 + 렌더 |
| [NFR-MOBILE-03](../../requirements/nfr.md#nfr-mobile-03) (4G P95<25s) | 모바일 분기 |
| [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01) (학부 모드 가독성 KKL 4급) | 학부 모드 LLM 프롬프트 + 후처리 검증 |
| [NFR-UX-02](../../requirements/nfr.md#nfr-ux-02) (전문 모드 어휘 보존) | 전문 모드 LLM 프롬프트 |
| [NFR-LANG-03](../../requirements/nfr.md#nfr-lang-03) (학술 용어 사전 일관) | `Glossary` 사용 강제 |
| [NFR-MOBILE-02](../../requirements/nfr.md#nfr-mobile-02) (터치 타깃 ≥44px) | 단락 선택 핸들·번역 버튼·그림 영역 |
| [NFR-A11Y-02](../../requirements/nfr.md#nfr-a11y-02)·[03](../../requirements/nfr.md#nfr-a11y-03) | 섹션 토글 키보드 / 호버 의존 제거 |
| [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01)·[02](../../requirements/nfr.md#nfr-cost-02) | 청크 단위 요약 입력 압축 |

---

## 5. 데이터·외부 의존 (본 unit이 닫는 결정)

- PDF 텍스트 추출 라이브러리 선택 (예: PyMuPDF / pdfplumber / pdf.js). [D1](../../story-artifacts/handoff.md#d-1)·[D5](../../story-artifacts/handoff.md#d-5)에 의해 백엔드/프론트 분담 결정.
- 학부 모드 가독성 측정 지표 — [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01) 만족 검증 도구.
- 모바일 바텀시트 패턴 ([A8](../../story-artifacts/handoff.md#a-8) 가정 확정).

---

## 6. 빌드 가능 정의 (Definition of Buildable)

- [ ] [U0](unit-u0-foundation.md) `LlmPort`를 canned 응답으로 mock해도 5개 스토리 AC 통과
- [ ] 전문/학부 모드 토글이 동일 입력에서 *다른 톤*을 산출
- [ ] [US-COMP-04](../../story-artifacts/user_stories.md#us-comp-04) 데스크톱 드래그·모바일 롱프레스 양쪽 통과
- [ ] [NFR-UX-01](../../requirements/nfr.md#nfr-ux-01) 가독성 측정 자동 보고서 (학부 모드 평균 문장 길이 ≤22 어절)
- [ ] [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01) 시뮬레이션 — 모드별 평균 토큰·비용

---

## 7. 미해결 위험 (본 unit이 닫는 위험)

- [R1](../../story-artifacts/handoff.md#r-1) 일부 — [US-COMP-01](../../story-artifacts/user_stories.md#us-comp-01) 모바일 요약 레이아웃 와이어프레임.
- [R5](../../story-artifacts/handoff.md#r-5) **학술 용어 사전** — 본 unit이 사전 적중률·미충족 케이스를 보고.

---

## 8. 변경 정책

- **단독 변경**: 요약 프롬프트, 모드별 톤, 섹션 토글 UX, 바텀시트 디자인.
- **cross-unit 영향**: `SummaryResult` 스키마 변경 → U3 입력 합의 갱신 필요.
- **금지**: 요약 결과의 *차별성·인용 관계* 정보 추가 (그건 U3·U4의 책임).
