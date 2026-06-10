# DocSuri MVP — 커버리지 매트릭스

본 파일은 **[Prompt 2](../prompts.md#prompt-2) 원문**에 등장한 페르소나·골칫거리·기능 후보가 사용자 스토리에 모두 매핑되었는지 확인한다.

---

## 1. 페르소나 × Epic 매트릭스

각 칸의 값은 해당 페르소나·Epic을 다루는 스토리 ID.

| 페르소나 | [E1](../requirements/epics.md#e1) Discover | [E2](../requirements/epics.md#e2) Comprehend | [E3](../requirements/epics.md#e3) Differentiate | [E4](../requirements/epics.md#e4) Trace |
|---|---|---|---|---|
| [P1](personas.md#p1) 박지훈 | [DISC-01](user_stories.md#us-disc-01), [02](user_stories.md#us-disc-02), [03](user_stories.md#us-disc-03) | [COMP-01](user_stories.md#us-comp-01), [02](user_stories.md#us-comp-02) | [DIFF-01](user_stories.md#us-diff-01), [02](user_stories.md#us-diff-02) | [TRACE-01](user_stories.md#us-trace-01) |
| [P2](personas.md#p2) 김민서 | [DISC-04](user_stories.md#us-disc-04) | [COMP-03](user_stories.md#us-comp-03), [04](user_stories.md#us-comp-04), [05](user_stories.md#us-comp-05) | [DIFF-03](user_stories.md#us-diff-03) | [TRACE-02](user_stories.md#us-trace-02) |

> 두 페르소나 모두 4개 Epic 전부를 최소 1개 스토리로 커버한다. **빈 칸 없음** ✅.

---

## 2. Prompt 2의 골칫거리 → 스토리 매핑

| 원문 골칫거리 | 처리 스토리 | 비고 |
|---|---|---|
| DB 시스템 부정확성·신호잡음 낮음 | [US-DISC-01](user_stories.md#us-disc-01), [02](user_stories.md#us-disc-02), [03](user_stories.md#us-disc-03) | 의미 검색 + 정렬·필터 + 키워드 확장으로 대응 |
| 논문 전체를 읽어야 한다 | [US-COMP-01](user_stories.md#us-comp-01), [02](user_stories.md#us-comp-02), [03](user_stories.md#us-comp-03) | 전문·학부 모드 요약 |
| 트렌드에 뒤쳐짐 | [US-DISC-02](user_stories.md#us-disc-02) (연도·인용 정렬) | 데일리 알림은 [E6](../requirements/epics.md#e6), 본 사이클 비포함 |
| 중복 여부 파악을 위한 검색 반복 | [US-DIFF-01](user_stories.md#us-diff-01) | novelty 검증 단일 진입점 |
| 검증되더라도 시간 오래 걸림 | [US-DIFF-01](user_stories.md#us-diff-01), [02](user_stories.md#us-diff-02) | 차별성 노트 + 공백 제안 |
| 논문이 너무 많음 | [US-DISC-01](user_stories.md#us-disc-01)·[02](user_stories.md#us-disc-02) (Top-N + 필터) | 결과 제한 + 필터 |
| 영어 장벽 / 어려움 | [US-COMP-03](user_stories.md#us-comp-03), [04](user_stories.md#us-comp-04) | 학부 모드 풀어쓰기 + 부분 번역 |
| 답변이 이상함 / 출처 모름 | [NFR-DATA-02](../requirements/nfr.md#nfr-data-02) (모든 요약에 원문 링크) | 스토리 본문이 아닌 NFR로 강제 |

---

## 3. Prompt 2의 기능 후보 → 스토리/Epic 매핑

| 기능 후보 | 처리 위치 | MVP 여부 |
|---|---|---|
| 자연어 검색 | [US-DISC-01](user_stories.md#us-disc-01), [04](user_stories.md#us-disc-04) | ✅ Must / Should |
| 키워드 자동 확장 | [US-DISC-03](user_stories.md#us-disc-03) | ✅ Should |
| 논문 요약 | [US-COMP-01](user_stories.md#us-comp-01), [03](user_stories.md#us-comp-03) | ✅ Must |
| 논문 번역 | [US-COMP-04](user_stories.md#us-comp-04) | ✅ Must |
| 시각 자료 설명 | [US-COMP-05](user_stories.md#us-comp-05) | △ Could |
| 유사 논문 탐색 | [US-DISC-01](user_stories.md#us-disc-01) + [US-DIFF-01](user_stories.md#us-diff-01) | ✅ Must |
| 연구 공백 분석 | [US-DIFF-02](user_stories.md#us-diff-02) | ✅ Should |
| 이미 존재하는 아이디어 확인 | [US-DIFF-01](user_stories.md#us-diff-01), [03](user_stories.md#us-diff-03) | ✅ Must / Could |
| 인용/피인용 트리 | [US-TRACE-01](user_stories.md#us-trace-01), [02](user_stories.md#us-trace-02) | ✅ Should / Could |
| 매일 아침 알림 | — | ❌ Won't ([E6](../requirements/epics.md#e6)) |
| 키워드 순위 / 트렌드 데일리 | — | ❌ Won't ([E6](../requirements/epics.md#e6)) |
| 논문 자동 검색 예약 | — | ❌ Won't ([E6](../requirements/epics.md#e6)) |
| 재현 가능성 자동 평가 | — | ❌ Won't ([E5](../requirements/epics.md#e5)) |
| 검색 필터 저장 / 개인화 | — | ❌ Won't ([E7](../requirements/epics.md#e7)) |

> 비포함 후보 5개 모두 [`epics.md`](../requirements/epics.md)의 Won't 표에 기록되어 후속 사이클 재평가 대상.

---

## 4. INVEST 체크리스트 결과 (요약)

| 스토리 ID | I | N | V | E | S | T | 비고 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| [US-DISC-01](user_stories.md#us-disc-01) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| [US-DISC-02](user_stories.md#us-disc-02) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | [DISC-01](user_stories.md#us-disc-01) 의존 — Independent 약함, MVP에서는 허용 |
| [US-DISC-03](user_stories.md#us-disc-03) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | [DISC-01](user_stories.md#us-disc-01) 의존 |
| [US-DISC-04](user_stories.md#us-disc-04) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | [DISC-01](user_stories.md#us-disc-01) 의존 |
| [US-COMP-01](user_stories.md#us-comp-01) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| [US-COMP-02](user_stories.md#us-comp-02) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | [COMP-01](user_stories.md#us-comp-01) 의존 |
| [US-COMP-03](user_stories.md#us-comp-03) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | [COMP-01](user_stories.md#us-comp-01)과 출력 분기 공유 |
| [US-COMP-04](user_stories.md#us-comp-04) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| [US-COMP-05](user_stories.md#us-comp-05) | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ✅ | 시각자료 위치 검출이 단순화로 제어됨 |
| [US-DIFF-01](user_stories.md#us-diff-01) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | SP 8 — 분해 검토 후보 |
| [US-DIFF-02](user_stories.md#us-diff-02) | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ✅ | [DIFF-01](user_stories.md#us-diff-01) 의존 + SP 8 |
| [US-DIFF-03](user_stories.md#us-diff-03) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | [DISC-04](user_stories.md#us-disc-04) 의존 |
| [US-TRACE-01](user_stories.md#us-trace-01) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | 그래프 컴포넌트 SP 8 |
| [US-TRACE-02](user_stories.md#us-trace-02) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | [TRACE-01](user_stories.md#us-trace-01) 데이터 공유 |

- **Independent ⚠️**: MVP 의존 그래프가 명확해 허용. 다음 단계에서 *작업 순서*로 흡수.
- **Small ⚠️ (SP 8)**: 3건 — 5/6단계에서 분해 가능성 의견 받기.

---

## 5. NFR 인용 분포

| NFR 키 | 인용 스토리 |
|---|---|
| [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01) | [DISC-01](user_stories.md#us-disc-01), [03](user_stories.md#us-disc-03) |
| [NFR-PERF-02](../requirements/nfr.md#nfr-perf-02) | [COMP-01](user_stories.md#us-comp-01), [04](user_stories.md#us-comp-04) |
| [NFR-PERF-03](../requirements/nfr.md#nfr-perf-03) | [TRACE-01](user_stories.md#us-trace-01), [02](user_stories.md#us-trace-02) |
| [NFR-UX-01](../requirements/nfr.md#nfr-ux-01) | [DISC-04](user_stories.md#us-disc-04), [COMP-03](user_stories.md#us-comp-03), [05](user_stories.md#us-comp-05), [DIFF-03](user_stories.md#us-diff-03), [TRACE-02](user_stories.md#us-trace-02) |
| [NFR-UX-02](../requirements/nfr.md#nfr-ux-02) | [COMP-01](user_stories.md#us-comp-01), [DIFF-01](user_stories.md#us-diff-01) |
| [NFR-UX-03](../requirements/nfr.md#nfr-ux-03) | [DISC-01](user_stories.md#us-disc-01), [02](user_stories.md#us-disc-02), [COMP-02](user_stories.md#us-comp-02) |
| [NFR-LANG-01](../requirements/nfr.md#nfr-lang-01) | [DISC-04](user_stories.md#us-disc-04), [COMP-03](user_stories.md#us-comp-03), [04](user_stories.md#us-comp-04), [05](user_stories.md#us-comp-05), [DIFF-03](user_stories.md#us-diff-03) |
| [NFR-DATA-01](../requirements/nfr.md#nfr-data-01) | [DISC-01](user_stories.md#us-disc-01), [TRACE-01](user_stories.md#us-trace-01) |
| [NFR-DATA-02](../requirements/nfr.md#nfr-data-02) | [DISC-01](user_stories.md#us-disc-01), [COMP-01](user_stories.md#us-comp-01), [DIFF-01](user_stories.md#us-diff-01), [02](user_stories.md#us-diff-02), [TRACE-01](user_stories.md#us-trace-01) |
| [NFR-COST-01](../requirements/nfr.md#nfr-cost-01) | [COMP-01](user_stories.md#us-comp-01), [DIFF-01](user_stories.md#us-diff-01), [02](user_stories.md#us-diff-02) |
| [NFR-A11Y-02](../requirements/nfr.md#nfr-a11y-02) | [COMP-02](user_stories.md#us-comp-02) |

> 모든 NFR 키가 최소 1개 스토리에서 인용되었다 ✅.
