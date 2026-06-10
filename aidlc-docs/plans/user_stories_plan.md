# 작업 계획서 — User Stories (Inception 단계)

- **단계**: AI-DLC › Inception › User Stories
- **목표**: 고수준 요구사항(논문 리서치 시간 단축 서비스 — 가칭 DocSuri 차세대)을 **개발 계약(contract)으로 기능할 수 있는 사용자 스토리 집합**으로 변환한다.
- **산출물 위치**: `aidlc-docs/story-artifacts/` (스토리), 본 계획서는 `aidlc-docs/plans/`
- **작성 언어**: 한국어
- **작성자 역할**: 시니어 프로덕트 매니저

> ⚠️ 진행 규칙
> - 계획 승인 전에는 어떤 산출물도 만들지 않는다.
> - 각 단계는 끝나는 즉시 체크박스를 닫는다.
> - 사용자 확인이 필요한 결정은 단계 본문 안에 `❓ 확인 필요` 블록으로 표시한다. 사용자가 답하기 전까지 해당 단계를 시작하지 않는다.

---

## 0. 컨텍스트 정리 (사전 단계)

- [x] **0.1** 본 계획에서 사용할 입력 자료를 한 곳에 정렬한다.
  - 입력: Prompt 2에 제공된 5종 페르소나 진술, 사실/행동/목표/골칫거리, 기능 후보 목록
  - 참조 가능 자료: 저장소의 `AGENTS.md`, `Architecture-Report.md`, 기존 `demo/`, `feature-specs/`, `Sprint-Backlog-*.md` (기존 DocSuri 1차 데모 산출물)
  - 산출: 별도 파일 없음 — 1.x 단계에서 활용

  > ❓ **확인 필요 (0.A)**: 이번 스토리 집합은 **기존 DocSuri 데모 위에 진화**하는 형태인가, 아니면 **완전 그린필드로 처음부터 다시** 정의하는 형태인가?
  > - 옵션 A: 기존 데모의 요약/번역/추천 기능을 **이미 존재하는 자산**으로 가정하고 신규 스토리만 작성
  > - 옵션 B: 기존을 무시하고 0번 스토리부터 전부 새로 작성 (이번 세션의 "재시작" 지시와 일관) -> 옵션 B
  > - **권장**: 옵션 B (지시문의 "restart building"과 합치), 단 기존 자산은 *참고용 학습 데이터*로만 활용

---

## 1. 페르소나 정리

- [x] **1.1** Prompt 2에 등장한 5종 페르소나 진술을 분석하여 중복을 제거하고 **MVP 페르소나 후보**를 정리한다.
  - 후보 페르소나 (원문 기반)
    - P1. 박지훈 — 28세, AI 박사과정, 졸업논문 준비 / 주제 중복·트렌드 추적이 어려움
    - P2. 박지훈(변형) — 28세, AI 박사과정 / 재현 불가능한 논문 때문에 시간 손실
    - P3. 30대 연구원 — 일정 과중, 논문 시간 자체를 줄이고 싶음
    - P4. 40대 화장품업계 퇴직자 — AI 입문 학습 목적, 어려운 내용을 쉽게 알고 싶음
    - P5. 대학원생(일반) — 검색·검토 시간 과다
    - P6. 프로젝트 논문 작성 대학원생 — 무관한 검색결과/긴 본문/중복 여부 검증

  > ❓ **확인 필요 (1.A)**: MVP에 포함할 페르소나는 어느 것인가? -> 옵션 C
  > - 옵션 A: **P1+P2 통합(박지훈) 단독** — 가장 강한 페인과 명확한 직업 맥락. 데모 범위에 적합.
  > - 옵션 B: 박지훈 + P6(프로젝트 논문 대학원생) — 핵심 사용 사례 둘
  > - 옵션 C: 박지훈 + P4(AI 입문자) — 난이도 격차가 큰 두 페르소나로 기능 균형 점검
  > - 옵션 D: 5종 모두 — 범위 비대, MVP에 비권장
  > - **권장**: 옵션 B. 양쪽 모두 "리서치 시간 단축"이라는 공동 골칫거리를 공유하면서, P4의 "쉬운 설명" 요구는 사용자 스토리의 비기능 요건(가독성 수준)으로 흡수 가능.

- [x] **1.2** 확정된 페르소나에 대해 다음 4영역(사실·행동·목표·골칫거리)을 1페이지 카드로 정리한다.
  - 산출: `aidlc-docs/story-artifacts/personas.md` ✅

---

## 2. 사용자 스토리의 포맷·메타데이터 합의

