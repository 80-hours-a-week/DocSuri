# DocSuri AI-DLC 프롬프트 로그

이 파일은 AI-DLC 세션 동안 사용자에게 받은 모든 프롬프트를 시간순(append-only)으로 기록합니다.
각 항목은 `## Prompt N — YYYY-MM-DD` 형식으로 구분합니다.

---

<a id="prompt-1"></a>
## Prompt 1 — 2026-06-10

> We will restart building an application today based on AI-DLC. For every front end and backend component we will create a project folder. All documents will reside in the aidlc-docs folder. Throughout our session I'll ask you to plan your work ahead and create an md file for the plan. You may work only after I approve said plan. These plans will always be stored in aidlc-docs/plans folder. You will create many types of documents in the md format. Requirement, features changes documents will reside in aidlc-docs/requirements folder. User stories must be stored in the aidlc-docs/story-artifacts folder. Architecture and Design documents must be stored in the aidlc-docs/design-artifacts folder. All prompts in order must be stored in the aidlc-docs/prompts.md file. Confirm your understanding of this prompt. Create the necessary folders and files for storage, if they do not exist already. Write in Korean.

**조치**: `aidlc-docs/` 하위에 `plans/`, `requirements/`, `story-artifacts/`, `design-artifacts/` 폴더 생성. `prompts.md` 초기화.

---

<a id="prompt-2"></a>
## Prompt 2 — 2026-06-10

> # Inception
> ## User stories
>
> Your Role: You are an expert product manager and are tasked with creating well defined user stories that becomes the contract for developing the system as mentioned in the Task section below. Plan for the work ahead and write your steps in an md file (user_stories_plan.md) with checkboxes for each step in the plan.
> If any step needs my clarification, add a note in the step to get my confirmation. Do not make critical decisions on your own. Upon completing the plan, ask for my review and approval. After my approval, you can go ahead to execute the same plan one step at a time. Once you finish each step, mark the checkboxes as done in the plan.
>
> Your Task: Build user stories for the high-level requirement as described here.
> - (페르소나 5종 — AI 박사과정 박지훈, 30대 연구원, 40대 화장품업계 퇴직자, 일반 대학원생, 프로젝트 논문 작성 중인 대학원생)
> - 사실/행동/목표/골칫거리/필요 기능 후보(요약·번역·유사도·인용 트리·재현성·트렌드·알림 등) 일체 제시

**조치**: `aidlc-docs/plans/user_stories_plan.md` 작성 후 승인 대기.

---

<a id="prompt-3"></a>
## Prompt 3 — 2026-06-10

> 1.A는 옵션 C로 수정해. 대신 P4에서 언급한 입문자의 기준은 대학 학부생으로 바꿔줘.

**결정 확정**: 부록 A의 권장안 전부 채택, 단 1.A는 옵션 C(박지훈 + 학부 입문자)로 수정. P4의 "40대 퇴직자" 프로파일은 "AI 입문 대학 학부생"으로 재설정.
**조치**: 계획서 부록 A에 결정 표시 → 0~6단계 실행 → 7단계(사용자 리뷰 게이트)에서 정지.

---

<a id="prompt-4"></a>
## Prompt 4 — 2026-06-10

> MVP에서 개인화 기능은 왜 뺀 거야?

**해명**: `epics.md`의 E7 비포함 사유("인증 + 영속 저장 필요")가 *세션 개인화*까지 함께 잘라낸 듯한 표현이었음을 인정. 실제로는 (a) 전문/학부 모드 토글, (b) 주제 컨텍스트 주입, (c) 필터 URL 직렬화 형태로 **세션 한정 개인화는 이미 MVP에 흡수**되어 있다는 점을 설명. Prompt 2에 명시된 "검색 필터 저장"을 위한 옵션 A(현행 유지) / B(US-PERS-01 추가) / C(익명 세션 ID) / D(풀 인증)을 제시.

---

<a id="prompt-5"></a>
## Prompt 5 — 2026-06-10

> 원안대로 개인화 기능은 MVP 이후로 미루자.

**결정 확정**: 옵션 A (현행 유지) 채택. **E7 Personalize는 MVP 비포함**으로 동결. 단, 비포함 사유는 정확히 "영속 개인화(재방문·장기 컨텍스트)는 NFR-SEC-01과 정렬되지 않음, 세션 개인화는 이미 흡수"로 다듬는다.
**조치**: `epics.md`의 E7 사유 정정 → `user_stories_plan.md` 7.1·7.2 단계 닫기 → 8단계 인계 노트 작성.

