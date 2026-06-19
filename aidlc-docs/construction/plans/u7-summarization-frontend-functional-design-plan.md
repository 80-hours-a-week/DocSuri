# u7-summarization-frontend-functional-design-plan.md — Functional Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → Functional Design (유닛별 루프) · **유닛**: U7 Summarization **Frontend** 슬라이스 · **트랙**: 프론트(U5 코드베이스 `frontend/`) ⟶ U7 백엔드 API 소비 · **일자**: 2026-06-19
**근거(SSOT)**: `aidlc-docs/inception/` — `user-stories/stories.md`(에픽 6 US-S1~S5: 구조화 요약·한국어 번역·출처보기/기권·개인화·온디맨드), `requirements/requirements.md`(FR-12~14·NFR-P2·QT-5) · **백엔드 계약(동결)**: `backend/modules/summarization/`(`api/router.py` `POST /api/summarize`, `domain/models.py` 응답 union: `ok`+§3 6필드+anchors / `abstain` / `cost_degraded` / `source_unavailable`) · **프론트 컨벤션**: `frontend/CLAUDE.md`(모바일 우선·발명 금지·XSS/안전링크), `construction/u5-frontend/functional-design/frontend-components.md`(ApiClient 단일 진입 · `screenState` union · StateView)
**원칙**: 이 단계는 **기술 무관(technology-agnostic)** — 컴포넌트 계층·props/state 의미 계약·인터랙션 흐름·폼/상태 규칙·API 통합점만 설계한다. 프레임워크/SSR/transport(mock vs BFF)·타입생성·번들·성능 수치는 **NFR Requirements/Design**에서 확정.
**범위 명확화(플래그)**: U7은 백엔드 API까지만 설계·구현됐고 **요약/번역 클라이언트 화면은 명세된 적이 없다**(U5 FD는 히어로+검색+라이브러리 자리만, 요약/번역 미포함). 본 FD가 그 화면을 **최초 정의**한다 — `frontend/CLAUDE.md` "문서에 없으면 발명 말고 먼저 플래그" 원칙에 따라 §4 게이트로 사용자 결정을 받는다.

**✅ 확정 결정 (2026-06-19, 오너) — 아래는 게이트 통과 완료, §4에 [Answer] 반영. 백엔드 SSOT `inception/requirements/summarization-translation-pipeline.md` 2026-06-19 개정과 정합:**
- **Q1 화면**: 하이브리드 — 카드 `[요약]` → tldr(3줄) 인라인 + `상세히 보기` 링크 → 전용 상세 라우트(`/paper/[id]`)에서 전체 구조화 요약·출처보기·번역.
- **Q3 범위**: 풀세트(US-S1~S5) — **요약에 persona(전문/입문) 유지**, 번역은 **단일**·초록+전문.
- **Q4 persona**: **요약 한정 부활** — 번역은 단일. 전환 UX(세그먼트 토글 등)는 §4 Q4로 **재개(미정)**.
- **Q5 출처보기**: A — 각 §3 항목 옆 인라인 앵커 칩(`target·label·span`), 전문 뷰어 없음.
- **Q6 번역**: 상세 페이지 **명시 버튼 2개** — [초록 번역](`scope=abstract`) · [전문 번역](`scope=full`, 신규). 백엔드 계약에 `scope` 추가.
- **여전히 미정(팀/후속)**: **Q2**(진입 목록) · **Q4**(persona 전환 UX) · **Q7**(상태 렌더) · **Q8**(식별자 매핑).

> ⚠️ **계약 대조로 드러난 프론트↔백엔드 갭 (본 계획 §4에서 결정)**
> 1. **진입 표면 부재**: 논문은 `ResultCard`(검색·라이브러리 공용)에 살지만 **논문 상세 라우트가 없다**. §3 구조화 요약(6필드+앵커)을 펼칠 면을 신설해야 함 → **Q1**.
> 2. **출처 보기 갭**: US-S3는 "원문 섹션/표/그림 하이라이트"를 말하나 **프론트에 전문 뷰어가 없고**, 백엔드 앵커는 `{field, target, span, label}`만 제공(전문 텍스트 미반환) → **Q5**.
> 3. **요청 식별자 갭**: `/api/summarize`는 `paperId`+`version`(+`abstract?`)를 받지만, `ResultCardVM`은 `arxivId`·`abstractSnippet`(스니펫)만 노출 → **Q8**.

---

## 1. 유닛 컨텍스트 (Step 1 — Analyze Unit Context)