- [x] **2.1** 본 프로젝트에서 사용할 사용자 스토리 표준 포맷을 정의한다.  
  - 확정: Connextra(2.A) + Gherkin(2.B) + MoSCoW(2.C) + 피보나치 Story Point(2.D) + NFR 분리(2.E)

  > ❓ **확인 필요 (2.A)**: 스토리 본문 포맷은? -> 옵션 A
  > - 옵션 A (**권장**): Connextra 표준 — `As a <persona>, I want <capability>, so that <benefit>.`
  > - 옵션 B: Job Story 포맷 — `When <상황>, I want to <동기>, so I can <결과>.`
  > - 옵션 C: 한국어 자유 서술

  > ❓ **확인 필요 (2.B)**: Acceptance Criteria 포맷은? -> 옵션 A
  > - 옵션 A (**권장**): Gherkin (Given/When/Then) — 자동화 테스트 시드로 직결
  > - 옵션 B: 불릿 체크리스트
  > - 옵션 C: 둘 다 병기

  > ❓ **확인 필요 (2.C)**: 우선순위 부여 기법은? -> 옵션 A
  > - 옵션 A (**권장**): MoSCoW (Must / Should / Could / Won't-this-cycle)
  > - 옵션 B: RICE 스코어
  > - 옵션 C: 우선순위 부여 생략, Epic 그룹화만 수행

  > ❓ **확인 필요 (2.D)**: 추정치(estimation)을 함께 넣는가? -> 옵션 A
  > - 옵션 A (**권장**): Story Point(피보나치) — 가벼운 상대 추정
  > - 옵션 B: T-shirt size (S/M/L/XL)
  > - 옵션 C: 추정 생략 — Inception 단계의 빠른 확정 우선

  > ❓ **확인 필요 (2.E)**: 비기능 요구(보안·성능·접근성·LLM 비용 등)도 스토리로 표현하는가, 별도 NFR 섹션으로 묶는가? -> 옵션 A
  > - 옵션 A (**권장**): NFR은 별도 `aidlc-docs/requirements/nfr.md`로 분리. 스토리 본문에는 "Definition of Done" 라인으로 NFR 키를 인용.

- [x] **2.2** 스토리 ID 규칙·트레이서빌리티 키 설계  
  - 확정: `US-<EPIC>-<NN>` + `Source-Prompt: prompts.md#prompt-N`
  - 제안 규칙: `US-<EPIC>-<NN>` (예: `US-SUMM-01`, `US-CITE-03`)
  - 각 스토리에 `Source-Prompt: prompts.md#prompt-N` 메타를 박아 출처 역추적 가능하게 함.

  > ❓ **확인 필요 (2.F)**: 위 ID 규칙을 그대로 채택해도 되는가? -> 네.

---

## 3. 기능 후보의 Epic 그룹화

- [x] **3.1** Prompt 2의 기능 후보들을 응집도가 높은 **Epic** 단위로 묶는다.
  - 초안 Epic 후보 (변경 가능)
    - **E1. Discover** — 자연어 검색, 키워드 자동 확장, 관심 분야 필터
    - **E2. Comprehend** — 논문 요약, 번역, 시각 자료 설명, 쉬운 설명(독자 수준 적응)
    - **E3. Differentiate** — 유사도 분석, 중복 아이디어 검증, 연구 공백 탐지
    - **E4. Trace** — 인용·피인용 트리, 기술 흐름 시각화
    - **E5. Trust** — 재현 가능성 자동 평가, 인용 정확성 점검
    - **E6. Stay-Current** — 매일 아침 알림, 분야별 키워드 순위, 자동 검색 예약
    - **E7. Personalize** — 관심 논문/필터 저장, 사용자 컨텍스트 학습

  > ❓ **확인 필요 (3.A)**: 이 7개 Epic 중 **MVP에 포함할 Epic**은? (스토리 개수와 작업량을 결정짓는 핵심 결정)
  > - 옵션 A (**권장**): E1·E2·E3 + E4 일부 — Discover→Comprehend→Differentiate 의 핵심 가치 사슬에 집중. -> 옵션 A
  > - 옵션 B: E1·E2·E3·E4·E6 — 알림까지 포함한 풀버전. 백엔드 스케줄러·인덱싱 비용 큼.
  > - 옵션 C: 사용자가 직접 명시

- [x] **3.2** 확정된 Epic을 `aidlc-docs/requirements/epics.md`에 한 페이지 분량으로 기술한다 (목적·범위·성공 지표·관련 페르소나). ✅

---

## 4. 사용자 스토리 초안 작성

- [x] **4.1** 각 Epic에 대해 **페르소나×Epic** 매트릭스를 만들고, 칸마다 1~3개의 스토리를 도출한다. → 매트릭스는 `coverage_matrix.md §1`
- [x] **4.2** 합의된 포맷(2.A/2.B)에 따라 스토리를 작성한다. 각 스토리는 다음 필드를 가진다.
  - ID, Epic, Persona, Story, Acceptance Criteria, Priority(MoSCoW), Estimate, Dependencies, NFR keys, Source-Prompt
- [x] **4.3** 결과를 단일 파일로 정리한다.
  - 산출: `aidlc-docs/story-artifacts/user_stories.md` (스토리 전체) ✅
  - 부속: `aidlc-docs/story-artifacts/story_index.md` (ID·제목·우선순위만 추린 색인) ✅

  > ❓ **확인 필요 (4.A)**: 스토리 파일을 **Epic당 1파일로 분할**할지, **하나의 마스터 파일**로 둘지? (옵션 A: 분할 → 후속 작업이 단순. 옵션 B: 단일 → 초기 검토 편함. **권장: 옵션 B**.)

---

## 5. 품질 검증 (INVEST + Definition of Ready)

- [x] **5.1** INVEST 체크리스트를 각 스토리에 통과시킨다. → `coverage_matrix.md §4`
- [x] **5.2** 누락된 페르소나·골칫거리·필요 기능이 없는지 Prompt 2 원문과 역추적 검증한다. → `coverage_matrix.md §1·2·3`
- [x] **5.3** 모순·중복 스토리 정리. → `story_index.md` ↔ `user_stories.md` 합계 불일치 1건 발견 후 수정.

---

## 6. 우선순위·릴리스 분류

- [x] **6.1** 2.C에서 합의된 기법으로 모든 스토리를 분류한다 (예: M/S/C/W). → 14개 스토리 모두 MoSCoW 부여 완료.
- [x] **6.2** MVP 후보군(Must) 합산 추정치를 산출하여 단일 데모 범위로 적정한지 점검한다. → **Must 29 SP / 6 스토리, Must+Should 57 SP / 11 스토리**. 데모 사이클 위험 신호: SP 8 스토리 3건(분해 검토 의견 요청). 자세한 내용은 7단계.

---

## 7. 사용자 리뷰 게이트

- [x] **7.1** 위 산출물 일체를 사용자에게 리뷰 요청한다.  
  - 사용자 피드백: [Prompt 10](../prompts.md#prompt-10) (모바일 검토 요청) → [Prompt 11](../prompts.md#prompt-11) (즉시 반영, 권장값 채택) → [Prompt 12](../prompts.md#prompt-12) (옵션 1 통과).
- [x] **7.2** 피드백 반영 후 스토리 파일을 동결(freeze)한다.  
  - 반영: `mobile_review_plan.md` A1~A8 + 후속 2건 일괄 적용.
  - 동결 대상: `personas.md`, `user_stories.md`, `story_index.md`, `coverage_matrix.md`, `epics.md`, `nfr.md`.
  - 정밀화 항목(SP 8 분해, Mobile ⚠️ 5건, Could 처분, NFR-COST 재검증 등)은 **다음 단계 입력**으로 `handoff.md` §2 위험·§4 결정에 이월.

---

## 8. 후속 단계 연결

- [x] **8.1** 동결된 스토리를 다음 단계(Architecture/Design) 입력으로 인계할 수 있도록 `aidlc-docs/story-artifacts/handoff.md`에 인계 노트를 작성한다. ✅
  - 인계 노트에 포함: 미해결 위험(open risks), 가정(assumptions), 다음 단계 결정 필요 사항.

---

## 부록 A — 결정 요약(승인 완료, 2026-06-10)

| ID | 항목 | 최종 결정 |
|---|---|---|
| 0.A | 그린필드 vs 데모 확장 | ✅ **그린필드** (옵션 B) |
| 1.A | MVP 페르소나 | ✅ **박지훈(P1+P2) + AI 입문 대학 학부생(P4 재정의)** — 옵션 C |
| 2.A | 스토리 포맷 | ✅ **Connextra** (옵션 A) |
| 2.B | Acceptance Criteria | ✅ **Gherkin** (옵션 A) |
| 2.C | 우선순위 기법 | ✅ **MoSCoW** (옵션 A) |
| 2.D | 추정치 | ✅ **Story Point 피보나치** (옵션 A) |
| 2.E | NFR 처리 | ✅ **`requirements/nfr.md` 분리** (옵션 A) |
| 2.F | 스토리 ID 규칙 | ✅ `US-<EPIC>-<NN>` 채택 |
| 3.A | MVP Epic 범위 | ✅ **E1·E2·E3 + E4 일부** (옵션 A) |
| 4.A | 스토리 파일 구조 | ✅ **단일 마스터 파일** (옵션 B) |

> Prompt 3 (2026-06-10) 기준 확정. 변경 시 본 표를 업데이트하고 `prompts.md`에 새 결정 로그를 추가한다.
