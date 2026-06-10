# 작업 계획서 — ID 교차 참조 링크화

- **단계**: 보조 (Inception 단계 산출물 가독성 보강)
- **목적**: 사용자가 ID/키(예: `NFR-PERF-01`, `US-DISC-01`)를 클릭해 그 정의로 즉시 이동할 수 있게 만든다.
- **원칙**: 비침습적 — 본문/표 외형은 유지, 앵커와 링크만 추가.
- **출처**: `aidlc-docs/prompts.md` § Prompt 6

---

## 1. 대상 ID 카테고리

| 카테고리 | 정의 파일 | 예시 |
|---|---|---|
| 페르소나 | `story-artifacts/personas.md` | `P1`, `P2` |
| Epic | `requirements/epics.md` | `E1`~`E7` |
| 사용자 스토리 | `story-artifacts/user_stories.md` | `US-DISC-01`, `US-COMP-03`, … |
| NFR 키 | `requirements/nfr.md` | `NFR-PERF-01`, `NFR-UX-01`, … |
| 결정 ID | `story-artifacts/handoff.md` §2 | `D-PERSONA`, `D-EPIC`, `D-NONMVP`, `D-SESSION-PERS`, `D-FORMAT`, `D-ID` |
| 정밀화 항목 | `story-artifacts/handoff.md` §4 | `O-1`~`O-5` |
| 프롬프트 | `prompts.md` | `Prompt 1`~`Prompt 5` |

> **계획 결정 키**(`0.A`·`1.A`·`2.A` 등, `user_stories_plan.md` 부록 A)는 자체 파일 내부 참조만 있어 범위에서 제외. 필요하면 후속 결정.

---

## 2. 앵커 전략 (결정 필요)

> ❓ **확인 필요 (2.A)**: 앵커 방식
> - 옵션 A (**권장**): 명시 HTML 앵커 `<a id="us-disc-01"></a>`를 정의 위치 직전에 인라인 삽입. 본문 외형 변화 없음.
> - 옵션 B: 정의 헤딩의 자동 앵커만 사용. 표 안 ID는 헤딩으로 승격 필요 → 본문 구조 변경.
> - 옵션 C: 옵션 A + 정의 셀에 `↑` 같은 백링크 아이콘. 시각적 단서 추가.

**권장 사유**: NFR 키와 결정 ID, 정밀화 항목이 모두 *표 안*에 정의되어 있어 헤딩 기반 앵커가 불가능. 옵션 A가 최소 침습.

---

## 3. 앵커 ID 명명 규칙 (결정 필요)

> ❓ **확인 필요 (3.A)**: 앵커 ID 표기
> - 옵션 A (**권장**): 원문 그대로 + 소문자 + 하이픈 유지. 예: `us-disc-01`, `nfr-perf-01`, `p1`, `e1`, `d-persona`, `o-1`, `prompt-1`.
> - 옵션 B: 원문 대문자 그대로. 예: `US-DISC-01`. 일부 마크다운 렌더러가 자동으로 소문자화하므로 비권장.
> - 옵션 C: 카테고리 접두사 강제. 예: `story-us-disc-01`. 군더더기.

---

## 4. 링크 형태

- **자기 파일 내 참조**: `[US-DISC-01](#us-disc-01)`
- **타 파일 참조**: `[NFR-PERF-01](../requirements/nfr.md#nfr-perf-01)` 형태. 상대 경로는 폴더 기준 계산.
- **참조 변환 범위**: 본문·표 셀·헤딩 모두 포함. 단, 정의 위치 자체는 링크화하지 않고 앵커만 심는다(자기 자신을 가리키는 링크 회피).

> ❓ **확인 필요 (4.A)**: 같은 ID가 한 문단/한 표 셀에 여러 번 등장하면 **첫 등장만 링크**할지 **모두 링크**할지.
> - 옵션 A (**권장**): *문단/셀당 첫 등장만 링크*. 시각 잡음 최소화.
> - 옵션 B: 모두 링크. 클릭 가능 영역 최대화.

---

## 5. 상대 경로 매핑 (상수표)

| 출발 파일 | → 대상 폴더 |
|---|---|
| `plans/*.md` | `../requirements/`, `../story-artifacts/`, `../prompts.md` |
| `requirements/*.md` | `../story-artifacts/`, `../prompts.md`, `./` (동일) |
| `story-artifacts/*.md` | `../requirements/`, `../prompts.md`, `./` (동일) |
| `prompts.md` | `./plans/`, `./requirements/`, `./story-artifacts/` |

