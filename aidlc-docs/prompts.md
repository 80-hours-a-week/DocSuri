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
**조치**: `feature/aidlc-inception-user-stories` 브랜치 생성 → `aidlc-docs/` 단일 커밋 → `origin` push → develop 대상 PR 생성.
