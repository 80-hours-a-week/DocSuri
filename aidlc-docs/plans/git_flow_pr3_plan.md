# 작업 계획서 — Inception 후속 산출물 git-flow PR (세 번째, Units 분해)

- **단계**: 보조 (AI-DLC › Construction › Unit Decomposition 산출물을 develop으로 PR)
- **출처**: [`prompts.md` § Prompt 19](../prompts.md#prompt-19)
- **선행 PR**:
  - [PR #9](https://github.com/80-hours-a-week/DocSuri/pull/9) — Inception 1차 동결 (commit `7575fc3`, merge `487662b`)
  - [PR #10](https://github.com/80-hours-a-week/DocSuri/pull/10) — 모바일 검토 + handoff 동결 (commit `0ba0a22`, merge `734db65`)
- **참조 메모리**: `project_git_flow_setup`, `user_commit_message_style`, `feedback_commit_review_gate`, `feedback_demo_scope_audits`
- **현재 상태**: `feature/aidlc-inception-user-stories` 브랜치. develop보다 2 ahead(`7575fc3`, `0ba0a22` — 둘 다 이미 develop에 머지됨). PR #10 패턴(현재 브랜치 재사용·base 자동 비교) 그대로 적용.

---

## 1. 브랜치 전략

- **결정 (권장)**: 현재 브랜치 `feature/aidlc-inception-user-stories`를 **그대로 재사용**.
- **근거**: PR #9·#10 모두 merge commit 방식으로 머지되어 우리 커밋이 develop에 그대로 살아 있음. 새 커밋을 쌓아 push 시 GitHub이 base(`develop @ 734db65`) ↔ head(새 커밋) 사이 diff를 자동 계산 → PR diff에 이번 사이클 변경만 노출.
- **새 브랜치·develop pull·rebase 모두 불필요**. PR #10 사이클과 동일.

> ❓ **확인 필요 (1.A)**: 현재 브랜치 재사용 — PR #10과 동일 패턴으로 가도 되는가? (권장: 예)

---

## 2. 커밋 범위 (Scope discipline)

**포함 (단일 커밋, 11 파일)**

| 파일 | 상태 | 변경 핵심 |
|---|---|---|
| `aidlc-docs/plans/git_flow_pr3_plan.md` | **신규** | 본 계획서 자체 (선행 PR 패턴과 정합) |
| `aidlc-docs/plans/units_plan.md` | **신규** | Construction › Unit Decomposition 8단계 계획서 (부록 A 7개 결정 + 모든 체크박스 클로즈) |
| `aidlc-docs/plans/git_flow_pr2_plan.md` | M | 5.1~5.4 결과 메모 (커밋 `0ba0a22`, PR #10 URL) |
| `aidlc-docs/prompts.md` | M | Prompt 14 완료 줄 + Prompt 15·16·17·18·19 추가 + 앵커 5개 |
| `aidlc-docs/story-artifacts/handoff.md` | M | R1~R7·A1~A8·D1~D10 정의 앵커 25개 삽입 (id_linking 컨벤션 정합) |
| `aidlc-docs/design-artifacts/units/unit-u0-foundation.md` | **신규** | 공통 인프라 unit — 포트 8개 + D1·D2·D3·D4·D8·D9·D10 결정 위치 |
| `aidlc-docs/design-artifacts/units/unit-u1-discover.md` | **신규** | Discover unit — DISC-01·02·03·04 |
| `aidlc-docs/design-artifacts/units/unit-u2-comprehend.md` | **신규** | Comprehend unit — COMP-01·02·03·04·05 |
| `aidlc-docs/design-artifacts/units/unit-u3-differentiate.md` | **신규** | Differentiate unit — DIFF-01·02·03 |
| `aidlc-docs/design-artifacts/units/unit-u4-trace.md` | **신규** | Trace unit — TRACE-01·02 |
| `aidlc-docs/design-artifacts/units/units-overview.md` | **신규** | Unit 매트릭스 + cross-unit 의존 다이어그램 + 빌드 순서 + 위험·결정 매핑 |

**제외 (이 PR과 무관, 손대지 않음)**

| 파일/경로 | 비고 |
|---|---|
| `.DS_Store` | macOS 메타 |
| `demo/app/infra/llm/bedrock.py`, `mock.py` | 데모 인프라 |
| `demo/scripts/smoke.sh`, `demo/tests/*`, `demo/web/*` | 데모 영역 |
| `web/src/app/api/recommend/route.ts` | 추천 API |
| `.claude/`, `.playwright-mcp/` | 로컬 도구 캐시 |
| `after-fix-*.png`, `docsuri-*.png`, `initial-load.png` | 디버그 스크린샷 |

> ❓ **확인 필요 (2.A)**: 위 "제외" 목록 그대로 두는 게 맞는가? (권장: 예 — PR #9·#10과 동일)

---

## 3. 커밋 메시지 (초안)

```
docs(aidlc): decompose Inception artifacts into 5 build-independent units

PR #10 머지 이후 추가된 Construction(Unit Decomposition) 산출물을 단일 커밋으로 정리.

- design-artifacts/units/ 6개 문서 신설 — U0 Foundation + U1 Discover +
  U2 Comprehend + U3 Differentiate + U4 Trace + units-overview
- 14개 스토리를 4개 도메인 unit에 누락·중복 0으로 매핑
- U0가 모든 도메인 unit의 의존 포트 8개(EmbeddingPort / LlmPort / CachePort /
  SessionPort / Telemetry / Glossary / CitationApi) 정의
- Cross-unit DTO 2개(SearchResult, SummaryResult)로 도메인 unit 간 결합 최소화
- handoff.md R1~R7 · A1~A8 · D1~D10에 정의 앵커 25개 삽입 (id_linking 컨벤션)
- units-overview 의존 다이어그램으로 Acyclic 검증, 추천 빌드 순서 명시
- prompts.md Prompt 14~19 + 앵커 정합 + PR2 결과 메모

AGENTS.md §2 (페르소나) · §3 (Feature Topology) · §7.5 (PR Review 의례)
맥락의 Sprint 2 Construction 단계 1차 산출물.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

> ❓ **확인 필요 (3.A)**: 메시지 길이/형식 의견 있는가? (영문 prefix `docs(aidlc):` + 한국어 본문 + AGENTS.md 인용)

---

## 4. PR 본문 (초안)

```
## Summary

- AI-DLC Construction(Unit Decomposition) 1차 산출물 추가
- 14개 사용자 스토리를 4 도메인 unit(U1 Discover · U2 Comprehend · U3 Differentiate · U4 Trace) + 1 인프라 unit(U0 Foundation)으로 분해
- 각 unit은 *단일 팀이 독립 빌드 가능*하며 cross-unit 의존은 DTO/포트 2종+8종으로 명시
- handoff.md의 R/A/D 25개 항목에 정의 앵커 삽입 → unit 문서에서 링크 정합
- AGENTS.md §2·§3·§7.5 맥락의 Sprint 2 Construction 1차 산출물

## 변경 트리

aidlc-docs/
├── plans/
│   ├── git_flow_pr3_plan.md (신규)
│   ├── units_plan.md (신규)
│   ├── git_flow_pr2_plan.md (PR #10 결과 메모)
│   └── prompts.md (Prompt 15~19)
├── story-artifacts/
│   └── handoff.md (R/A/D 앵커 25개)
└── design-artifacts/units/ (신규 폴더)
    ├── unit-u0-foundation.md
    ├── unit-u1-discover.md
    ├── unit-u2-comprehend.md
    ├── unit-u3-differentiate.md
    ├── unit-u4-trace.md
    └── units-overview.md

## 선행 PR

- 머지 완료: #9 (Inception 1차) · #10 (모바일 검토 + handoff 동결)

## 단위 분해 요약

| Unit | Epic | 스토리 | SP | 핵심 책임 |
|---|---|---|---|---|
| U0 Foundation | — | (인프라) | — | 포트 8개 + D1~D4·D8·D9·D10 결정 |
| U1 Discover | E1 | 4 | 18 | 자연어 검색 + 결과 카드 + 모바일 분기 |
| U2 Comprehend | E2 | 5 | 20 | 요약 모드 분기 + 번역 + 시각자료 |
| U3 Differentiate | E3 | 3 | 21 | novelty + 연구 공백 |
| U4 Trace | E4 | 2 | 11 | 1-hop 그래프(데스크톱) + 리스트(모바일) |

## Test plan

문서 PR이라 자동 테스트 없음. 리뷰 항목:

- [ ] units-overview.md 의존 다이어그램이 Acyclic 인지
- [ ] 14개 스토리가 unit md에 누락·중복 없이 매핑되는지
- [ ] U0 포트 8개의 시그니처가 도메인 unit의 §3 입력 표와 정합한지
- [ ] handoff.md의 R/A/D 25개 앵커가 unit md에서 깨진 링크 없이 참조되는지
- [ ] PR #10 본문의 "다음 단계 인계" 항목과 본 PR이 정합한지

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

> ❓ **확인 필요 (4.A)**: PR 본문 내용에 추가/삭제할 부분이 있는가?

---

## 5. 실행 단계

- [ ] **5.1** §2의 11개 파일을 **명시적 경로**로 `git add` → 단일 커밋 작성. (현재 브랜치 그대로 사용)
- [ ] **5.2** `origin feature/aidlc-inception-user-stories`로 push (이미 추적 설정됨)
- [ ] **5.3** `gh pr create` (base: develop, head: 동일 feature 브랜치, 본문 §4 초안 사용)
- [ ] **5.4** 본 계획서 §1·§5에 결과 메모 추가 (커밋 SHA, PR URL) + `prompts.md` Prompt 19에 완료 줄

---

## 6. 안전장치

- `git add <명시 경로>` 만 사용. `git add -A`, `git add .`, `git commit -a` **절대 사용 안 함**.
- `.DS_Store`, `demo/`, `web/`, `.claude/`, `.playwright-mcp/`, 스크린샷은 *건드리지 않음*.
- `--no-verify`, `--no-gpg-sign`, `--amend` 등 **사용 안 함**.
- push는 같은 feature 브랜치로만. develop/main 직접 푸시 **안 함**.
- 사전 hook 실패 시 amend 대신 새 커밋.
- 이미 머지된 PR #9·#10의 커밋(`7575fc3`, `0ba0a22`)을 **수정·cherry-pick 안 함**.

---

## 부록 A — 결정 표 (승인 대기)

| ID | 항목 | 최종 결정 |
|---|---|---|
| 1.A | 브랜치 | ✅ 현재 브랜치 재사용 (Prompt 20) |
| 2.A | 제외 목록 정합 | ✅ §2의 제외 6종 그대로 (Prompt 20) |
| 3.A | 커밋 메시지 형식 | ✅ §3 초안 그대로 (Prompt 20) |
| 4.A | PR 본문 형식 | ✅ §4 초안 그대로 (Prompt 20) |

---

## 사용자에게 요청

부록 A의 4개 항목에 대해

1. **권장안 전부 채택** → 5.1부터 즉시 실행
2. **일부 수정** — 어느 항목을 어떻게
3. **별도 안 제시**

중 하나로 답해 주세요. 승인 전까지 git 명령은 실행하지 않습니다.