- **책임**: U1~U6 검색/라이브러리 위에 얹힌 **잎(leaf) 프론트 슬라이스**. 사용자가 선택한 단일 논문에 대해 **온디맨드 요약/번역을 요청·렌더**하는 클라이언트 표면. 백엔드 U7(`POST /api/summarize`)을 ApiClient 시임으로 소비하며, 새 단계를 만들지 않는다(하류 의존 없음).
- **스토리(Owner=U7, 클라이언트 표면 본 FD 담당)**: **US-S1**(AI 구조화 요약 렌더) · **US-S2**(한국어 번역 렌더) · **US-S3**(출처 보기 앵커 + 근거부족 기권 메시지) · **US-S4**(개인화: 수준 전문가/입문자 전환·뷰 선호) · **US-S5**(온디맨드: 캐시 즉시 vs 첫 생성 로딩).
- **소비 계약(백엔드 U7, 동결)**:
  - 요청 `POST /api/summarize` ← `{ task: "summary"|"translate", paperId, version, scope?: "abstract"|"full", persona?: "expert"|"beginner", targetLang?: "ko", abstract? }` *(2026-06-19: 번역 `scope` 추가(기본 abstract); persona는 **요약 전용**(전문/입문), 번역은 단일)*
  - 응답 union(`to_dict`, SEC-9 화이트리스트):
    - `{ status:"ok", task, meta, cached, summary:{ tldr, contributions[], method, results, limitations, reproducibility, anchors:[{field,target:"section"|"table"|"figure",span,label}] } }`
    - 또는 `{ status:"ok", ..., translation:{ koreanText, keptTerms[] } }`
    - `{ status:"abstain", reason }` · `{ status:"cost_degraded", message }` · `{ status:"source_unavailable", reason }`
- **재사용 프론트 자산**: `ResultCard`(action 슬롯 보유) · `StateView`/`StateView.module.css`(비-해피 상태) · `lib/api/*`(ApiClient 단일 진입 + transport 시임 + 검증) · `screenState` union 패턴(idle|loading|page|empty|abstain|degraded|invalid|error) · 모바일 우선 CSS Module.
- **신규 정의 대상(본 FD)**: 진입 액션(요약/번역 트리거) · §3 구조화 요약 렌더 컴포넌트 · 앵커("출처 보기") 표시 · persona 전환 UX · 번역 뷰 · 응답 union → screenState 매핑 · 신규 `ApiClient.summarize()` 메서드 계약. (실제 배치·범위는 §4 결정에 종속.)
- **경계(범위 밖)**: transport 구현(mock/BFF), SSR 전략, 타입생성, 성능 예산 = NFR. 백엔드 마운트(app-shell `wiring.py`)·IAM = 인프라 last-mile(별도). 전문 하이라이트 뷰어 신설 여부 = Q5.
- **핵심 트레이스**: FR-12, FR-13, FR-14, NFR-P2, QT-5(근거화 표면), US-S1..S5. 보안: XSS(논문 텍스트 렌더), 안전 링크(arXiv), 토큰 비노출(`frontend/CLAUDE.md` Part 2-B).

---

## 2. Functional Design 실행 계획 (Step 2 — §4 답변 확정 후 수행, 체크박스)

> 산출물은 `aidlc-docs/construction/u7-summarization-frontend/functional-design/` 에 생성한다. **§4 답변 확정 전에는 생성하지 않는다.**

- [ ] **frontend-components.md** — 컴포넌트 계층·props/state·인터랙션·폼/상태 규칙·API 통합점(U5 FD 형식 미러):
  - 컴포넌트 트리(진입 액션 → 요약 표면 → §3 섹션 렌더 → 앵커 → 상태 뷰), 각 컴포넌트 props/state 의미 계약.
  - 인터랙션 흐름: 요약 요청 → 로딩/캐시즉시 → 렌더 / 번역 전환 / persona 전환 / 출처 보기 / 기권·비용저하·소스부재 상태.
  - 응답 union → `screenState` 매핑 표(ok·abstain·cost_degraded·source_unavailable·loading·error).
  - API 통합점: `ApiClient.summarize(SummarizeRequest) → SummarizeResponse` union(기존 `search()` union 패턴 미러).
  - 보안 표면: 외부 텍스트 React 이스케이프(XSS)·앵커 span 안전 렌더·토큰 비노출.
- [ ] **business-rules.md** — 클라이언트 결정·검증 규칙:
  - 요청 구성 규칙(task/persona/targetLang 기본값·식별자 매핑 = Q8) · 중복요청 디듀프 · 캐시(`cached:true`) 표기.
  - 상태 우선순위(기권/소스부재 > 부분 렌더; 날조 금지 표면) · 빈/에러/오프라인 UX(무한 로딩 금지) · 재시도 경로.
  - persona 전환 규칙(논문당 ≤2벌, 전환=재요청·캐시히트 즉시 = Q4) · 번역 뷰 전환 규칙(Q6) · 앵커 표시 규칙(Q5).
