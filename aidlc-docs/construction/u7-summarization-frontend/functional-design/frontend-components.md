# U7 Summarization Frontend — Frontend Components (Functional Design)

**단계**: CONSTRUCTION → Functional Design · **유닛**: U7 Summarization Frontend 슬라이스 · **일자**: 2026-06-19
**스코프**: 단일 논문에 대한 온디맨드 **요약 / 초록 번역 / 전문 번역** 클라이언트 표면 + **출처 보기(전문 하이라이트 뷰어, Q5=C)**. 진입 = 검색·라이브러리 공용 카드(US-S1~S5).
**근거**: 계획서 `construction/plans/u7-summarization-frontend-functional-design-plan.md`(§확정 결정 8문) · 백엔드 계약 `backend/modules/summarization/`(`POST /api/summarize`) · 프론트 자산 `frontend/lib/api/*`(ApiClient·classify union)·`StateView`·`ResultCard` · SSOT `inception/requirements/summarization-translation-pipeline.md`(2026-06-19 개정).
**원칙**: 기술 무관 — props/state는 **의미적 계약**. 프레임워크/SSR/transport(BFF 실 경로 — real-first, mock 없음)·타입생성·성능 수치는 NFR.

---

## 1. 컴포넌트 계층

```
AppShell (기존 U5) ............... SSR 루트·라우팅·세션·전역 바운더리
├─ (검색/라이브러리 표면 — 기존)
│  └─ ResultCard ................ 단일 논문 카드(기존, action 슬롯 보유)
│     ├─ SummaryAction .......... [요약] 버튼 → tldr 인라인 펼침 + [상세히 보기] 링크 (Q1·Q2)
│     └─ SummaryInline .......... tldr(3줄) 경량 뷰 — 같은 요약 1벌의 '뷰 프리셋'(재생성 0)
│
└─ (라우트) PaperDetailScreen ... /paper/[id] — 전용 상세 라우트(신규, Q1=하이브리드)
   ├─ PaperHeader ............... 제목·저자·영문 초록 + [arXiv에서 원문 보기] 링크아웃
   ├─ SummaryActions ........... [요약] · [초록 번역] · [전문 번역] 액션 바 (Q6)
   ├─ PersonaToggle ............ [전문가용 | 입문자용] 세그먼트 — 요약 전용(Q4=A)
   ├─ SummaryView .............. 구조화 6필드 렌더 + 항목별 AnchorChip
   │  └─ AnchorChip ............ 출처 칩(target·label) → 클릭 시 FullTextViewer 하이라이트
   ├─ TranslationView .......... koreanText + keptTerms 배지 (초록·전문 공용)
   ├─ FullTextViewer ........... 전문 텍스트 렌더 + 앵커 위치 하이라이트 (Q5=C, 신규)
   └─ StateView ................ 로딩/기권/비용저하/소스부재/에러 공유 (기존 확장)

ApiClient (공유 레이어, 트리 밖) ── transport seam → U6 게이트웨이
├─ summarize(SummarizeRequest) → SummarizeOutcome  (status 판별 union)
└─ getFullText(FullTextRequest) → FullTextOutcome   (Q5=C, OA 라이선스 게이트)
```

> 신규 컴포넌트는 결정 게이트 근거가 있는 것만: `PaperDetailScreen`·`SummaryActions`·`PersonaToggle`·`SummaryView`/`AnchorChip`·`TranslationView`·`FullTextViewer`·`SummaryInline`. `ResultCard`/`StateView`/`AppShell`/`ApiClient`는 기존 재사용·확장.

---

## 2. 컴포넌트별 계약 (props · state · 상호작용 · API 통합점)

### 2.1 ResultCard 확장 (기존 + action 슬롯)
- **책임**: 기존 7필드 카드. `action` 슬롯에 `SummaryAction`을 주입(검색·라이브러리 공용 — Q2=A).
- **props(추가)**: `action`(기존 슬롯) ← `<SummaryAction paperId version arxivUrl />`.
- **규칙**: 카드 자체는 비싼 호출을 트리거하지 않는다 — 액션 탭 시에만(BR-SF-1). 안전 링크(`safeHref`, BR-U5-7) 유지.
- **근거**: US-S1, Q1·Q2.

