# U5 Frontend — NFR Requirements Plan

**단계**: CONSTRUCTION → NFR Requirements · **일자**: 2026-06-16
**Owner**: Track 3 (@kyjness) · **Deploy unit**: ④ frontend (독립) · **브랜치**: `feature/u5`
**선행**: U5 Functional Design 완료·승인 (히어로 슬라이스 스코프)
**근거**: `construction/u5-frontend/functional-design/` 4종 · `inception/application-design/components.md` §U5 · `shared/dtos/*.schema.json` · `frontend/README.md`(§5-D 스택 확정 위임)

> 이 단계 목적: U5의 **비기능 요구(성능·가용성·보안·접근성·관측)** 확정 + **기술 스택 선정(§5-D)**. 전역 결정(언어/스토어/임베딩 등 백엔드 전역)은 U5에 직접 영향 없음 — U5는 `shared/dtos` 계약만 소비.
> **시스템 전역 계승**: NFR-C1 $1600/월(시스템 전역, U5는 LLM 직접 호출 없음 — 비용 기여 0), 모든 백엔드 호출은 U6 게이트웨이 단일 진입.

---

## A. NFR 평가 작업 항목 (체크박스)

- [ ] A1. 성능 목표 — 폰 우선(NFR-U1) FCP/LCP·번들 예산·단일 요청/응답(NFR-P1)·SSR 초기 렌더 정책
- [ ] A2. 가용성/복원력 — 전역 에러 바운더리(NFR-R1)·백엔드 장애 시 사용자 피드백+재시도·SSR 서버 다운 시 거동
- [ ] A3. 보안 — SSR 서버측 쿠키 포워딩(토큰 클라 비노출 SEC-3/12)·CSP/frame-ancestors(SEC-4)·클라 번들 시크릿 0·XSS 기본 방어(BR-U5-6)
- [ ] A4. 접근성/사용성 — WCAG 목표 등급·키보드/스크린리더·UI 언어(다국어 cross-lingual 질의 대응)
- [ ] A5. 관측 가능성 — 핵심 경로(검색·로그인) 에러율/지연 측정·클라 에러 리포팅 수준
- [ ] A6. 유지보수 — 모노레포 `frontend/` 독립 배포 ④·패키지 매니저·lint/format·디렉토리 구조
- [ ] A7. 테스트 전략 — 컴포넌트 테스트 러너·E2E(data-testid 기반)·DTO 계약 테스트(mock↔실제 드리프트 방지)
- [ ] A8. **기술 스택 선정(§5-D)** — SSR 프레임워크·TS·타입 생성(JSON Schema→TS)·데이터 페칭/서버상태·스타일링·빌드/배포
- [ ] A9. 산출물 작성: `nfr-requirements.md` · `tech-stack-decisions.md`

---

## B. 결정 필요 질문 ([Answer] 태그에 답변 기입)

### B1. SSR 프레임워크 (§5-D 핵심)
> components.md §U5는 "SSR 폰 우선". 폐기 사이클 prior art = Next.js(기본 계승 ❌, 참조만). 독립 배포 ④.
- Q1. SSR 프레임워크를 무엇으로? **(A) Next.js(React, SSR/RSC 성숙·생태계·prior art 친숙 — 권장)** / (B) Remix(React Router·웹표준 폼·중첩 라우트) / (C) SvelteKit(경량 번들·폰 우선 성능 유리) / (D) 기타
  - [Answer]: **A — Next.js(React, App Router SSR).** prior art는 참조일 뿐 기본 계승 아님; 성숙도·생태계로 신규 선택.

### B2. 언어/타입 생성 (§5-D)
> README: "TS 타입은 `shared/dtos/*.schema.json`에서 생성(§5-D로 위임), Python 바인딩과 동일 JSON Schema 출처 → 드리프트 0".
- Q2. **(A) TypeScript + JSON Schema→TS 코드 생성(예: json-schema-to-typescript)로 DTO 타입 자동 생성, 빌드/CI에 생성 단계 고정 — 권장** / (B) TS + 수기 타입(생성 안 함) / (C) 기타
  - [Answer]: **A.** TS + `shared/dtos/*.schema.json`→TS 생성, 생성 산출물은 빌드/CI 단계로 고정(Python 바인딩과 동일 출처 → 드리프트 0).

### B3. 데이터 페칭 / 서버 상태 (§5-D)
> FD 결정: 전역 스토어 없음, ApiClient가 서버상태 단일 진입(transport seam). 검색=단일 요청/응답.
- Q3. **(A) 별도 서버상태 라이브러리 없이 ApiClient(fetch 래퍼) + 화면 로컬 상태 — 슬라이스 범위에 충분, 권장** / (B) TanStack Query 등 도입(캐시·디듀프·재시도 내장; 라이브러리/이력 무한스크롤에 유리하나 슬라이스엔 과함) / (C) 기타
  - [Answer]: **A.** 서버상태 라이브러리 없이 ApiClient(transport seam) + 화면 로컬 상태. 후속 라이브러리/이력 무한스크롤 진입 시 재평가(Part 1 — 현 슬라이스엔 도입 사유 없음).