- [ ] **domain-entities.md** (경량) — 클라이언트 뷰모델: `SummarizeRequest`/`SummarizeResponse`(union) VM, `SummaryVM`(§3 6필드+anchors), `TranslationVM`, `AnchorVM`, `screenState` enum. 백엔드 DTO와 1:1 정합(드리프트 0) 명시.
- [ ] **상호작용/접근성 노트** — 모바일 터치 타깃·키보드/스크린리더·로딩/빈/실패 상태 동반 설계(`frontend/CLAUDE.md` Part 2-C).

---

## 3. PBT/테스트 가능 속성 식별 (형태만; 수치·도구는 NFR/Build&Test)

- [ ] 응답 union → screenState 매핑 전수성(4 status × 로딩/에러 누락 0).
- [ ] 외부 텍스트 렌더 XSS 무해성(이스케이프 라운드트립).
- [ ] persona 전환 멱등(같은 persona 재요청 → 같은 표면; 캐시 표기 일관).
- [ ] 식별자 매핑 결정성(카드 → SummarizeRequest 동일 입력 → 동일 요청).

---

## 4. 질문 게이트 (Step 3 — 답변 후 §2 수행)

> 각 항목 `[Answer]:` 뒤에 **A/B/C…** 중 하나(또는 `X` + 설명). 권장안은 각 질문의 A. 일괄 수용 시 "전부 A"로 답해도 됩니다.

## Question 1
§3 구조화 요약(6필드+앵커)을 **어디에 렌더**하고, 요약/번역 **진입점**을 어디에 둘까요? (라우팅·컴포넌트 구조를 좌우하는 핵심 결정)

A) **전용 상세 라우트 `/paper/[id]`** — 검색·라이브러리 카드의 [요약] 버튼 → 상세 페이지로 이동, 거기서 persona/번역 선택 + §3 요약 렌더. 기존 search/library의 route+screen 패턴과 일치, 긴 구조화 출력에 공간 넉넉.

B) **카드 인라인 펼침** — 카드 action 슬롯의 [요약] → 같은 화면에서 카드 아래로 요약 패널 확장(아코디언). 이동 없음, 맥락 유지. 단 긴 §3가 리스트를 길게 만듦.

C) **드로어/모달 오버레이** — [요약] → 현재 화면 위로 바텀시트(드로어) 오버레이. 닫으면 리스트 복귀. 단 모달 내 스크롤·접근성 부담.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ 하이브리드(B+A) — 카드 [요약]→tldr 3줄 인라인 + [상세히 보기]→ A안 전용 상세 라우트(`/paper/[id]`)에서 전체 구조화 요약·출처보기·번역. (2026-06-19 확정)

## Question 2
요약/번역 **진입 액션을 어느 목록에** 노출할까요?

A) **검색 결과 + 라이브러리(저장한 논문) 둘 다** — 두 곳 모두 같은 논문 카드이므로 공통 액션으로 노출. 일관된 경험.

B) **검색 결과 카드만** — 스토리 문구("결과 카드")에 가장 충실. 라이브러리는 후속.

C) **라이브러리만** — 저장해둔 논문을 차분히 요약/번역하는 시나리오 우선.

X) 기타 (please describe after [Answer]: tag below)

[Answer]:

## Question 3
이번 증분의 **범위**를 어디까지 할까요?

A) **풀세트(US-S1~S5)** — 구조화 요약 + 한국어 번역 + persona(전문가/입문자) + 출처 보기 앵커 + 캐시 즉시/로딩 상태까지 한 번에. 스토리 에픽 전체를 일관된 유닛으로.

B) **요약 우선(US-S1·S5 + 상태)** — 구조화 요약 + 로딩/캐시/기권/비용저하/소스부재 상태만 먼저. 번역(S2)·출처앵커(S3)는 후속 패스.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ A 풀세트(US-S1~S5) — 요약에 persona(전문/입문) 유지, 번역은 단일·초록+전문. (2026-06-19 확정)

## Question 4 — 🔄 재개 (2026-06-19): persona = 요약 전용
요약에 persona(전문가용/입문자용, 논문당 ≤2벌)를 도입한다(번역은 단일). **전환 UX**를 어떻게 할까요?

