# 작업 계획서 — Inception 후속 산출물 git-flow PR (두 번째)

- **단계**: 보조 (Inception › User Stories 단계의 *모바일 검토 반영 + F1 정리* 변경을 develop으로 PR)
- **출처**: [`prompts.md` § Prompt 14](../prompts.md#prompt-14)
- **선행 PR**: [PR #9](https://github.com/80-hours-a-week/DocSuri/pull/9) — 2026-06-10 03:02 UTC 머지 완료. 본 PR은 그 이후 변경분만 다룬다.
- **참조 메모리**: `project_git_flow_setup` (feature PR → develop), `user_commit_message_style` (영문 conventional prefix + 한국어 본문 + AGENTS.md §n.m 인용), `feedback_commit_review_gate` (멀티 커밋 배치 시 사전 계획), `feedback_demo_scope_audits` (Sprint 1 단계 — 데모 부트 기준)
- **현재 상태**: `feature/aidlc-inception-user-stories` 브랜치에 있음. `develop` 보다 1 ahead(7575fc3, PR #9의 base). 본 PR과 무관한 변경(`demo/`, `web/`, `.DS_Store`, 스크린샷, `.claude/`, `.playwright-mcp/`) 다수 존재 — **본 PR에 포함하지 않음**.

---

## 1. 브랜치 전략 (Prompt 15 결정 반영)

- **결정**: 현재 브랜치 `feature/aidlc-inception-user-stories`를 **그대로 재사용**.
- **근거**: PR #9는 *merge commit* 방식(`487662b`)으로 머지되어 7575fc3가 develop에 그대로 살아 있음. 동일 SHA 중복·squash 회피 문제 없음.
- **새 브랜치·develop 머지·rebase 모두 불필요**. 후속 커밋을 그대로 쌓아 push 시 GitHub이 base(`develop @ 487662b`) ↔ head(새 커밋) 사이 diff만 자동 계산 → PR diff에 본 사이클 변경만 노출.

> 1.A는 옵션 D(현재 브랜치 재사용)로 확정. A·B·C 후보는 폐기.

---

## 2. 커밋 범위 (Scope discipline)

**포함 (단일 커밋, 11 파일)**

| 파일 | 상태 | 변경 핵심 |
|---|---|---|
| `aidlc-docs/plans/git_flow_pr2_plan.md` | **신규** | 본 계획서 자체 (선행 PR 패턴과 정합) |
| `aidlc-docs/plans/mobile_review_plan.md` | **신규** | A1~A8 8단계 일괄 반영 계획서 (결정 표 + 실행 단계 + 후속) |
| `aidlc-docs/plans/git_flow_pr_plan.md` | M (이미 staged) | 5.1~5.5에 결과 메모 추가 (커밋 7575fc3, PR #9 URL) |
| `aidlc-docs/plans/user_stories_plan.md` | M | 7.1·7.2 출처 표기를 Prompt 10·11·12로 정정, 부록 A에 1.A 옵션 C 확정 |
| `aidlc-docs/prompts.md` | M | Prompt 10·11·12·13·14 신규 + Prompt 7·9·12 *사후 주의* 단락 + 앵커 4개 추가 |
| `aidlc-docs/requirements/epics.md` | M | 헤더에 디바이스 정책 한 줄 추가 |
| `aidlc-docs/requirements/nfr.md` | M | NFR-PERF 측정 환경 명시 / NFR-UX-03 디바이스 분기 / NFR-A11Y-03 신설 / **NFR-MOBILE-01~05 신설** / **NFR-NET-01~04 신설** / 페르소나 NFR 매핑 갱신 |
| `aidlc-docs/story-artifacts/personas.md` | M | P1·P2 *모바일 사용 시나리오* 단락 추가, 디바이스 비중 행 추가 |
| `aidlc-docs/story-artifacts/user_stories.md` | M | US-DISC-01 모바일 AC 분기 / US-COMP-02·04·05 인터랙션 동사 일반화 / US-COMP-04 모바일 분기 AC 추가 / US-TRACE-01 모바일 분기 AC 추가 / 신규 NFR 키 인용 |
| `aidlc-docs/story-artifacts/coverage_matrix.md` | M | §1-B 디바이스×페르소나, §1-C 디바이스×Epic, INVEST에 M축 추가, NFR 인용 분포에 신규 키 10건 추가 |
| `aidlc-docs/story-artifacts/handoff.md` | M | 전면 재작성(R1~R7 위험 + D1~D10 결정 + Open Decisions + Assumptions + 변경 정책) + Prompt 12 링크 + 출처 로그 표기 갱신 |

**제외 (이 PR과 무관, 손대지 않음)**

| 파일/경로 | 비고 |
|---|---|
| `.DS_Store` | macOS 메타, 커밋 대상 아님 |
| `demo/app/infra/llm/bedrock.py`, `mock.py` | 데모 인프라 수정, 별도 작업 |
| `demo/scripts/smoke.sh`, `demo/tests/*`, `demo/web/*` | 데모 영역 |
| `web/src/app/api/recommend/route.ts` | 추천 API, 별도 작업 |
| `.claude/`, `.playwright-mcp/` | 로컬 도구 설정·캐시 |
| `after-fix-*.png`, `docsuri-*.png`, `initial-load.png` | 디버그 스크린샷 |

> ❓ **확인 필요 (2.A)**: 위 "제외" 목록 그대로 두는 게 맞는가?

---

## 3. 커밋 메시지 (초안)

```
docs(aidlc): refine Inception artifacts with mobile review and handoff freeze

PR #9 머지 이후 추가된 Inception(User Stories) 단계 보강을 단일 커밋으로 정리.

- 모바일 검토 반영: NFR-MOBILE 5건 + NFR-NET 4건 + NFR-A11Y-03 신설
- US-DISC-01 / US-COMP-02·04·05 / US-TRACE-01에 모바일 분기 AC 추가
- 페르소나 P1·P2에 모바일 사용 시나리오 단락 추가, 디바이스 비중 행 신설
- 커버리지 매트릭스에 디바이스×페르소나·디바이스×Epic + INVEST M축 추가
- prompts.md Prompt 4·5·6 번호 충돌 해소 → 10·11·12로 재할당, Prompt 13·14 추가
- handoff.md 동결: 위험(R1~R7), 가정(A1~A8), 다음 단계 결정(D1~D10) 정리
- mobile_review_plan.md 신설 + 모든 계획서 체크박스 클로즈

AGENTS.md §2 (페르소나) · §3 (Feature Topology) · §7.5 (PR Review 의례)
맥락의 Sprint 2 요구사항 계약 동결본 v2.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

> ❓ **확인 필요 (3.A)**: 메시지 길이/형식 의견 있는가? (영문 conventional prefix `docs(aidlc):` + 한국어 본문 + AGENTS.md 섹션 인용은 사용자 합의된 스타일)

---

## 4. PR 본문 (초안)

```
## Summary

- PR #9(Inception › User Stories 1차 동결) **후속 보강**을 단일 커밋으로 추가
- 모바일 검토 반영: NFR 10건 신설 + 스토리 5건 AC에 모바일 분기 추가
- prompts.md 번호 충돌 해소(F1): 모바일 흐름을 Prompt 10·11·12로 재할당
- handoff.md 동결: 위험·가정·다음 단계 결정을 한 페이지로 정리
- AGENTS.md §2·§3·§7.5 맥락의 Sprint 2 요구사항 계약 **동결본 v2**

## 변경 트리

aidlc-docs/
├── plans/
│   ├── mobile_review_plan.md (신규)
│   ├── git_flow_pr_plan.md (결과 메모)
│   └── user_stories_plan.md (출처 정정)
├── prompts.md (Prompt 10~14 추가, Prompt 7·9·12 사후 주의)
├── requirements/
│   ├── epics.md (디바이스 정책 한 줄)
│   └── nfr.md (NFR-MOBILE×5, NFR-NET×4, NFR-A11Y-03)
└── story-artifacts/
    ├── personas.md (모바일 시나리오 단락)
    ├── user_stories.md (5건 AC 모바일 분기)
    ├── coverage_matrix.md (디바이스 매트릭스 + INVEST M축)
    └── handoff.md (위험·가정·결정 동결)

## 선행 PR

머지 완료: PR #9 (`docs(aidlc): add Inception user-stories artifacts`)

## 다음 단계로 인계되는 미해결 항목

`aidlc-docs/story-artifacts/handoff.md` 참조:
- §2 위험: R1 Mobile UX 미확정 5건, R2 SP 8 스토리 3건, R3 LLM 비용 변동성, R4 인용 API 의존, R5 학술 용어 사전, R6 오프라인 캐시, R7 Won't 항목 재요청
- §4 결정 필요: D1~D10 (백엔드·임베딩·LLM·프론트엔드·디자인 시스템·그래프·캐시·호스팅·관찰가능성)

## Test plan

문서 PR이라 자동 테스트 없음. 리뷰 항목:

- [ ] `prompts.md`의 Prompt 1~14가 시간순·번호 정합인지 (특히 Prompt 10·11·12 = 모바일 흐름)
- [ ] `nfr.md`의 신규 키 10개(NFR-MOBILE/NET/A11Y-03)가 모두 최소 1개 스토리에서 인용되는지 (`coverage_matrix.md §5`)
- [ ] `user_stories.md`의 디바이스 분기 AC(US-DISC-01, US-COMP-04, US-TRACE-01)가 Gherkin 컨텍스트로 명확히 구분되는지
- [ ] `handoff.md`의 위험·결정·가정이 다음 단계 입력으로 충분한지
- [ ] PR #9 본문의 "다음 단계 인계" 항목과 본 PR의 인계 표가 정합한지

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

> ❓ **확인 필요 (4.A)**: PR 본문 내용에 추가/삭제할 부분이 있는가?

---

## 5. 실행 단계

- [x] **5.1** §2의 11개 파일을 **명시적 경로**로 `git add` → 단일 커밋 작성. ✅ → 커밋 `0ba0a22` · 11 파일 · +518 / -125 줄
- [x] **5.2** `origin feature/aidlc-inception-user-stories`로 push (이미 추적 설정됨) ✅ → `7575fc3..0ba0a22`
- [x] **5.3** `gh pr create` (base: develop, head: 동일 feature 브랜치, 본문 §4 초안 사용) ✅ → [PR #10](https://github.com/80-hours-a-week/DocSuri/pull/10)
- [x] **5.4** 본 계획서 §1·§5에 결과 메모 추가 (커밋 SHA, PR URL) + `prompts.md` Prompt 14에 완료 줄 ✅

---

## 6. 안전장치

- `git add aidlc-docs/<명시 경로>` 만 사용. `git add -A`, `git add .`, `git commit -a` **절대 사용 안 함**.
- `.DS_Store`, `demo/`, `web/`, `.claude/`, `.playwright-mcp/`, 스크린샷은 *건드리지 않음* (commit·push·stash 대상에서 제외).
- `--no-verify`, `--no-gpg-sign`, `--amend` 등 **사용 안 함**.
- push는 새 feature 브랜치로만. develop/main에 직접 푸시 **안 함**.
- 사전 hook 실패 시 amend 대신 새 커밋.
- 이미 머지된 PR #9의 commit `7575fc3`을 **수정하거나 cherry-pick하지 않음**.

---

## 부록 A — 결정 표 (승인 대기)

| ID | 항목 | 최종 결정 |
|---|---|---|
| 1.A | 브랜치 이름 | ✅ **현재 브랜치 `feature/aidlc-inception-user-stories` 재사용** (옵션 D, Prompt 15) |
| 2.A | 제외 목록 정합 | ✅ §2의 제외 6종 그대로 (Prompt 16) |
| 3.A | 커밋 메시지 형식 | ✅ §3 초안 그대로 (Prompt 16) |
| 4.A | PR 본문 형식 | ✅ §4 초안 그대로 (Prompt 16) |

---

## 사용자에게 요청

**본 계획서를 검토해 주시기 바랍니다.** 부록 A의 4개 항목에 대해

1. 권장안 전부 채택,
2. 일부 수정(어떤 항목을 어떻게),
3. 별도 안 제시

중 어느 쪽인지 알려 주시면, 승인 후 §5의 5.1부터 한 단계씩 실행하며 체크박스를 닫겠습니다. 승인 전까지 git 명령은 실행하지 않습니다.
