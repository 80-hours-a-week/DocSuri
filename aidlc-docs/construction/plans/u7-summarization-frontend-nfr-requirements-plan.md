# u7-summarization-frontend-nfr-requirements-plan.md — NFR Requirements 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Requirements (유닛별 루프) · **유닛**: U7 Summarization **Frontend** 슬라이스 · **일자**: 2026-06-19
**근거**: FD 산출물 `construction/u7-summarization-frontend/functional-design/`(컴포넌트·BR-SF-1~16·VM, 8문 확정) · 백엔드 계약 `POST /api/summarize`(스트리밍·status union) · SSOT 2026-06-19 개정 · 프론트 자산 `frontend/lib/api/*`(ApiClient·transport seam·classify)·`@/types/generated`·`frontend/CLAUDE.md`.
**목적**: 프론트 U7 슬라이스의 비기능 요구사항 확정 + **기술 바인딩**(스트리밍 소비·SSR 전략·대용량 전문 렌더·전문 반환 API 정합·타입 생성). 본 단계는 **정책 형태**까지 — px/ms 수치·번들 예산 실측은 Build&Test.
**고도(altitude)**: 스택 종류 + NFR 목표(정책 형태). 구체 수치·서킷·재시도 값은 NFR Design/Build&Test.

> **[전역 계승](재결정 아님)**: 프론트 전역 PIN을 U7 슬라이스가 상속 — **Next.js 15.1.6(App Router) · React 19 · SSR · pnpm · vitest + playwright · ApiClient 단일 진입 + 실 transport(`routeHandlerTransport` BFF → U6 게이트웨이) · `@/types/generated` 타입 파이프라인 · 모바일 우선 CSS Module · XSS/안전링크/토큰 비노출(`frontend/CLAUDE.md`)**. 해당 항목엔 `[전역 계승]` 표기.
> **[real-first]**: 백엔드 U7과 동일하게 **프로덕션 mock 대역 없음** — 프론트는 실 BFF transport로 동작. 단위 테스트는 test-only stub Transport만 허용(백엔드 `tests/stubs` 선례). 신규 계약(scope=full·getFullText)은 백엔드 §6 통합 의존.
> **[U6/게이트웨이 위임]**: 인증/인가·레이트리밋·비용 게이트는 U6 게이트웨이 소관 — 프론트는 BFF transport로 소비만(토큰 클라이언트 비노출).
> **⚠️ 신규 백엔드 의존**: `getFullText`/전문 반환 API(Q5=C)와 `scope` 파라미터는 백엔드 신규 계약 — 본 단계에서 **provisional 계약 + transport seam**으로 병렬 설계(§4 Q4).

---

## 1. 유닛 컨텍스트 (NFR 렌즈)

- 프론트 U7 = 단일 논문 **온디맨드 요약/번역/전문뷰어** 클라이언트 표면. 검색 SLA(NFR-P1) **비대상** — **NFR-P2**(캐시 HIT 즉시 / 첫 생성 스트리밍 체감 TTFB).
- **핵심 NFR 동인**:
  - **NFR-P2(체감 성능)** — `cached:true` 즉시 렌더(스피너 생략, BR-SF-5). 첫 생성은 수십 초 가능(Sonnet 풀논문) → **점진 렌더로 체감 관리**. 백엔드가 *근거화 통과분*만 스트리밍(BR-S8)하므로 프론트는 안전 콘텐츠를 점진 표시.
  - **대용량 렌더** — 전문 번역(한국어 ~수만 토큰)·전문뷰어(정규화 전문)는 긴 텍스트 → 렌더 성능·스크롤·앵커 하이라이트(Q5=C).
  - **신뢰성/복원력** — 응답 union 전수 매핑(BR-SF-14)·무한 로딩 금지·재시도(BR-SF-15)·전문 라이선스 게이트(BR-SF-11).
  - **보안** — 외부 텍스트 XSS 이스케이프(BR-SF-9)·날조 0 표시 무가공(BR-SF-10)·토큰/내부값 비노출(BR-SF-16)·안전 링크(BR-SF-13). [대부분 전역 계승]
  - **유지보수성** — VM ↔ 백엔드 DTO 1:1(드리프트 0), generated-types 파이프라인.
- **FD 잠금(답변)**: 화면 하이브리드(Q1)·진입 공용(Q2)·요약 persona/번역 단일(Q3·Q4)·전문뷰어(Q5=C)·번역 버튼(Q6)·StateView 재사용(Q7)·식별자(Q8).

---

## 2. NFR Requirements 실행 계획 (Step 2 — §4 답변 확정 후, 체크박스)

> 산출물은 `construction/u7-summarization-frontend/nfr-requirements/` 에 생성. **§4 답변 전 미생성.**

- [x] **nfr-requirements.md** ✅ 생성(2026-06-19) — 프론트 U7 NFR 확정:
  - 성능(**NFR-P2**: 캐시 HIT 즉시·첫 생성 점진 렌더 TTFB 목표 형태·상세 라우트 로드·대용량 전문 렌더 정책), 신뢰성(union 전수 매핑·무한로딩 금지·재시도·라이선스/소스부재 폴백).
  - 보안(XSS·날조0 무가공·토큰 비노출·안전링크 — 대부분 전역 계승, U7 표면 적용), 접근성(터치 타깃·스크린리더·포커스 이동), 관측(클라이언트 오류/상태 텔레메트리 형태).
  - 유지보수성(VM↔DTO 1:1·generated-types), 테스트(union 매핑 전수·XSS 라운드트립·persona 멱등·식별자 결정성 PBT 형태 — 도구/수치는 NFR Design).