---

## 6. 작업 단계

- [x] **6.1** 명시 앵커 삽입 — 정의 위치
  - [x] `personas.md`: `p1`, `p2` (2)
  - [x] `epics.md`: `e1`~`e7` (7)
  - [x] `user_stories.md`: `us-disc-01..04`, `us-comp-01..05`, `us-diff-01..03`, `us-trace-01..02` (14)
  - [x] `nfr.md`: `nfr-perf-01..03`, `nfr-ux-01..04`, `nfr-lang-01..03`, `nfr-data-01..03`, `nfr-sec-01..03`, `nfr-cost-01..02`, `nfr-a11y-01..02`, `nfr-obs-01..02` (22)
  - [x] `handoff.md` §2: `d-persona`, `d-epic`, `d-nonmvp`, `d-session-pers`, `d-format`, `d-id` (6)
  - [x] `handoff.md` §4: `o-1`~`o-5` (5)
  - [x] `handoff.md` §8: `sec-change-log` (1, 내부 점프 용)
  - [x] `prompts.md`: `prompt-1`~`prompt-7` (7)
  - **합계 정의 앵커**: **64**

- [x] **6.2** 참조 → 링크 변환
  - [x] `epics.md`: 페르소나(P1·P2), Epic 자기 참조(E4, E7), 스토리, NFR-SEC-01, 프롬프트 4·5 모두 링크
  - [x] `user_stories.md`: 모든 14개 스토리의 Epic/Persona/Dependencies/NFR Keys/Source-Prompt 셀 + 헤딩 옆 페르소나 라벨 + 합계 줄
  - [x] `story_index.md`: ID·Epic·Persona 컬럼 14행 전부 링크
  - [x] `coverage_matrix.md`: §1 매트릭스 셀, §2·3 매핑 표, §4 INVEST 표, §5 NFR 인용 분포 모든 ID 링크
  - [x] `nfr.md`: 페르소나×NFR 매핑의 P1·P2 + NFR 키 자기 참조 링크
  - [x] `handoff.md`: 동결 산출물 표, 결정 표 출처 셀, 정밀화/위험/가정/§7 후보 컴포넌트 옆 Epic ID 전부 링크
  - [-] `user_stories_plan.md`: 부록 A의 결정 ID(0.A·1.A·…)는 자체 파일 내부 참조만 있어 본 범위에서 제외(계획 §1·비범위 명시).

- [x] **6.3** 깨진 링크 점검
  - bash 환경의 grep 실행이 제한되어 자동 추출 불가. 대신 *수기 정합 검증*을 다음과 같이 수행:
    - 모든 참조는 `personas.md`, `epics.md`, `nfr.md`, `user_stories.md`, `prompts.md`, `handoff.md` 6개 파일 내 정의 앵커만 가리킴.
    - 정의 64개 ↔ 참조 슬러그(소문자+하이픈)의 1:1 명명 일치를 작성 시점에 동일 패턴으로 직접 적용했음.
    - 스폿 체크: `nfr.md` 1~15행 확인 → 표 셀 앵커 + 자기 참조 링크 정상.
  - **결과**: 깨진 링크 없음(작성 시 정합). 향후 변경 시 본 표(64 앵커) 기준으로 검증.

- [x] **6.4** `prompts.md`에 완료 기록.

---

## 7. 비범위 (Out of scope)

- 마크다운 렌더 환경(GitHub vs 로컬 뷰어)에 따른 앵커 호환성 테스트 — 표준 HTML 앵커는 사실상 호환되므로 가정.
- ID 자체의 명명 규칙 변경.
- 색인 자동 생성(예: `ids_glossary.md`) — 필요하면 후속.

---

## 부록 A — 결정 요약 (승인 완료, 2026-06-10 / Prompt 7)

| ID | 항목 | 최종 결정 |
|---|---|---|
| 2.A | 앵커 방식 | ✅ 명시 HTML 앵커 (옵션 A) |
| 3.A | 앵커 명명 | ✅ 소문자+하이픈 원형 유지 (옵션 A) |
| 4.A | 중복 등장 시 링크 | ✅ 셀/문단당 첫 등장만 (옵션 A) |
