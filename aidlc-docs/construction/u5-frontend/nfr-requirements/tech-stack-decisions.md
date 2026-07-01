# U5 Frontend — Tech Stack Decisions (NFR Requirements)

**단계**: CONSTRUCTION → NFR Requirements · **유닛**: U5 Frontend (Track 3) · **일자**: 2026-06-16
**Deploy unit**: ④ frontend (독립) · **근거**: U5 FD 4종 · components.md §U5 · README §5-D · `shared/dtos/*.schema.json`
**원칙**: prior art(폐기 사이클 Next.js)는 **참조만**, 기본 계승 아님(aidlc-state.md 비고). 신규 선택. 전역 결정(Python·OpenSearch·Cohere)은 백엔드 전용 — U5는 `shared/dtos` 계약만 소비하므로 직접 영향 없음.

> 표기: `TD-U5-n`. 잠정/후속 의존은 ⏳로 표시.

---

## TD-U5-1. SSR 프레임워크 — **Next.js (React, App Router)**
- **결정**: Next.js + React, App Router 기반 SSR.
- **근거**: components.md §U5 "SSR 폰 우선"(DQ2). SSR/스트리밍·코드 스플릿·라우트 가드·생태계 성숙. 팀 prior art 친숙(학습비용↓) — 단, 계승이 아닌 신규 채택.
- **반려**: Remix(웹표준 폼 강점이나 생태계·RSC 성숙도 열세), SvelteKit(번들 경량 이점 있으나 팀 친숙도·생태계 trade-off).
- **추적**: NFR-U1, NFR-U2, FR-11.

## TD-U5-2. 언어 + DTO 타입 생성 — **TypeScript + JSON Schema→TS 코드 생성**
- **결정**: TypeScript. `shared/dtos/*.schema.json`에서 TS 타입을 **빌드/CI 단계로 자동 생성**(예: json-schema-to-typescript). 수기 타입 금지.
- **근거**: README §5-D — Python 바인딩과 **동일 JSON Schema 출처** → 양쪽 드리프트 0. 생성물은 커밋/CI 검증.
- **불변식**: 생성 타입은 SSOT 파생물 — 직접 수정 금지(스키마 변경 → 재생성).
- **추적**: dtos.md, SEC-9(노출 필드 한정), BR-U5-19.

## TD-U5-3. 데이터 페칭 / 서버 상태 — **ApiClient(fetch 래퍼) + 화면 로컬 상태, 전역 서버상태 라이브러리 없음**
- **결정**: 별도 서버상태 라이브러리(TanStack Query 등) 미도입. ApiClient를 **transport seam**(MockTransport ↔ HttpTransport)으로 두고, 화면은 로컬 상태로 union을 분기.
- **근거**: FD 결정(전역 스토어 없음) + Part 1(도입 사유 없음). 검색=단일 요청/응답이라 캐시·디듀프 라이브러리 불필요. 디듀프/타임아웃은 ApiClient에서 직접 처리.
- **⏳ 재평가**: 후속 라이브러리/이력 **커서 무한스크롤** 진입 시 서버상태 라이브러리 필요성 재검토.
- **추적**: NFR-P1, BR-U5-17/18.

## TD-U5-4. 스타일링 — **CSS Modules + CSS 변수**
- **결정**: CSS Modules(+CSS custom properties). CSS-in-JS·Tailwind 미채택.
- **근거**: 런타임 비용 0·SSR 안전(하이드레이션 충돌 없음)·폰 우선 단순. 디자인 토큰은 CSS 변수.
- **추적**: NFR-U1, NFR-U2(목업 프레임 폭 고정).

## TD-U5-5. 테스트 — **Vitest + Testing Library / Playwright / DTO 계약 테스트**
- **결정**: 컴포넌트·상태머신=Vitest + React Testing Library. E2E=Playwright(안정적 `data-testid` 기반). + **DTO 계약 테스트**(생성 TS 타입 ↔ mock 픽스처 정합).
- **근거**: 자동화 친화 UI 규칙(data-testid). 계약 테스트로 mock↔실제 드리프트 차단.
- **추적**: BR-U5-22, BR-U5-19, FR-11(상태 분기 커버).

## TD-U5-6. SSR 인증/세션 — **서버측 httpOnly 쿠키 포워딩**
- **결정**: 세션은 secure/httpOnly/sameSite 쿠키(transport). SSR 서버가 게이트웨이 호출 시 쿠키 포워딩. 클라 JS·번들은 토큰 미접근.
- **근거**: SEC-3/12 — 토큰 클라 비노출. `SessionInfo`(userId·expiresAt)만 화면 동기화.
- **추적**: BR-U5-13/14, SEC-3, SEC-12, SEC-8.

## TD-U5-7. 패키지/빌드/배포 — **pnpm + 독립 패키지, ESLint/Prettier**
- **결정**: pnpm. `frontend/` 독립 배포 ④. lint=ESLint, format=Prettier. 빌드=프레임워크 기본(Next build).
- **⏳ 후속**: 배포 산출물 형태(노드 SSR 서버 vs 정적+엣지)·호스팅 토폴로지는 NFR Design/Infrastructure Design.
- **추적**: unit-of-work.md ④, 유지보수 규칙.

## TD-U5-8. 관측 — **경량 계측, 외부 APM 후속**
- **결정**: 핵심 경로(검색·로그인) 에러율·지연을 경량 계측 훅으로 노출. 외부 APM(Sentry 등) 연동은 Infra/후속.
- **추적**: Part 2-A 관측 규칙, NFR-R1.

## TD-U5-9. 공급망/의존성
- **결정**: 의존성 최소화(Part 1). lockfile 고정(pnpm). 생성 코드(타입)·런타임 의존 분리.
- **⏳ 후속**: SCA/취약점 스캔은 CI/Infra 단계.

---

## 의존성·조율 표시
- **⏳ U6 게이트웨이**: 모든 백엔드 호출의 단일 진입. 미배포 동안 HttpTransport는 비활성 — MockTransport로 개발(BR-U5-19).
- **⏳ Infra**: 호스팅·CDN·배포 파이프라인은 Infrastructure Design.
- **트랙 경계**: `shared/`(단일 소유 @revenantonthemission)·`backend/`(@ELSAPHABA 조율)은 U5 트랙 브랜치에서 편집 금지.