### 2.2 SummaryAction (카드 인라인 진입)
- **책임**: 카드의 [요약] 버튼. 탭 → `summarize(task:"summary")` 호출 → 결과의 `tldr`만 `SummaryInline`으로 인라인 펼침. 항상 `상세히 보기` 링크(→ `/paper/[id]`)를 동반.
- **state(로컬)**: `screenState`(idle|loading|page|abstain|degraded|sourceUnavailable|error), `outcome?`.
- **상호작용**: 탭 → 로딩(또는 `cached:true`면 즉시) → tldr 인라인. 전체/번역/출처는 `상세히 보기`로.
- **API 통합점**: `ApiClient.summarize({ task:"summary", paperId, version, persona })`.
- **규칙**: BR-SF-1(탭 트리거), BR-SF-5(캐시 표기), BR-SF-7(상태 우선순위). 근거: US-S1·S5, Q1.

### 2.3 SummaryInline
- **책임**: `tldr`(3줄) 경량 뷰. 같은 §3 출력의 **뷰 프리셋** — 추가 생성/요청 0.
- **props**: `tldr`, `cached`.
- **규칙**: 외부 텍스트 이스케이프(BR-SF-9). 근거: SSOT §9.2(뷰 프리셋).

### 2.4 PaperDetailScreen (`/paper/[id]`, 신규 라우트)
- **책임**: 단일 논문 상세 표면 소유 — 헤더·액션·결과 렌더·상태. 요약/번역/전문뷰어의 컨테이너.
- **props**: 라우트 파라미터 `paperId`(=arxivId, Q8=A), `version`(=1, Q8=A).
- **state**: `activeView`('summary'|'abstractTrans'|'fullTrans'), `persona`('expert'|'beginner'), 각 작업별 `screenState`+`outcome`(독립), `anchorTarget?`(뷰어 하이라이트 대상).
- **상호작용**: 액션 선택 → 해당 작업 요청/렌더. 앵커 클릭 → `FullTextViewer` 열고 위치 하이라이트.
- **API 통합점**: `summarize(...)`(3종), `getFullText(...)`(앵커 클릭 시).
- **규칙**: BR-SF-2(요청 구성)·BR-SF-6(persona 전환)·BR-SF-7·BR-SF-8(앵커→뷰어). 근거: US-S1~S5, Q1·Q3.

### 2.5 PaperHeader
- **책임**: 제목·저자·영문 초록(검색 VM 보유분) + `[arXiv에서 원문 보기]` 링크아웃.
- **props**: `title`, `authors`, `abstract`, `arxivUrl`.
- **규칙**: 안전 링크(`safeHref` http/https + noopener, BR-U5-7). 영문 원문 전문은 **앱 내 표시 안 함** — arXiv로(라이선스·기계연료). 근거: SSOT §1(라이선스).

### 2.6 SummaryActions
- **책임**: [요약] · [초록 번역] · [전문 번역] 3버튼(Q6=명시 버튼). 각 버튼 = 별도 task/scope 요청.
- **props**: `paperId`, `version`, `persona`, `onSelect(view)`.
- **상호작용**: [요약]→`task:"summary"`(+persona) / [초록 번역]→`task:"translate", scope:"abstract"` / [전문 번역]→`task:"translate", scope:"full"`.
- **규칙**: 전문 번역은 시간·비용 큼 → 로딩 인디케이터(하드 게이트 없음, BR-SF-3). 캐시 적중 시 즉시(BR-SF-5).
- **근거**: US-S1·S2, Q6, SSOT §5(액션 3개).

