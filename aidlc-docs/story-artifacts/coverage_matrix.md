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

## 1-B. 디바이스 × 페르소나 매트릭스

각 칸은 해당 디바이스에서의 페르소나 주 활동(verb).

| 디바이스 | [P1](personas.md#p1) 박지훈 | [P2](personas.md#p2) 김민서 |
|---|---|---|
| 데스크톱(≥1280px) | 정독 · 노트 작성 · 차별성 분석 | 졸업프로젝트 보고서 작성 · 깊은 학습 |
| 태블릿(768~1279px) | 회의 사이 짧은 요약 확인 | 강의 자료 + 논문 병행 학습 |
| 모바일(<768px) | 통근 중 트리아지(요약·저장·인용 리스트 확인) | 강의 쉬는 시간 개념 검색 · 부분 번역 · 짧은 요약 읽기 |

> 모바일 활동이 두 페르소나 모두에 **명시적**으로 존재한다. 모바일 거동 미정의 스토리는 5단계 INVEST 재검증에서 ⚠️로 표시한다.

## 1-C. 디바이스 × Epic 커버리지

각 칸은 해당 Epic의 모바일 분기를 다루는 스토리 ID (없으면 ❌).

| Epic | 데스크톱 분기 | 모바일 분기 |
|---|---|---|
| [E1](../requirements/epics.md#e1) Discover | DISC-01·02·03·04 (전부) | **DISC-01 AC #모바일** + DISC-04(한국어 우선) |
| [E2](../requirements/epics.md#e2) Comprehend | COMP-01·02·03 | **COMP-04 AC #모바일** (롱프레스 + 바텀시트) + COMP-05 터치 타깃 |
| [E3](../requirements/epics.md#e3) Differentiate | DIFF-01·02·03 | ❗ DIFF-01·02 모바일 거동 미정 — *다음 사이클로 이관 또는 입력 폼 디자인 시 보강* |
| [E4](../requirements/epics.md#e4) Trace | TRACE-01 (그래프) | **TRACE-01 AC #모바일** (간소화 리스트) + TRACE-02 |

> E3에서 모바일 분기 빈 칸 1건 발견. 박지훈의 모바일 시나리오는 *트리아지/큐레이션*에 한정되므로 차별성 분석은 모바일에서 *읽기 전용 결과 확인*만 보장되고 입력은 데스크톱에서 수행한다는 가정을 [`personas.md`](personas.md) §모바일 사용 시나리오에 명시했다.

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

## 4. INVEST 체크리스트 결과 (요약 · 모바일 검증 후 갱신)

추가 검증 축: **M (Mobile)** — 모바일 분기가 본문 또는 AC에서 명시적으로 다뤄지는가.

| 스토리 ID | I | N | V | E | S | T | **M** | 비고 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| [US-DISC-01](user_stories.md#us-disc-01) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 모바일 AC 추가 완료 |
| [US-DISC-02](user_stories.md#us-disc-02) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | 모바일 필터 UI(슬라이드업) 미정 — 디자인 단계로 이월 |
| [US-DISC-03](user_stories.md#us-disc-03) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | 모바일에서 확장 키워드 칩 UI 디자인 단계로 이월 |
| [US-DISC-04](user_stories.md#us-disc-04) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 한국어 입력 자체가 모바일 친화 |
| [US-COMP-01](user_stories.md#us-comp-01) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | 요약 결과 표시 — 모바일에선 섹션 카드형 권장(디자인 단계) |
| [US-COMP-02](user_stories.md#us-comp-02) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | "탭/클릭" 일반화 완료 |
| [US-COMP-03](user_stories.md#us-comp-03) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 학부 모드는 모바일 사용 시나리오의 1차 타깃 |
| [US-COMP-04](user_stories.md#us-comp-04) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 모바일 분기 AC(롱프레스 + 바텀시트) 추가 완료 |
| [US-COMP-05](user_stories.md#us-comp-05) | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | 터치 타깃 44px AC 추가 |
| [US-DIFF-01](user_stories.md#us-diff-01) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | 모바일에선 *읽기 전용 결과 확인*만 허용 (입력은 데스크톱) — 추후 입력 폼 디자인 시 명문화 |
| [US-DIFF-02](user_stories.md#us-diff-02) | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | DIFF-01과 동일 가정 |
| [US-DIFF-03](user_stories.md#us-diff-03) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 학부 모드 가벼운 점검 — 모바일 친화 |
| [US-TRACE-01](user_stories.md#us-trace-01) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | 모바일 분기 AC(간소화 리스트 + 노드 검색) 추가 완료 |
| [US-TRACE-02](user_stories.md#us-trace-02) | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 본래 카드 리스트 — 모바일 친화 |

- **Independent ⚠️**: MVP 의존 그래프가 명확해 허용. 다음 단계에서 *작업 순서*로 흡수.
- **Small ⚠️ (SP 8)**: 3건 — 7단계에서 분해 가능성 의견 받기.
- **Mobile ⚠️ (5건)**: DISC-02·03, COMP-01, DIFF-01·02 — 모바일 UX는 *디자인 단계*에서 별도 보강. 본 사이클의 스토리 본문에는 의도적으로 미루며 위험으로 등재한다.

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
| [NFR-A11Y-03](../requirements/nfr.md#nfr-a11y-03) | [COMP-04](user_stories.md#us-comp-04), [05](user_stories.md#us-comp-05), [TRACE-01](user_stories.md#us-trace-01) |
| [NFR-MOBILE-01](../requirements/nfr.md#nfr-mobile-01) | [DISC-01](user_stories.md#us-disc-01) |
| [NFR-MOBILE-02](../requirements/nfr.md#nfr-mobile-02) | [COMP-04](user_stories.md#us-comp-04), [05](user_stories.md#us-comp-05) |
| [NFR-MOBILE-03](../requirements/nfr.md#nfr-mobile-03) | [DISC-01](user_stories.md#us-disc-01), [TRACE-01](user_stories.md#us-trace-01) |
| [NFR-MOBILE-04](../requirements/nfr.md#nfr-mobile-04) | [DISC-01](user_stories.md#us-disc-01), [COMP-04](user_stories.md#us-comp-04) |
| [NFR-MOBILE-05](../requirements/nfr.md#nfr-mobile-05) | [TRACE-01](user_stories.md#us-trace-01) |
| [NFR-NET-01](../requirements/nfr.md#nfr-net-01) ~ 04 | 📌 모든 스토리에 횡단 적용 — 디자인 단계에서 스토리별 명시 보강 예정 |

> 모든 NFR 키가 최소 1개 스토리에서 인용되었다 ✅. NFR-NET-* 4개는 횡단 관심사이므로 스토리별 인용 대신 디자인 단계의 *공통 기준*으로 위임.
