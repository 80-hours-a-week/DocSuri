# 작업 계획서 — Inception 산출물 git-flow PR

- **단계**: 보조 (Inception 산출물을 develop 브랜치로 PR)
- **출처**: [`prompts.md` § Prompt 8](../prompts.md#prompt-8)
- **참조 메모리**: project_git_flow_setup (feature PR → develop), user_commit_message_style (영문 conventional prefix + 한국어 본문 + AGENTS.md §n.m 인용), feedback_commit_review_gate (멀티 커밋 배치 시 사전 계획)
- **현재 상태**: develop 브랜치, origin/develop과 동기. 작업 디렉터리에 본 PR과 무관한 수정·신규 파일 다수 (demo/, web/, .DS_Store, 스크린샷, .claude/) — **본 PR에 포함하지 않음**.

---

## 1. 브랜치 전략

- 분기 기준: `develop`
- 브랜치 이름: **`feature/aidlc-inception-user-stories`**
  - 기존 관례(`feature/recommandation`, `feature/analysis`, `feature/ingest`)와 정합.
  - "aidlc"는 새 메서드 패밀리, "inception-user-stories"는 단계 + 산출물 범위.

> ❓ **확인 필요 (1.A)**: 브랜치 이름을 위와 같이 가도 되는가?
> - 권장: `feature/aidlc-inception-user-stories`
> - 짧게: `feature/aidlc-inception`
> - 별도 안: 사용자 제안

---

## 2. 커밋 범위 (Scope discipline)

**포함 (단일 커밋)**

```
aidlc-docs/plans/user_stories_plan.md
aidlc-docs/plans/id_linking_plan.md
aidlc-docs/plans/git_flow_pr_plan.md  ← 본 파일
aidlc-docs/prompts.md
aidlc-docs/requirements/epics.md
aidlc-docs/requirements/nfr.md
aidlc-docs/story-artifacts/personas.md
aidlc-docs/story-artifacts/user_stories.md
aidlc-docs/story-artifacts/story_index.md
aidlc-docs/story-artifacts/coverage_matrix.md
aidlc-docs/story-artifacts/handoff.md
```

**제외 (이 PR과 무관, 손대지 않음)**

| 파일/경로 | 비고 |
|---|---|
| `.DS_Store` | macOS 메타, 커밋 대상 아님 |
| `demo/app/infra/llm/bedrock.py`, `mock.py` | 데모 인프라 수정, 별도 작업 |
| `demo/scripts/smoke.sh`, `demo/tests/*`, `demo/web/*` | 데모 영역 |
| `web/src/app/api/recommend/route.ts` | 추천 API, 별도 작업 |
| `.claude/`, `.playwright-mcp/` | 로컬 도구 설정·캐시 |
| `after-fix-*.png`, `docsuri-*.png`, `initial-load.png` | 디버그 스크린샷 |

> ❓ **확인 필요 (2.A)**: 위 "제외" 목록을 그대로 두는 것이 맞는가?

---

## 3. 커밋 메시지 (초안)

```
docs(aidlc): add Inception user-stories artifacts

AI-DLC Inception (User Stories) 단계 산출물을 일괄 추가.

- 페르소나: P1 박지훈(전문), P2 김민서(학부 입문) — AGENTS.md §2 페르소나 풀에서 MVP 2종 선별
- Epic: E1 Discover · E2 Comprehend · E3 Differentiate · E4 Trace(1-hop)
- 사용자 스토리 14건 (Connextra + Gherkin AC, MoSCoW, 피보나치 SP)
- NFR: 성능·UX·언어·데이터·보안·비용·접근성·관찰가능성을 별도 파일로 분리
- 커버리지 매트릭스 + 스토리 색인 + Architecture 인계 노트
- 모든 ID 64개에 명시 앵커 + 상호 참조 링크 적용
- 결정 출처를 prompts.md 단일 로그(Prompt 1~8)로 보존

AGENTS.md §2 (페르소나) · §3 (Feature Topology) · §7.5 (PR Review 의례) 맥락의
Sprint 2 요구사항 계약 1차 동결본.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

> ❓ **확인 필요 (3.A)**: 메시지 길이/형식 의견 있는가? (영문 conventional prefix `docs(aidlc):` + 한국어 본문 + AGENTS.md 섹션 인용은 사용자 합의된 스타일)

---

## 4. PR 본문 (초안)

```
## Summary

- AI-DLC Inception (User Stories) 단계 산출물 일괄 추가 — `aidlc-docs/` 트리 신설
- 페르소나 2종(P1 박지훈, P2 김민서), Epic 4종(E1~E4), 사용자 스토리 14건, NFR 22건
- 모든 ID 64개에 명시 HTML 앵커 + 상호 참조 링크 적용
- 결정 출처는 `aidlc-docs/prompts.md` 단일 로그(Prompt 1~8)로 보존
- AGENTS.md §2·§3·§7.5 맥락의 Sprint 2 요구사항 계약 1차 동결본

## 변경 트리

aidlc-docs/
├── plans/ (user_stories_plan, id_linking_plan, git_flow_pr_plan)
├── prompts.md
├── requirements/ (epics, nfr)
└── story-artifacts/ (personas, user_stories, story_index, coverage_matrix, handoff)

## 다음 단계로 인계되는 미해결 항목

`aidlc-docs/story-artifacts/handoff.md §4` 참조 — O-1 SP 8 분해, O-2 Could 처분, O-3 세션 상태 모델 매체, O-4 LLM 비용 모니터링 위치, O-5 한국어 가독성 자동 측정.

## Test plan

문서 PR이라 자동 테스트 없음. 리뷰 항목:

- [ ] `prompts.md`에 모든 결정 출처가 보존되었는지
- [ ] `user_stories.md`의 ID·우선순위·SP·NFR 인용이 `story_index.md`·`coverage_matrix.md`와 정합한지
- [ ] `epics.md`의 비포함 Epic 사유가 명확한지 (특히 E7 영속 개인화)
- [ ] `nfr.md`의 NFR 키 22개가 모두 최소 1개 스토리에서 인용되는지 (`coverage_matrix.md §5`)
- [ ] AGENTS.md §2 페르소나 풀과 본 PR의 페르소나 2종이 정렬되는지

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

> ❓ **확인 필요 (4.A)**: PR 본문 내용에 추가/삭제할 부분이 있는가?

---

## 5. 실행 단계

- [ ] **5.1** `feature/aidlc-inception-user-stories` 생성 + 체크아웃 (분기 기준 develop)
- [ ] **5.2** `aidlc-docs/` 트리 전체를 단일 커밋으로 stage + commit
- [ ] **5.3** `origin`에 push (`-u`로 추적 설정)
- [ ] **5.4** `gh pr create`로 PR 생성 (base: develop, head: feature/aidlc-inception-user-stories)
- [ ] **5.5** PR URL을 사용자에게 보고 + `prompts.md` 갱신

---

## 6. 안전장치

- `git add aidlc-docs/` 만 사용. `git add -A`, `git add .`, `git commit -a` **절대 사용 안 함**.
- `--no-verify`, `--no-gpg-sign`, `--amend` 등 **사용 안 함**.
- push는 `origin feature/aidlc-inception-user-stories`로만. develop/main에 직접 푸시 **안 함**.
- 사전 hook 실패 시 amend 대신 새 커밋.

---

## 부록 A — 결정 요약 (승인 완료, 2026-06-10 / Prompt 9)

| ID | 항목 | 최종 결정 |
|---|---|---|
| 1.A | 브랜치 이름 | ✅ `feature/aidlc-inception-user-stories` |
| 2.A | 제외 목록 유지 | ✅ 예 (제외 6종 그대로 두기) |
| 3.A | 커밋 메시지 형식 | ✅ 영문 prefix + 한국어 본문 + AGENTS.md 섹션 인용 |
| 4.A | PR 본문 형식 | ✅ 위 초안 |
