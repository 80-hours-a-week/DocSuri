# 작업 계획서 — Units (단위 분해)

- **단계**: AI-DLC › Construction(Architecture/Design) › Unit Decomposition
- **목적**: 동결된 14개 사용자 스토리를 **단일 팀이 독립 빌드 가능한 unit**으로 그룹화한다.
  - *응집도*: unit 내 스토리는 같은 도메인 관심사·데이터·UI 영역을 공유
  - *결합도*: unit 간 상호작용은 **명시적 인터페이스(입력/출력 계약)**로만 일어남
- **출처**: [`prompts.md` § Prompt 17](../prompts.md#prompt-17)
- **입력 자산** (동결됨, PR #10 머지 완료):
  - `aidlc-docs/story-artifacts/user_stories.md` (14 스토리)
  - `aidlc-docs/story-artifacts/personas.md` (P1·P2)
  - `aidlc-docs/requirements/epics.md` (E1·E2·E3·E4 + Won't)
  - `aidlc-docs/requirements/nfr.md` (33 키)
  - `aidlc-docs/story-artifacts/coverage_matrix.md` (의존 그래프 단서)
  - `aidlc-docs/story-artifacts/handoff.md` (D1~D10 미결정, R1~R7 위험)
- **작성 언어**: 한국어

> ⚠️ 진행 규칙
> - 본 계획 승인 전에는 어떤 산출물도 만들지 않는다.
> - 각 단계 종료 시 즉시 체크박스를 닫는다.
> - 결정 필요 항목은 단계 안에 `❓ 확인 필요` 블록 + 부록 A에 1줄 요약을 둔다.

---

## 0. 사전 컨텍스트 정리

- [x] **0.1** 입력 자산의 *동결 상태* 재확인 (PR #10 머지 SHA 기준). ✅ — develop 최신 commit이 PR #10 머지 결과(`b51c1a3` 가정, 본 작업은 head feature 브랜치에서 진행)
- [x] **0.2** 14개 스토리의 의존 그래프를 한 페이지로 그린다. ✅ — 본 §0.2 본문에 ASCII 다이어그램 보존
- [x] **0.3** **링크 컨벤션 사전 준비** — Prompt 18의 추가 결정에 따라 `handoff.md` §2 위험(R1~R7) · §3 가정(A1~A8) · §4 결정(D1~D10)에 HTML 정의 앵커를 삽입. unit 문서에서 `[R1](../../story-artifacts/handoff.md#r-1)` 형태로 링크 가능해짐.
  - `coverage_matrix.md §4` Dependencies 열을 정리하면 다음과 같다:
    ```
    DISC-01 ─┬─ DISC-02
             ├─ DISC-03
             ├─ DISC-04
             └─ TRACE-01

    COMP-01 ─┬─ COMP-02
             ├─ COMP-03
             ├─ COMP-05
             └─ DIFF-01(부분)

    COMP-04 (독립)

    DIFF-01 ─┬─ DIFF-02
             └─ (DISC-01·COMP-01 입력)

    DIFF-03 ── DISC-04·COMP-03 입력

    TRACE-01 ── TRACE-02
    ```

  > ❓ **확인 필요 (0.A)**: 산출물 저장 폴더 — Prompt 17 본문은 "design/ folder"라 했지만 Prompt 1에서 정한 규칙은 `aidlc-docs/design-artifacts/`다.
  > - 옵션 A (**권장**): `aidlc-docs/design-artifacts/units/` — Prompt 1 규칙 + units 하위 폴더 명시
  > - 옵션 B: `aidlc-docs/design-artifacts/` (units 접두사 파일명으로 구분)
  > - 옵션 C: 새 `design/` 폴더 (저장소 루트)

---

## 1. Unit 그룹화 기준 결정

- [x] **1.1** 그룹화 차원(dimension)을 정한다. ✅ Epic 기준 (1.A)

  > ❓ **확인 필요 (1.A)**: 그룹화 기준 —
  > - 옵션 A (**권장**): **Epic 기준** — 4 Epic(E1~E4)이 곧 unit. 도메인 응집도 자연스럽고, 사용자 스토리·NFR·페르소나 매핑이 그대로 유지됨.
  > - 옵션 B: **Layer 기준** — 검색/이해/분석/시각화 등 기술 레이어. 팀 전문성(프론트/백엔드/ML)을 살릴 수 있으나 한 스토리가 여러 레이어를 가로질러 *완성 정의*가 흐려진다.
  > - 옵션 C: **User journey 기준** — 페르소나 시나리오 묶음. UX 일관성 우수하나 백엔드 응집이 깨짐.
  > - 옵션 D: **데이터 의존성 기준** — 임베딩 인덱스 의존 / LLM 의존 / 그래프 API 의존. 인프라 비용 최적화에 강하나 사용자 가치 단위가 흐려짐.

- [x] **1.2** 1.A 결정에 따라 **Foundation/Shared unit**을 둘지 결정한다. ✅ Foundation unit 신설 (1.B)

  > ❓ **확인 필요 (1.B)**: 공통 인프라 처리 —
  > - 옵션 A (**권장**): **Foundation unit 신설** — 임베딩 클라이언트·LLM 게이트웨이·캐시·인증(익명)·관찰가능성을 한 단위로. *모든 도메인 unit이 의존하는 안정 인터페이스*가 됨. handoff.md §4의 D1~D4·D8·D10 결정이 이 unit에서 닫힌다.
  > - 옵션 B: 공통 인프라를 각 도메인 unit에 분산 (중복 위험)
  > - 옵션 C: 별도 unit 아닌 *섹션 문서*로만 처리

---

## 2. Unit 후보 식별 + 응집/결합 분석

- [x] **2.1** 1.A·1.B 결정에 따른 unit 후보를 1쪽 표로 정리한다. ✅ 본 §2.1 초안표 채택

  **권장 결정(A+A)을 가정한 초안** — 변경 가능:

  | Unit ID | 이름 | 포함 스토리 | Epic | 페르소나 | SP 합 |
  |---|---|---|---|---|---|
  | **U0** | Foundation (공통 인프라) | — (인프라) | — | P1·P2 | — |
  | **U1** | Discover | DISC-01·02·03·04 | E1 | P1·P2 | 18 |
  | **U2** | Comprehend | COMP-01·02·03·04·05 | E2 | P1·P2 | 20 |
  | **U3** | Differentiate | DIFF-01·02·03 | E3 | P1·P2 | 21 |
  | **U4** | Trace | TRACE-01·02 | E4 | P1·P2 | 11 |

- [x] **2.2** Unit 경계를 가로지르는 **cross-unit dependency**를 의존 그래프에서 추출. ✅
  - 후보 의존:
    - U3.DIFF-01 ← U1.DISC-01 (검색 결과 입력) + U2.COMP-01 (요약 입력)
    - U3.DIFF-03 ← U1.DISC-04 + U2.COMP-03
    - U4.TRACE-01 ← U1.DISC-01
    - 모든 도메인 unit ← U0 (Foundation)

- [x] **2.3** 각 cross-unit 의존을 **명시적 인터페이스 한 줄**(예: `U1.SearchResult` DTO, `U2.SummarizePort`)로 기록한다.
  - 이 인터페이스가 unit 간 *유일한 합의 지점*이며, 한쪽이 구현 못 해도 mock으로 *독립 빌드*가 가능해야 함. ✅ 각 unit 문서 §3에 박음.

---

## 3. Cross-cutting NFR 처리

- [x] **3.1** NFR-MOBILE/NET/A11Y·NFR-OBS·NFR-SEC는 unit 모두에 횡단 적용된다. 처리 방식 결정. ✅ 각 unit md §4 (3.A)

  > ❓ **확인 필요 (3.A)**: Cross-cutting NFR —
  > - 옵션 A (**권장**): **각 unit md의 *Cross-cutting NFRs* 섹션**에 적용 키 인용 + 책임 경계 한 줄 (예: "U0가 단일 lazy-load 정책 제공, 각 unit은 호출 시 차감")
  > - 옵션 B: 별도 `unit-cross-cutting.md` 단일 문서. 한 곳에 모이나 unit 자기 완결성 떨어짐
  > - 옵션 C: 현행 (NFR 문서가 횡단, unit md는 인용 생략)

---

## 4. Unit 문서 구조 결정

- [x] **4.1** 각 unit md의 표준 섹션을 정한다. ✅ Unit Spec 8섹션 (4.A)

  > ❓ **확인 필요 (4.A)**: 문서 자기 완결도 —
  > - 옵션 A (**권장**): **Unit Spec** — 다음 8개 섹션을 모두 포함하여 *팀 한 명에게 이 한 파일만 줘도 개발 가능*하게 함.
  >   1. 정체성 (이름·범위·미션 1줄)
  >   2. 포함 스토리 (Connextra + Gherkin AC 본문 *복사*)
  >   3. Cross-unit 의존 (입력 인터페이스 + 출력 인터페이스)
  >   4. Cross-cutting NFRs (NFR 키 인용 + 책임 경계)
  >   5. 데이터·외부 의존 (D1~D10 중 본 unit이 닫는 결정)
  >   6. 빌드 가능 정의 (mock 가능 입력·시연 가능 출력)
  >   7. 미해결 위험 (R1~R7 중 본 unit이 닫는 위험)
  >   8. 변경 정책 (이 unit 단독으로 변경 가능한 범위, cross-unit 영향)
  > - 옵션 B: **Unit Index** — ID·제목·우선순위·SP만 색인 + user_stories.md 링크. DRY 우선
  > - 옵션 C: **Unit Brief** — A의 §1·§3·§4·§6만. 가벼움 우선, 자기 완결성 약간 양보

- [x] **4.2** Unit 파일 명명 규칙. ✅ `unit-<id>-<name>.md` (4.B)
  - 적용: `unit-u0-foundation.md`, `unit-u1-discover.md`, `unit-u2-comprehend.md`, `unit-u3-differentiate.md`, `unit-u4-trace.md`, `units-overview.md`

  > ❓ **확인 필요 (4.B)**: 위 명명 규칙을 그대로 채택해도 되는가?

---

## 5. Unit 문서 작성

- [x] **5.1** Foundation unit(U0) 문서 작성 — handoff §4 D1~D4·D8·D10 결정 후보 + 인터페이스 export 정의 ✅ `unit-u0-foundation.md`
- [x] **5.2** Discover unit(U1) 문서 작성 — DISC-01~04 ✅ `unit-u1-discover.md`
- [x] **5.3** Comprehend unit(U2) 문서 작성 — COMP-01~05 ✅ `unit-u2-comprehend.md`
- [x] **5.4** Differentiate unit(U3) 문서 작성 — DIFF-01~03 ✅ `unit-u3-differentiate.md`
- [x] **5.5** Trace unit(U4) 문서 작성 — TRACE-01·02 ✅ `unit-u4-trace.md`
- [x] **5.6** Units overview 문서(`units-overview.md`) — unit 매트릭스 + cross-unit 의존 다이어그램 + 빌드 순서 추천 ✅

---

## 6. 독립 빌드 가능성 검증

- [x] **6.1** 각 unit에 대해 *입력 인터페이스를 mock 했을 때 자기 완결적으로 동작 가능한가*를 점검한다. ✅ 각 unit md §6 "Definition of Buildable"
- [x] **6.2** cross-unit 의존이 **방향성(Acyclic)** 인지 확인 (순환 의존 0건이어야 함). ✅ `units-overview.md §2` 다이어그램
- [x] **6.3** Unit 분해 후의 14개 스토리 → unit 매핑이 *원본 14개와 정확히 일치*하는지 정합 검증 (누락·중복 0). ✅ 14/14 (DISC-01·02·03·04, COMP-01~05, DIFF-01~03, TRACE-01·02 모두 unit 파일에서 ≥1회 참조; 정의 unit은 정확히 1개)

---

## 7. 사용자 리뷰 게이트

- [x] **7.1** 위 산출물을 사용자에게 리뷰 요청 (변경 요청 / 추가 unit 분리 / 합치기 의견 받기). ✅ Prompt 21 "승인"으로 통과.
- [x] **7.2** 피드백 반영 후 unit 정의를 동결한다. ✅ 변경 요청 없음 — `unit-u0~u4-*.md` 6개 문서 + handoff R/A/D 앵커 25개 동결.

---

## 8. 후속 단계 연결

- [x] **8.1** 동결된 unit 정의를 `handoff.md`의 §2 위험·§4 결정에 매핑 갱신 (어느 unit이 어느 위험·결정을 닫는지 명시). ✅ §2에 "닫는 Unit" 컬럼, §4에 "진입 Unit" 컬럼 추가.
- [x] **8.2** 다음 설계 단계(API/Data model/Component 설계)의 입력으로 정렬. ✅ §5 권장 입력 순서를 U0→(U1·U2 병렬)→(U3·U4 병렬) 흐름으로 재정렬. 헤더에 **Inception 단계 종료** 마커 추가.

---

## 부록 A — 결정 요약 (승인 완료, 2026-06-10 / Prompt 18)

| ID | 항목 | 최종 결정 |
|---|---|---|
| 0.A | 산출물 저장 폴더 | ✅ **`aidlc-docs/design-artifacts/units/`** |
| 1.A | 그룹화 기준 | ✅ **Epic 기준** |
| 1.B | 공통 인프라 처리 | ✅ **Foundation unit 신설** |
| 3.A | Cross-cutting NFR | ✅ 각 unit md의 NFRs 섹션에 인용 |
| 4.A | 문서 자기 완결도 | ✅ **Unit Spec 8섹션** |
| 4.B | 파일 명명 규칙 | ✅ `unit-<id>-<name>.md` |
| **+** | **링크 컨벤션** | ✅ **Prompt 6·7의 id_linking 동일 적용** — NFR-* / US-* / P1·P2 / E1~E4 / R* / D* / A* 모두 정의 위치 링크 |

> 가정 확정: unit 5개(U0 Foundation + U1~U4) · 문서 6개(5 + overview).

---

## 사용자에게 요청

부록 A의 6개 결정 항목에 대해

1. **권장안 전부 채택**,
2. **일부 수정** — 어느 항목을 어떻게,
3. **별도 안 제시**

중 하나로 답해 주세요. 승인 후 0단계부터 한 단계씩 실행하며 체크박스를 닫겠습니다. 승인 전까지 산출물 생성은 보류합니다.
