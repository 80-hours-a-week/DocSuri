# DocSuri MVP — Inception ▶ Architecture/Design 인계 노트

- **단계**: AI-DLC › Inception › User Stories 종료, Architecture/Design 시작
- **동결 일자**: 2026-06-10
- **승인 근거**: [`aidlc-docs/prompts.md`](../prompts.md) § [Prompt 1](../prompts.md#prompt-1)·[2](../prompts.md#prompt-2)·[3](../prompts.md#prompt-3)·[4](../prompts.md#prompt-4)·[5](../prompts.md#prompt-5)

---

## 1. 동결 산출물 (Frozen Artifacts)

| 경로 | 역할 |
|---|---|
| [`personas.md`](personas.md) | [P1](personas.md#p1) 박지훈 / [P2](personas.md#p2) 김민서 페르소나 카드 |
| [`user_stories.md`](user_stories.md) | 14 스토리 마스터 (Connextra + Gherkin AC) |
| [`story_index.md`](story_index.md) | 우선순위·SP 색인 |
| [`coverage_matrix.md`](coverage_matrix.md) | 페르소나×Epic·INVEST·NFR 인용 검증 |
| [`requirements/epics.md`](../requirements/epics.md) | 4개 MVP Epic + 비포함 Epic 사유 |
| [`requirements/nfr.md`](../requirements/nfr.md) | NFR-PERF/UX/LANG/DATA/SEC/COST/A11Y/OBS |

> 위 6개 파일은 Architecture/Design 단계에서 **참조 전용**으로 다룬다. 변경이 필요할 경우 새 결정 로그를 [`prompts.md`](../prompts.md)에 추가하고 본 인계 노트의 [§8 변경 로그](#sec-change-log)를 갱신한다.

---

## 2. 핵심 결정 요약

| 결정 ID | 내용 | 출처 |
|---|---|---|
| <a id="d-persona"></a>D-PERSONA | MVP 페르소나는 [P1](personas.md#p1) 박지훈(전문) + [P2](personas.md#p2) 김민서(학부 입문) — 양극단 분기 검증 | [Prompt 3](../prompts.md#prompt-3) (옵션 C) |
| <a id="d-epic"></a>D-EPIC | MVP Epic = [E1](../requirements/epics.md#e1) Discover · [E2](../requirements/epics.md#e2) Comprehend · [E3](../requirements/epics.md#e3) Differentiate · [E4](../requirements/epics.md#e4) Trace(1-hop) | [`plans/user_stories_plan.md`](../plans/user_stories_plan.md) 결정 3.A |
| <a id="d-nonmvp"></a>D-NONMVP | 비포함 Epic = [E5](../requirements/epics.md#e5) Trust · [E6](../requirements/epics.md#e6) Stay-Current · [E7](../requirements/epics.md#e7) Personalize(영속) | [`epics.md`](../requirements/epics.md), [Prompt 5](../prompts.md#prompt-5) |
| <a id="d-session-pers"></a>D-SESSION-PERS | 세션 한정 개인화는 모드 토글·주제 컨텍스트·필터 URL 직렬화로 흡수 | [`epics.md`](../requirements/epics.md) "세션 한정 개인화는 어디에?" |
| <a id="d-format"></a>D-FORMAT | Connextra + Gherkin AC + MoSCoW + 피보나치 SP + NFR 별도 파일 | [`plans/user_stories_plan.md`](../plans/user_stories_plan.md) 결정 2.A–2.E |
| <a id="d-id"></a>D-ID | `US-<EPIC>-<NN>` + `Source-Prompt:` 메타 | [`plans/user_stories_plan.md`](../plans/user_stories_plan.md) 결정 2.F |

---

## 3. MVP 범위 수치

- 총 스토리: **14** (70 SP)
- MVP(Must+Should): **11 / 57 SP**
- Must만: **6 / 29 SP**
- 비MVP(Could): 3 / 13 SP

---

## 4. 다음 단계가 답해야 할 정밀화 항목

본 단계에서 *의도적으로 미뤘던* 결정들. Architecture/Design 진입 직후에 처리해야 한다.

| ID | 항목 | 권장 처리 시점 |
|---|---|---|
| <a id="o-1"></a>O-1 | SP 8 스토리 3건 분해 여부 — [`US-DIFF-01`](user_stories.md#us-diff-01), [`US-DIFF-02`](user_stories.md#us-diff-02), [`US-TRACE-01`](user_stories.md#us-trace-01) | Architecture 첫 주, 컴포넌트 분리 후 |
| <a id="o-2"></a>O-2 | Could 3건 본 사이클 처분 — [`US-COMP-05`](user_stories.md#us-comp-05), [`US-DIFF-03`](user_stories.md#us-diff-03), [`US-TRACE-02`](user_stories.md#us-trace-02) | MVP 범위 동결 직전 (잔여 capacity 확인 후) |
| <a id="o-3"></a>O-3 | "세션 스코프 상태 모델"의 구체 매체 — React Context vs URL 쿼리 vs localStorage(읽기 전용) | UI 컴포넌트 설계 시 |
| <a id="o-4"></a>O-4 | LLM 비용 모니터링 메커니즘 — [NFR-OBS-02](../requirements/nfr.md#nfr-obs-02) 구현 위치 | 백엔드 아키텍처 결정 시 |
| <a id="o-5"></a>O-5 | 한국어 가독성([NFR-UX-01](../requirements/nfr.md#nfr-ux-01)) 자동 측정 가능성 — 도구 부재 시 휴리스틱 정의 | [E2](../requirements/epics.md#e2) 컴포넌트 설계 시 |

---

## 5. 가정 (Assumptions)

| 가정 | 검증 방법 |
|---|---|
| arXiv 메타데이터 + Semantic Scholar API의 무료/저비용 티어로 MVP 트래픽 처리 가능 | Architecture 단계의 *데이터 파이프라인 PoC*에서 rate limit 측정 |
| 데모 LLM 월 USD 50 한도로 Must 스토리 시연이 가능 | [NFR-COST-01](../requirements/nfr.md#nfr-cost-01) + 캐시([NFR-DATA-03](../requirements/nfr.md#nfr-data-03))로 시뮬레이션 |
| 비로그인 익명 세션만으로 사용자 가치 절반 이상 전달 가능 | 페르소나 인터뷰 또는 데모 후 피드백 |
| 한국어/영어 자연어 입력은 동일 임베딩 모델에서 충분한 의미 보존 | [E1](../requirements/epics.md#e1) 컴포넌트 설계 시 다국어 임베딩 모델 평가 |

---

## 6. 위험 (Risks)

| 위험 | 영향 | 완화 방향 |
|---|---|---|
| [US-DIFF-01](user_stories.md#us-diff-01)·[02](user_stories.md#us-diff-02)의 LLM 토큰 사용량 폭증 | [NFR-COST-01](../requirements/nfr.md#nfr-cost-01) 초과 | 청크 압축 + 결과 캐시 우선 적용 ([NFR-COST-02](../requirements/nfr.md#nfr-cost-02) / [NFR-DATA-03](../requirements/nfr.md#nfr-data-03)) |
| Semantic Scholar 그래프 API rate limit | [E4](../requirements/epics.md#e4) 무력화 | 백오프 + 캐시 + 무료 티어 한도 시뮬레이션 |
| 학부 모드 가독성([NFR-UX-01](../requirements/nfr.md#nfr-ux-01)) 자동 검증 불가 | 품질 일관성 저하 | 휴리스틱(평균 문장 길이·약어 풀이 비율) + 샘플 수동 검토 |
| 인용 그래프 컴포넌트([US-TRACE-01](user_stories.md#us-trace-01)) SP 8 | 단일 이터레이션 초과 위험 | [O-1](#o-1)로 분해 가능성 평가 |
| 영속 개인화 부재로 인한 데모 UX 단절 | 재방문 사용자 이탈 | URL 직렬화([US-DISC-02](user_stories.md#us-disc-02))로 부분 완화, 그 이상은 후속 사이클 |

---

## 7. Architecture/Design 단계의 첫 번째 결정 후보

[Prompt 1](../prompts.md#prompt-1)의 지시("모든 프론트엔드·백엔드 컴포넌트마다 프로젝트 폴더")를 반영하면, 다음 단계는 **시스템 컴포넌트 분리 결정**으로 시작하는 것이 자연스럽다.

- 후보 컴포넌트
  - **(A) Search & Discovery API** — 검색·임베딩·정렬·필터 ([E1](../requirements/epics.md#e1) + 공통)
  - **(B) Comprehension Service** — 요약·번역·풀어쓰기 ([E2](../requirements/epics.md#e2))
  - **(C) Differentiation Service** — novelty·gap 분석 ([E3](../requirements/epics.md#e3), A·B 결과 소비)
  - **(D) Citation Graph Service** — 1-hop 인용 그래프 ([E4](../requirements/epics.md#e4))
  - **(E) Ingestion / Indexing Pipeline** — 코퍼스 수집·임베딩 갱신
  - **(F) Web Frontend** — 검색UI·뷰어·그래프·모드 토글
- 후보 폴더 구조: `app/<component>/` 또는 `services/<component>/` — 다음 계획서에서 결정.

---

<a id="sec-change-log"></a>
## 8. 변경 로그 (이후 갱신)

| 일자 | 변경 | 출처 |
|---|---|---|
| 2026-06-10 | 초기 동결 | [Prompt 5](../prompts.md#prompt-5) |
| 2026-06-10 | ID·키 교차 참조 링크 일괄 적용 | [Prompt 7](../prompts.md#prompt-7) |