---

<a id="prompt-6"></a>
## Prompt 6 — 2026-06-10

> 키나 ID가 무엇을 의미하는지 바로 찾을 수 있게 링크를 연결해줘

**조치**: `aidlc-docs/plans/id_linking_plan.md` 작성 → 승인 대기. 승인 후 모든 산출물에 명시 앵커를 심고 참조를 링크로 변환.

---

<a id="prompt-7"></a>
## Prompt 7 — 2026-06-10

> 권장안 전부 채택

**결정 확정**: `id_linking_plan.md` 부록 A 권장안 전부 채택 — 명시 HTML 앵커(2.A) · 소문자+하이픈(3.A) · 셀/문단당 첫 등장만 링크(4.A).
**조치**: 7개 파일에 **64개 정의 앵커** 삽입 + 6개 파일의 참조를 링크로 변환. `personas`(2) + `prompts`(7) + `epics`(7) + `nfr`(22) + `user_stories`(14) + `handoff`(12) = 64. 깨진 링크 없음(작성 시점 정합). 자동 grep 점검은 bash 제한으로 불가, 수기 검증으로 갈음.

> **사후 주의**: 본 청구는 *작성 시점* 정합이며, 후속 Prompt 10·11·12(모바일 검토 반영)로 NFR 키가 22→32로 늘고 `handoff.md` 구조가 재작성되어 일부 청구가 stale. Prompt 13(F1) 결정에 따라 *받아들임*.

---

<a id="prompt-8"></a>
## Prompt 8 — 2026-06-10

> Follow the git flow. Make a new branch in local and make a PR to the develop branch.

**조치**: `aidlc-docs/plans/git_flow_pr_plan.md` 작성 → 승인 대기. 승인 후 `feature/*` 브랜치 생성, `aidlc-docs/` 단일 커밋, push, develop 대상 PR 생성.

---

<a id="prompt-9"></a>
## Prompt 9 — 2026-06-10

> 권장안 전부 채택