- [x] **tech-stack-decisions.md** ✅ 생성(2026-06-19) — ADR 형식(결정·근거·대안·전환 비용):
  - **[전역 계승]**: Next.js App Router·React·SSR·transport seam(BFF)·generated-types·vitest/playwright·CSS Module.
  - **U7 고유**: 스트리밍 소비 메커니즘(Q1)·SSR 전략(Q2)·대용량 전문 렌더(Q3)·전문 반환 API 정합 전략(Q4)·타입 정합(Q5)·신규 `ApiClient.summarize()/getFullText()` 시임 계약.
- [x] **provisional 계약·정합 경계** ✅ — `scope`·`getFullText`/`FullTextVM`은 백엔드 신규 계약 → transport seam으로 병렬, 백엔드 확정 시 재정합.
- [x] **추적성** ✅ — NFR/스택 → NFR-P2, FR-12~14, QT-5(근거화 표면), SEC(XSS·토큰), US-S1~S5 역추적.

---

## 3. 가정 (잘못이면 §4 또는 지적으로 정정)

- A1: transport는 U5의 routeHandlerTransport(BFF)를 그대로 계승 — U6 게이트웨이 경유, 토큰 서버측 보관. [전역 계승]
- A2: 백엔드 `/api/summarize`는 스트리밍 응답이며, 스트리밍분은 **근거화 통과 후** 노출되는 안전 콘텐츠(BR-S8).
- A3: `getFullText`/전문 반환 API는 아직 미구현 — provisional 계약으로 설계, 백엔드 §6 작업과 병렬.
- A4: 타입은 `@/types/generated` 파이프라인 계승, 신규 DTO도 동일 경로.

---

## 4. 질문 게이트 (Step 3 — 답변 후 §2 수행)

> 각 항목 `[Answer]:` 뒤 A/B/… 또는 X+설명. 권장안은 각 질문 A. 일괄 수용 시 "전부 A".

## Question 1
백엔드가 스트리밍하는 요약/번역(근거화 통과분)을 프론트가 **어떻게 렌더**할까요?

A) **점진 렌더(스트림 소비)** — fetch 스트림/SSE로 받는 대로 표시(첫 생성 체감 TTFB↓). 백엔드가 안전 콘텐츠만 스트리밍하므로 표시 측 추가 검증 불요(BR-SF-10).

B) **완성분 await 후 일괄 렌더** — 스트림을 모아 완료 후 한 번에 표시. 단순하나 첫 생성 수십 초 동안 대기.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ A 점진 렌더(스트림 소비) — 백엔드 안전 콘텐츠 점진 표시. (2026-06-19 확정)

## Question 2
상세 라우트 `/paper/[id]`의 **렌더 전략**은?

A) **SSR 셸 + CSR 액션** — 헤더(제목·저자·초록)는 SSR로 빠르게, 요약/번역/전문뷰어는 사용자 액션 시 CSR 호출(온디맨드라 자연스러움).

B) **전체 CSR** — 라우트 진입 후 전부 클라이언트 렌더.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ A SSR 셸 + CSR 액션. (2026-06-19 확정)

## Question 3
전문 번역(긴 한국어)·전문뷰어(정규화 전문)의 **대용량 텍스트 렌더**는?

A) **점진/가상화 렌더** — 청크/가상 스크롤로 대용량 안정 렌더 + 앵커 위치 하이라이트(Q5=C).

B) **단순 일괄 렌더** — 전체 텍스트를 한 번에 DOM 렌더. 단순하나 초대형 문서서 성능 부담.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ A 점진/가상화 렌더 + 앵커 하이라이트. (2026-06-19 확정)

## Question 4
`getFullText`/전문 반환 API(Q5=C)·`scope`는 **백엔드 신규 계약**입니다. 프론트는 어떻게 진행할까요?

A) **provisional 계약 + transport seam 병렬** — mock/seam 기준으로 설계·테스트, 백엔드 §6 확정 시 1:1 재정합(병렬 진행, 차단 없음).

B) **백엔드 계약 확정까지 블로킹** — 전문뷰어/전문번역은 백엔드 완료 후 착수.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ A(real-first 재해석) — 실 BFF transport 기준, 프로덕션 mock 없음. 기존 엔드포인트(요약·초록번역)는 즉시 실 연동, 신규(scope=full·getFullText)는 백엔드 §6 통합 의존. provisional 타입은 §6 확정 시 재정합. (2026-06-19 확정)

## Question 5
신규 응답 DTO(Summary/Translation/FullText)의 **타입 정합**은?

A) **기존 generated-types 파이프라인 계승** — 백엔드 스키마 → `@/types/generated` 자동 생성, VM이 그것을 소비(드리프트 0). [전역 계승 인접]

B) **수기 타입 정의** — 프론트에서 타입을 손으로 유지.

X) 기타 (please describe after [Answer]: tag below)

[Answer]: ✅ A 기존 generated-types 파이프라인 계승. (2026-06-19 확정)

---

## 5. 진행 메모

- 본 게이트 답변 → §2 산출물(nfr-requirements.md·tech-stack-decisions.md) 생성 → NFR 완료(REVIEW REQUIRED) → 승인 → NFR Design(전송·서킷·성능 수치·테스트 도구).
- Q4=A 전제로 백엔드 §6(전문 반환 API·scope) 작업과 **병렬** 진행 가능(transport seam). 백엔드 계약 확정이 정합 마일스톤.