### 2.7 PersonaToggle (요약 전용)
- **책임**: [전문가용 | 입문자용] 세그먼트(Q4=A). 전환 시 해당 persona로 **재요청**, 이미 만든 벌은 `cached:true`로 즉시.
- **props**: `value`('expert'|'beginner')`, `onChange`.
- **규칙**: 번역에는 노출하지 않는다(번역=단일, BR-SF-6). 전환=재생성 0(캐시), 추가비용 0.
- **근거**: US-S4, Q4, SSOT §9.2(persona=요약 한정).

### 2.8 SummaryView + AnchorChip
- **책임**: 구조화 6필드(`tldr`·`contributions[]`·`method`·`results`·`limitations`·`reproducibility`) 렌더. 각 항목 옆 `anchors[]` 기반 `AnchorChip`("출처: §Results · 표2").
- **props(SummaryView)**: `summary: SummaryVM`, `onAnchor(anchor)`.
- **props(AnchorChip)**: `anchor: AnchorVM`(`field`·`target`·`span`·`label`), `onClick`.
- **상호작용**: AnchorChip 클릭 → `PaperDetailScreen.anchorTarget` 설정 → `FullTextViewer` 열림·하이라이트(Q5=C).
- **규칙**: 외부 텍스트(요약·span) React 이스케이프(BR-SF-9). 날조 0 — 백엔드 근거화 통과분만 옴(표시 측 가공 금지, BR-SF-10).
- **근거**: US-S1·S3, §3 스키마.

### 2.9 TranslationView (초록·전문 공용)
- **책임**: `translation.koreanText` 렌더 + `keptTerms[]`(미번역 보존 용어) 배지. 전문 번역은 긴 스크롤 텍스트 블록.
- **props**: `translation: TranslationVM`, `scope`('abstract'|'full'), `cached`.
- **규칙**: 외부 텍스트 이스케이프(BR-SF-9). 번역은 앵커 없음(요약 전용). 근거: US-S2, Q6.

### 2.10 FullTextViewer (Q5=C, 신규)
- **책임**: 논문 **전문 텍스트**(백엔드 신규 반환 API)를 렌더하고 앵커 위치(`target`/`span`)를 하이라이트·스크롤.
- **props**: `paperId`, `version`, `anchorTarget?`.
- **state(로컬)**: `screenState`(loading|page|licenseUnavailable|sourceUnavailable|error), `fullText?`.
- **API 통합점**: `ApiClient.getFullText({ paperId, version })` → `FullTextOutcome`.
- **규칙**: **OA 라이선스 미허용 → 'licenseUnavailable' 상태**(뷰어 대신 arXiv 링크아웃 안내, BR-SF-11). 외부 전문 텍스트 이스케이프(BR-SF-9). 정규화 텍스트(참고문헌·저자 제거)임을 안내(BR-SF-12).
- **근거**: US-S3, Q5=C. ⚠️ **신규 백엔드 의존**(전문 반환 API).

### 2.11 StateView (기존 확장)
- **책임**: 비-해피 상태 공유 표시. U5 `StateViewKind`에 **`degraded`·`sourceUnavailable`·`licenseUnavailable`** 추가.
- **메시지 매핑(요약 전용 카피)**: 아래 §3 표.
- **규칙**: 무한 로딩 금지·스택/내부식별자 비노출(BR-U5-11, SEC-15). 근거: US-S3, FR-11.

### 2.12 ApiClient 확장 (공유 레이어)
- **신규 메서드**:
  - `summarize(req: SummarizeRequest): Promise<SummarizeOutcome>` — `POST /api/summarize`, 응답을 `classifySummarizeResponse`로 분류(status 판별).
  - `getFullText(req: FullTextRequest): Promise<FullTextOutcome>` — Q5=C 신규 엔드포인트(라이선스 게이트).
- **규칙**: 단일 진입·transport seam·검증 기존 패턴 미러(`search()` 형). 토큰 클라이언트 비노출(SEC, `frontend/CLAUDE.md`). 근거: 기존 `lib/api/*`.

---

## 3. 응답 union → screenState 매핑 (전수 · 누락 0)

요약 응답은 **`status` 판별자**가 있어 구조 추정 불요(검색과 다름).

| 백엔드 응답 | 분류(`kind`) | screenState | StateView/렌더 |
|---|---|---|---|
| `{ status:"ok", summary }` | `summary` | `page` | SummaryView(+AnchorChip), `cached` 표기 |
| `{ status:"ok", translation }` | `translation` | `page` | TranslationView |
| `{ status:"abstain", reason }` | `abstain` | `abstain` | "근거가 부족해 요약을 보류했어요" |
| `{ status:"cost_degraded", message }` | `degraded` | `degraded` | "AI 요약이 일시 중단됐어요" |
| `{ status:"source_unavailable", reason }` | `sourceUnavailable` | `sourceUnavailable` | "원문을 가져올 수 없어요" |
| (HTTP 4xx 검증) | `invalid` | `invalid` | "입력을 확인해 주세요" |
| (네트워크/5xx) | `error` | `error` | "문제가 발생했어요 · 재시도" |
| (요청 중) | — | `loading` | "요약/번역 생성 중…" |

전문뷰어(`getFullText`) 매핑: `ok`→page · `license_unavailable`→`licenseUnavailable`(arXiv 안내) · `source_unavailable`→`sourceUnavailable` · 네트워크→`error`.

---

## 4. 상호작용/접근성 노트 (의미만; 수치는 NFR)

- 모바일 터치 타깃(액션 3버튼·persona 토글·AnchorChip)·키보드/스크린리더 라벨.
- 로딩·기권·비용저하·소스부재·라이선스부재 상태를 **각각** 동반 설계(무한 로딩 금지).
- 전문 번역·전문뷰어는 긴 스크롤 — 점진 렌더/스트리밍 동반(구체는 NFR).
- 앵커 클릭 → 뷰어 하이라이트는 포커스 이동·복귀 처리.