### B4. 스타일링 (§5-D)
- Q4. **(A) CSS Modules(+CSS 변수)·런타임 비용 0·폰 우선 단순 — 권장** / (B) Tailwind CSS(유틸리티·빠른 시안) / (C) CSS-in-JS(런타임 비용·SSR 주의) / (D) 기타
  - [Answer]: **A — CSS Modules + CSS 변수.** 런타임 비용 0·SSR 안전·폰 우선 단순.

### B5. 테스트 전략
> 자동화 친화 UI 규칙: 안정적 `data-testid`.
- Q5. **(A) 컴포넌트=Vitest + Testing Library, E2E=Playwright(data-testid), + DTO 스키마 계약 테스트(생성 타입↔mock 정합) — 권장** / (B) 단위 테스트만(E2E 후속) / (C) 기타
  - [Answer]: **A.** Vitest + Testing Library(컴포넌트·상태머신), Playwright(data-testid E2E), DTO 계약 테스트(생성 타입↔mock 픽스처 정합).

### B6. SSR 인증/세션 처리 (보안)
> 세션=secure/httpOnly 쿠키(transport). SSR 서버가 게이트웨이 호출 시 쿠키 전달 필요.
- Q6. **(A) SSR 서버측 요청에 클라 쿠키를 포워딩(httpOnly 유지·토큰은 서버↔게이트웨이 구간만), 클라 JS는 토큰 미접근 — 권장** / (B) 기타 처리 방식?
  - [Answer]: **A.** SSR 서버가 게이트웨이 호출 시 httpOnly 세션 쿠키 포워딩. 토큰은 서버↔게이트웨이 구간에만 존재, 클라 JS·번들 미접근(SEC-3/12).

### B7. 성능 예산 (NFR-U1 폰 우선)
- Q7. 폰 우선 성능 목표를 **(A) 정성 목표(초기 JS 번들 경량·LCP 합리적 수준 유지)로 두고 구체 수치는 코드/측정 단계에서 확정 — 권장** / (B) 지금 정량 SLO(예: LCP<2.5s·초기 JS<NkB) 확정 / (C) 기타
  - [Answer]: **A.** 정성 목표(초기 JS 경량·LCP 합리적 유지·코드 스플릿). 구체 수치 SLO는 측정 단계에서 확정(조기 과최적화 회피).

### B8. 관측 가능성 수준
> Part 2-A: 핵심 경로 에러·지연 측정·노출.
- Q8. 클라 관측을 **(A) 구조화 콘솔/경량 훅으로 핵심 경로(검색·로그인) 에러·지연 계측, 외부 APM(Sentry 등) 연동은 Infra/후속으로 — 권장** / (B) 지금 외부 에러 리포팅(Sentry 등) 도입 / (C) 기타
  - [Answer]: **A.** 경량 계측 훅으로 검색·로그인 경로 에러율·지연 노출. 외부 APM 연동은 Infra/후속(현 슬라이스 도입 사유 없음).

### B9. UI 언어 / 접근성 목표
> cross-lingual: 한국어 질의 지원(TD-3). 사용자/콘텐츠 다수 한국어.
- Q9. **(A) UI 기본 언어=한국어(단일), 결과 콘텐츠는 원문(영문 논문) 그대로 렌더; 접근성 목표=WCAG 2.1 AA 지향 — 권장** / (B) 다국어(i18n 프레임워크) 지금 도입 / (C) 기타
  - [Answer]: **A.** UI=한국어 단일(i18n 프레임워크 미도입), 논문 콘텐츠는 원문 그대로(이스케이프 렌더). 접근성=WCAG 2.1 AA 지향.

### B10. 패키지 매니저 / 배포 형태
> 독립 배포 ④. 구체 호스팅 토폴로지는 Infra Design.
- Q10. **(A) pnpm + `frontend/` 독립 패키지, 배포 산출물 형태(노드 SSR 서버 vs 정적+엣지)는 NFR Design/Infra에서 확정 — 권장** / (B) npm/yarn 지정 / (C) 기타
  - [Answer]: **A.** pnpm + `frontend/` 독립 배포 ④. lint/format=ESLint+Prettier. 배포 산출물 형태(노드 SSR vs 정적+엣지)는 NFR Design/Infra 단계 확정.

### B11. 추가 NFR 우려
- Q11. 위에서 안 다뤄진 NFR(국제화·SEO·오프라인[현 스코프 제외 확인]·레이트리밋 UX 등) 있으면 여기에. (없으면 "없음")
  - [Answer]: 오프라인/PWA = **스코프 제외 확정**(FD 단계 합의). 레이트리밋(429)은 ApiClient UserFacingError 정규화로 사용자 안내(US-A1 레이트리밋은 U6 권위). SEO=인증 기반 앱이라 우선순위 낮음(히어로 랜딩만 공개). 그 외 새 NFR 없음.

---

## C. 게이트 규약
- `[Answer]` 전부 채워지면 → 모호 답변 후속 질문(필요시) → **Step 6 산출물 생성**(`nfr-requirements.md`·`tech-stack-decisions.md`) → 완료 메시지(리뷰 게이트).
- 승인 전 산출물 생성·커밋·push/PR 없음. `shared/`·`backend/` 편집 없음(트랙 소유 경계).
- 승인 시 `audit.md` 로그 + `aidlc-state.md` U5 NFR Requirements 완료 표시. 다음 단계: NFR Design.