A) **표면 상단 세그먼트 토글** — [전문가용 | 입문자용] 토글, 전환 시 해당 persona로 재요청. 이미 만든 벌은 캐시 히트로 즉시 표시(재생성·추가비용 0, US-S5).

B) **생성 전 1회 선택** — 요약 시작 전에 수준을 고르고, 이후 같은 화면에선 전환 없음(다시 고르려면 재진입).

X) 기타 (please describe after [Answer]: tag below)

[Answer]:

## Question 5
US-S3 "출처 보기"는 *원문 섹션/표/그림 하이라이트*를 말하지만, **프론트에 전문 뷰어가 없고** 백엔드 앵커는 `{field, target(section|table|figure), span, label}`(전문 텍스트 미반환)만 줍니다. v1에서 어떻게 표시할까요?

A) **앵커 인라인 표시(전문 뷰어 없음)** — 각 §3 항목에 "근거: §Results · 표2 · '…span…'"처럼 target·label·span을 인라인 칩/각주로 노출. 가용 데이터에 정직, v1로 충분.

B) **arXiv 원문으로 링크아웃** — "출처 보기" → arXiv 원문 새 탭(안전 링크). 정확한 위치 하이라이트는 불가.

C) **전문 하이라이트 뷰어 신설** — S3 전문을 가져와 앵커 위치를 하이라이트하는 뷰어를 새로 구현. 충실하지만 범위·비용 큼(백엔드 전문 반환 계약 추가 필요).

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ A 앵커 인라인(전문 뷰어 없음) — 각 §3 항목 옆 target·label·span 칩. (2026-06-19 확정)

## Question 6
US-S2 한국어 번역(응답 `translation:{koreanText, keptTerms[]}`, 범위 = **초록 + 전문 둘 다**)을 **어떤 면**에서 보여줄까요?

A) **같은 표면에서 [한국어로] 전환** — 요약 표면 상단에 [요약 | 한국어로] 전환.

B) **별도 화면/섹션** — 번역을 요약과 분리된 화면/섹션으로.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ 상세 페이지 명시 버튼 2개 — [초록 번역](scope=abstract)·[전문 번역](scope=full). 요약과 같은 상세 페이지, 각 번역은 별개 task 요청·캐시. koreanText + keptTerms(미번역 보존 용어) 배지 표시. (2026-06-19 확정, 번역 범위 초록+전문으로 확장)

## Question 7
비-해피 응답(`abstain`/`cost_degraded`/`source_unavailable`) + 로딩/에러를 **어떻게 렌더**할까요?

A) **기존 StateView 패턴 재사용** — U5의 `screenState` union + `StateView`를 그대로 써서 요약 전용 메시지 매핑(기권="근거가 부족해 요약을 보류했어요", 비용저하="AI 요약이 일시 중단됐어요", 소스부재="원문을 가져올 수 없어요", 로딩/에러/캐시즉시). 일관성·재사용.

B) **요약 전용 인라인 메시지** — StateView 대신 표면 내부에 맞춤 메시지 블록.

X) 기타 (please describe after [Answer]: tag below)

[Answer]:

## Question 8
`/api/summarize` 요청 식별자 갭: 요청은 `paperId`+`version`(+`abstract?`)를 받지만 `ResultCardVM`은 `arxivId`·`abstractSnippet`만 노출합니다. **요청을 어떻게 구성**할까요?

A) **`paperId = arxivId`, `version = 1`, 추가 본문 없음** — 백엔드가 `paperId`로 전문을 참조(S3 `stored_full_text_ref`)하므로 카드의 arxivId만으로 요청. 가장 단순, v1 적합. *(번역은 초록 대상이라 필요 시 abstract 전달 여부도 이 안에서 확정.)*

B) **카드 VM/백엔드 계약 확장** — 내부 `paperId`·`version`·전체 `abstract`를 카드 VM(또는 검색 응답)에 실어 정확히 전달. 정합성↑, 백엔드/검색 계약 변경 필요.

C) **블로킹 플래그** — 식별자·버전 의미가 불명확하니 백엔드(U7) 계약을 먼저 확인 후 결정.

X) 기타 (please describe after [Answer]: tag below)

[Answer]:

---

## 5. 진행 메모

- 본 게이트 답변 → §2 산출물 생성 → FD 완료 메시지(REVIEW REQUIRED) → 승인 → NFR Requirements(transport·SSR·타입생성·성능 예산).
- 백엔드 app-shell 마운트·IAM은 본 FD 범위 밖(인프라 last-mile). 프론트는 transport 시임(mock/BFF)으로 백엔드 마운트와 **독립적으로** 설계·테스트 가능(구체 결정은 NFR).
