# 작업 계획서 — Inception 단계 종료 마무리 PR (네 번째)

- **단계**: 보조 (AI-DLC › Inception 단계 *공식 종료* 작업을 develop으로 PR)
- **출처**: [`prompts.md` § Prompt 23](../prompts.md#prompt-23)
- **선행 PR**:
  - [PR #9](https://github.com/80-hours-a-week/DocSuri/pull/9) — Inception 1차 (commit `7575fc3`, merge `487662b`) ✅
  - [PR #10](https://github.com/80-hours-a-week/DocSuri/pull/10) — 모바일 검토 + handoff 동결 (commit `0ba0a22`, merge `734db65`) ✅
  - [PR #11](https://github.com/80-hours-a-week/DocSuri/pull/11) — Unit Decomposition (commit `d1b45d7`, merge `adefb60`) ✅
- **현재 상태**: `develop` 브랜치(HEAD `adefb60`, origin과 동기). 본 작업은 *Inception 단계 종료 마커*를 develop에 명시적으로 박아 다음 agent(Construction)의 출발선을 깨끗하게 한다.

---

## 1. 브랜치 전략

- **결정 (권장)**: **새 브랜치** `feature/aidlc-inception-closure` 분기.
- **근거**:
  - 이전 `feature/aidlc-inception-user-stories`는 PR #9·#10·#11 모두 머지되어 *임무 완료*. 같은 브랜치를 4번째로 재사용하면 의미상 *Unit Decomposition* 작업이 계속되는 듯한 인상.
  - 본 PR의 성격(*Inception 단계 종료*)은 새로운 작업 묶음이므로 새 브랜치가 명확.
- **분기 기준**: `develop` (현재 위치, HEAD `adefb60`).

> ❓ **확인 필요 (1.A)**: 브랜치 이름 — 옵션
> - A (**권장**): `feature/aidlc-inception-closure`
> - B: `feature/aidlc-inception-user-stories` 재사용 (4번째 PR 누적)
> - C: 사용자 제안

---

## 2. 커밋 범위 (Scope discipline)

**포함 (단일 커밋, 5 파일)**

| 파일 | 상태 | 변경 핵심 |
|---|---|---|
| `aidlc-docs/plans/git_flow_pr4_plan.md` | **신규** | 본 계획서 자체 |
| `aidlc-docs/plans/git_flow_pr3_plan.md` | M | 5.4 결과 메모 (커밋 `d1b45d7`, [PR #11](https://github.com/80-hours-a-week/DocSuri/pull/11) URL) |
| `aidlc-docs/plans/units_plan.md` | M | §7·§8 클로즈 (Prompt 21 통과, handoff 매핑·종료 마커 반영) |
| `aidlc-docs/prompts.md` | M | Prompt 19 완료 줄 + Prompt 21·22·23 (+ 5.4 후 PR4 완료 줄) |
| `aidlc-docs/story-artifacts/handoff.md` | M | **Inception 단계 종료 마커** + §1 Unit 행 + §2·§4 unit 매핑 컬럼 + §5 진입 순서 재정렬 |

**제외 (이 PR과 무관, 손대지 않음)**

| 파일/경로 | 비고 |
|---|---|
| `.DS_Store` | macOS 메타 |
| `demo/app/infra/llm/bedrock.py`, `mock.py` | 데모 인프라 |
| `demo/scripts/smoke.sh`, `demo/tests/*`, `demo/web/*` | 데모 영역 |
| `web/src/app/api/recommend/route.ts` | 추천 API |
| `.claude/`, `.playwright-mcp/` | 로컬 도구 캐시 |
| `after-fix-*.png`, `docsuri-*.png`, `initial-load.png` | 디버그 스크린샷 |

> ❓ **확인 필요 (2.A)**: §2 제외 6종 그대로? (PR #9·#10·#11과 동일)

---

## 3. 커밋 메시지 (초안)

```
docs(aidlc): close Inception stage and freeze handoff for Construction

PR #11 머지 이후 작성된 Inception 단계 *공식 종료* 산출물을 단일 커밋으로 정리.

- handoff.md 헤더에 "Inception 단계 종료 ✅ 2026-06-10" 마커 박음
- handoff.md §1 동결 산출물 표에 Unit 분해 행 추가 (prompts 범위 1~22)
- handoff.md §2 위험 표에 "닫는 Unit" 컬럼 추가 (R1~R7 모두 unit에 할당)
- handoff.md §4 결정 표에 "진입 Unit" 컬럼 추가 (U0에 7개 결정 집중 명시)
- handoff.md §5 권장 입력 순서를 U0 → (U1·U2 병렬) → (U3·U4 병렬)로 재정렬
- units_plan.md §7·§8 클로즈 (Prompt 21 리뷰 게이트 통과)
- git_flow_pr3_plan.md 5.4 결과 메모 (PR #11 URL)
- prompts.md Prompt 19 완료 줄 + Prompt 21·22·23

AGENTS.md §2 (페르소나) · §3 (Feature Topology) · §7.5 (PR Review 의례)
맥락의 Sprint 2 Inception 단계 공식 종료. 다음 agent는 Construction
(Architecture Decision Records, U0 진입)으로 진입한다.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

> ❓ **확인 필요 (3.A)**: 메시지 길이/형식 의견 있는가? (영문 prefix `docs(aidlc):` + 한국어 본문 + AGENTS.md 인용)

---

## 4. PR 본문 (초안)

```
## Summary

- AI-DLC Inception 단계 **공식 종료** — handoff.md 헤더에 종료 마커 박음
- handoff.md §2 위험·§4 결정에 *닫는 unit*/*진입 unit* 컬럼 추가 (PR #11 unit 분해 결과 반영)
- handoff.md §5 권장 입력 순서를 unit 분해 흐름(U0 → U1·U2 병렬 → U3·U4 병렬)으로 재정렬
- 계획서 4개 모두 체크박스 100% 클로즈 (units_plan.md §7·§8 포함)
- AGENTS.md §2·§3·§7.5 맥락의 Sprint 2 Inception 단계 동결본 최종.
- **다음 단계는 Construction (Architecture Decision Records, U0 진입)** — 별도 agent가 담당.

## 변경 트리

aidlc-docs/
├── plans/
│   ├── git_flow_pr4_plan.md (신규)
│   ├── git_flow_pr3_plan.md (PR #11 결과 메모)
│   └── units_plan.md (§7·§8 클로즈)
├── prompts.md (Prompt 19 완료 + Prompt 21·22·23)
└── story-artifacts/
    └── handoff.md (종료 마커 + §1·§2·§4·§5 unit 매핑)

## 선행 PR

- 머지 완료: #9 (Inception 1차) · #10 (모바일 검토) · #11 (Unit 분해)

## Inception 단계 산출물 합계 (3개 PR + 본 PR)

| 분류 | 파일 수 | 핵심 |
|---|---|---|
| 페르소나 | 1 | P1 박지훈 · P2 김민서 |
| Epic / NFR | 2 | E1~E4 + Won't / 33개 NFR 키 |
| 사용자 스토리 | 3 | 14 스토리, 70 SP, MoSCoW + INVEST+M축 |
| Unit 분해 | 6 | U0 Foundation + U1~U4 + overview |
| 인계 노트 | 1 | handoff.md (위험 7 + 가정 8 + 결정 10 + 진입 순서) |
| 계획서 | 5 | user_stories / mobile_review / id_linking / units / git_flow ×4 |
| 출처 로그 | 1 | prompts.md (Prompt 1~23, 모든 결정 출처) |

## Test plan

문서 PR이라 자동 테스트 없음. 리뷰 항목:

- [ ] handoff.md 헤더에 "Inception 단계 종료" 마커가 명시되어 있는가
- [ ] §2 위험 R1~R7 모두 닫는 unit이 명시되어 있는가
- [ ] §4 결정 D1~D10 모두 진입 unit이 명시되어 있는가 (U0에 7개 집중 확인)
- [ ] §5 권장 입력 순서가 units-overview.md §3 빌드 순서와 정합한지
- [ ] prompts.md Prompt 1~23 시간순·번호 정합

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

> ❓ **확인 필요 (4.A)**: PR 본문에 추가/삭제할 부분이 있는가?

---

## 5. 실행 단계

- [ ] **5.1** 새 브랜치 분기 — `git checkout -b feature/aidlc-inception-closure` (분기 기준 develop, 현재 위치)
- [ ] **5.2** §2의 5개 파일을 **명시적 경로**로 `git add` → 단일 커밋 작성
- [ ] **5.3** `origin`에 push (`-u`로 추적 설정)
- [ ] **5.4** `gh pr create` (base: develop, head: 새 브랜치, 본문 §4 초안 사용)
- [ ] **5.5** 본 계획서 §1·§5에 결과 메모 추가 + `prompts.md` Prompt 23에 완료 줄

---

## 6. 안전장치

- `git add <명시 경로>` 만 사용. `git add -A`, `git add .`, `git commit -a` **절대 사용 안 함**.
- `.DS_Store`, `demo/`, `web/`, `.claude/`, `.playwright-mcp/`, 스크린샷은 *건드리지 않음*.
- `--no-verify`, `--no-gpg-sign`, `--amend` 등 **사용 안 함**.
- push는 새 feature 브랜치로만. develop/main 직접 푸시 **안 함**.
- 사전 hook 실패 시 amend 대신 새 커밋.
- 이미 머지된 PR #9·#10·#11의 커밋(`7575fc3`, `0ba0a22`, `d1b45d7`)을 **수정·cherry-pick 안 함**.

---

## 부록 A — 결정 표 (승인 대기)

| ID | 항목 | 최종 결정 |
|---|---|---|
| 1.A | 브랜치 이름 | ✅ `feature/aidlc-inception-closure` (Prompt 24) |
| 2.A | 제외 목록 정합 | ✅ §2의 제외 6종 그대로 (Prompt 24) |
| 3.A | 커밋 메시지 형식 | ✅ §3 초안 그대로 (Prompt 24) |
| 4.A | PR 본문 형식 | ✅ §4 초안 그대로 (Prompt 24) |

---

## 사용자에게 요청

부록 A의 4개 항목에 대해

1. **권장안 전부 채택** → 5.1부터 즉시 실행
2. **일부 수정**
3. **별도 안 제시**

중 하나로 답해 주세요. 승인 전까지 git 명령은 실행하지 않습니다.