**결정 확정**: `git_flow_pr_plan.md` 부록 A 권장안 4개 전부 채택.
**조치**: `feature/aidlc-inception-user-stories` 브랜치 생성 → `aidlc-docs/` 단일 커밋 → `origin` push → develop 대상 PR 생성. 결과: commit `7575fc3` + [PR #9](https://github.com/80-hours-a-week/DocSuri/pull/9).

> **사후 주의**: PR #9는 본 시점까지의 산출물만 포함. 후속 Prompt 10·11·12(모바일 검토 반영)로 발생한 변경(`mobile_review_plan.md` 신설, `nfr.md` 10개 키 추가, 스토리 5건 AC 수정, `handoff.md` 재작성)은 PR #9에 미포함. Prompt 13(F1) 결정에 따라 *받아들임* — 후속 PR이 필요하면 별도 계획서로 처리한다.

---

<a id="prompt-10"></a>
## Prompt 10 — 2026-06-10

> 모바일 환경을 고려해서 산출물을 검토해줘.

**조치**: 7단계 리뷰의 부속 검토. `personas.md`, `epics.md`, `nfr.md`, `user_stories.md`, `coverage_matrix.md` 5개 산출물을 모바일 디바이스 사용 시나리오 관점에서 점검 → 변경 후보 목록 도출(A1~A8) → 변경 계획 수립 여부 사용자 결정 요청.

---

<a id="prompt-11"></a>
## Prompt 11 — 2026-06-10

> 즉시 반영해줘.

**결정 확정**: 옵션 1(즉시 반영 계획서 작성 + 일괄 반영) 채택. 5개 결정 모두 권장값 채택.
- 반응형 브레이크포인트: **360 / 768 / 1280**
- 모바일 4G P95 검색 응답: **< 5초**
- 모바일 결과 카드 우선 메타: **제목 · 연도 · 유사도**
- US-TRACE-01 모바일 거동: **간소화 리스트 + 노드 검색**
- 오프라인 거동: **읽기 전용 캐시 24h**

**조치**: `aidlc-docs/plans/mobile_review_plan.md` 작성 → A1~A8 일괄 반영 → 사용자 승인 게이트(7단계) 재정렬.
**완료**: A1~A8 + 후속 2건 모두 반영. INVEST 표에 Mobile 축(M) 추가. NFR 매핑 표·NFR 인용 분포 갱신. 7단계 검토 요청을 사용자에게 제출.

---

<a id="prompt-12"></a>
## Prompt 12 — 2026-06-10

> 옵션 1로 진행해줘

**결정 확정**: 모바일 반영 결과 7단계 통과 → 스토리·NFR·페르소나 동결 → 8단계(인계 노트) 진행. Mobile ⚠️ 5건은 *디자인 단계*의 open risk로 이월.
**조치**: `aidlc-docs/story-artifacts/handoff.md` 작성 → `user_stories_plan.md` 7·8단계 + `mobile_review_plan.md` 마지막 항목 클로즈 → Inception › User Stories 단계 동결.

> **사후 주의**: 본 단계의 `handoff.md` 작성은 별도 흐름(Prompt 5·6·7)의 `handoff.md`(결정 ID `d-*` 6건 + 정밀화 ID `o-*` 5건 + `sec-change-log` 1건 포함)를 **전면 재작성으로 덮어씀**. Prompt 13(F1) 결정에 따라 *받아들임* — 현재 디스크의 R1~R7/D1~D10 구조가 정본.

---

<a id="prompt-13"></a>
## Prompt 13 — 2026-06-10

> F1로 진행해줘.

**결정 확정**: 본 세션 후반의 모바일 검토 흐름(원래 본 세션에서 Prompt 4·5·6으로 기록)을 **Prompt 10·11·12로 재할당**. `prompts.md` 헤더 번호 충돌 해소가 본 결정의 유일한 대상. 다른 충돌(handoff.md 덮어쓰기, NFR 키 카운트 stale, PR #9와 그 이후 변경 사이 격차)은 *현재 디스크가 정본이라는 전제로 받아들임*.
**조치**:
1. `prompts.md` 시간순 재정렬 + 모바일 흐름 헤더 10·11·12로 변경, `prompt-10/11/12/13` 앵커 신설.
2. Prompt 7·9·12에 *사후 주의* 한 단락 추가하여 stale·격차를 명시적으로 기록.
3. 외부 참조 정정 — `handoff.md`, `user_stories_plan.md`, `mobile_review_plan.md`의 "Prompt 4·5·6"(모바일 흐름) 표기를 "Prompt 10·11·12"로 갱신.
4. 사용자에게 정합성 감사 결과 보고.

---

<a id="prompt-14"></a>
## Prompt 14 — 2026-06-10

> upload to upstream according to the git flow. Make another PR to develop.

**현 상태**: PR #9는 머지 완료(2026-06-10 03:02 UTC). 그 이후 본 세션이 추가한 변경 10건(`aidlc-docs/` 내 modified 9 + untracked 1)이 origin과 동기화되지 않음.
**조치**: `aidlc-docs/plans/git_flow_pr2_plan.md` 작성 → 승인 대기. 승인 후 develop 최신화 → 새 `feature/*` 브랜치 → 단일 커밋 → push → 두 번째 PR 생성.

---

<a id="prompt-15"></a>
## Prompt 15 — 2026-06-10

> 아냐. 지금 브랜치를 그대로 써도 돼.

**결정 확정**: `git_flow_pr2_plan.md` 부록 A의 **1.A를 옵션 D(현재 브랜치 재사용)로 수정**. 근거: PR #9가 *merge commit* 방식으로 머지되어 `7575fc3`가 develop에 그대로 살아 있음 → 동일 SHA 중복·squash 회피 문제 없음. 새 브랜치·develop pull·rebase 모두 불필요.
**조치**: 계획서 §1 브랜치 전략 + §5 실행 단계 갱신(6단계 → 4단계). 부록 A 1.A 닫음. 나머지 2.A·3.A·4.A는 사용자 추가 확인 대기.

---

<a id="prompt-16"></a>
## Prompt 16 — 2026-06-10

> 권장안 채택

**결정 확정**: `git_flow_pr2_plan.md` 부록 A의 잔여 결정 2.A·3.A·4.A 모두 권장안 채택. 즉 제외 6종 그대로, 커밋 메시지 §3 초안 그대로, PR 본문 §4 초안 그대로.
**조치**: §5의 5.1~5.4 순차 실행. 커밋 범위에 본 계획서(`git_flow_pr2_plan.md`) 자체 포함하여 총 11 파일.
