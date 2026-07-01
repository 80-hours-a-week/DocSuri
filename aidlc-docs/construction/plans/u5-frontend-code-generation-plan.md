# U5 Frontend — Code Generation Plan (mock-first)

**단계**: CONSTRUCTION → Code Generation (Part 1 계획) · **일자**: 2026-06-16
**Owner**: Track 3 (@kyjness) · **Deploy unit**: ④ frontend (독립) · **브랜치**: `feature/u5`
**선행**: U5 FD·NFR Requirements·NFR Design 완료·승인
**스택**: Next.js(App Router SSR)·TypeScript·TS 생성타입·ApiClient transport seam·CSS Modules·pnpm·Vitest+Testing Library/Playwright

> **이 계획서가 Code Generation의 단일 진실 원천(SSOT)이다.** Part 2 생성은 이 단계 순서를 정확히 따른다(임의 로직 금지).

## 코드 위치 (Critical Rules)
- **애플리케이션 코드**: `frontend/` (Greenfield 멀티유닛 모노레포 — U5 레인). **절대 `aidlc-docs/`에 두지 않음.**
- **문서 요약**: `aidlc-docs/construction/u5-frontend/code/` (markdown만)
- **편집 금지 경계**: `shared/`(단일 소유)·`backend/`(조율 존). `shared/dtos/*.schema.json`은 **읽어서 타입 생성**만(원본 미편집).

## 스코프 / 스토리 추적
- **US-H1**(주, 히어로: 가입→로그인→검색→근거화 결과) · **US-D7**(주, 빈/실패/저하 상태 UX)
- 기여: **US-D1/D4**(검색·결과 카드 UI) · **US-A1/A2**(계정 UI)
- **계약만(후속 패스)**: US-L1/L2/L3(라이브러리·이력) — ApiClient 메서드 시그니처만, 화면 미구현

## 의존성 / 조율
- **⏳ U6 게이트웨이 미배포** → `MockTransport`(DTO 파생 픽스처)로 개발. real 전환=`HttpTransport`(server-only) 설정 교체.
- DTO 계약: `shared/dtos/search.schema.json`·`accounts.schema.json`·`library.schema.json`(SSOT) → TS 타입 생성.

---

## 생성 단계 (번호순·체크박스)

- [x] **Step 1 — 프로젝트 구조 셋업**: `frontend/` Next.js(App Router) 스캐폴드 — `package.json`(pnpm·scripts), `tsconfig.json`, `next.config.*`, `.eslintrc`·`.prettierrc`, CSS Modules 글로벌 토큰(CSS 변수), 디렉토리(`app/`·`components/`·`lib/`·`mocks/`·`types/generated/`·`test/`). `data-testid` 규약 주석. (US-H1 기반)
- [x] **Step 2 — DTO 타입 생성(TypeGen 파이프라인, LC-7)**: `shared/dtos/*.schema.json` → `frontend/types/generated/*.ts` 생성 스크립트(`pnpm gen:types`) + 생성 산출물. SSOT 파생(수정 금지 주석). (BR-U5-19)
- [x] **Step 3 — ApiClient + Transport Seam(LC-2, server-only)**: `lib/api/` — ApiClient 인터페이스(`search`/`signup`/`login`/`logout`/`currentSession` 활성 + 라이브러리/이력 시그니처 stub), `Transport` 인터페이스, `UserFacingError` 정규화(401/403/429/5xx/네트워크), 차등 재시도(멱등 GET 1회)+타임아웃+in-flight 디듀프(P-R1). `HttpTransport`는 `server-only`(쿠키 포워딩·baseURL). (BR-U5-17/18, NFR-U5-S1)
- [x] **Step 4 — Mock 픽스처 + MockTransport(MR mirror)**: `mocks/` — `shared/dtos` 파생 픽스처: SearchResponse 4분기(page/abstain/degraded/invalid)·KO↔EN cross-lingual 샘플·계정(signup/login/session). `MockTransport`가 픽스처 반환. (BR-U5-19)
- [x] **Step 5 — SessionContext + useSession(LC-3, client)**: `components/session/` — `SessionContext`(status·user), `useSession`. `currentSession` 부트. 토큰 미보유. (NFR-U5-S7)
- [x] **Step 6 — RouteGuard + 보호 라우트(LC-4)**: anonymous→로그인 리다이렉트(목적지 보존). 슬라이스: 검색 라우트 가드. (BR-U5-15, SEC-8)
- [x] **Step 7 — ErrorBoundary(2계층) + StateView(LC-5/6)**: 루트 글로벌 바운더리(fail-closed·스택 차단 SEC-15) + 세그먼트 바운더리. `StateView`(loading/empty/abstain/degraded/invalid/error, 기권≠빈결과, 저하 배너). `data-testid`. (NFR-U5-R1/R3, US-D7)
- [x] **Step 8 — SearchScreen 상태머신(client)**: `validateInput`(≤500자·trim·무해화 SEC-5), `submitQuery`(로딩·디듀프·버튼 비활성), union 분기 렌더. `data-testid=search-*`. (US-D1, FR-1, FR-11)
- [x] **Step 9 — ResultList + ResultCard(server)**: ResultList(랭킹순 top-N·저하 배너 슬롯), ResultCard(**7필드만**·텍스트 이스케이프·arxivUrl http/https+noopener·`data-testid=result-card-*`). (US-D4, FR-3/4/5, SEC-9, BR-U5-4~7)
- [x] **Step 10 — Signup/LoginForm(client)**: 생성타입 파생 검증(필수·형식), 정책 메시지는 백엔드 응답 표시, `password` 입력 전용. `data-testid=signup-*`/`login-*`. (US-A1/A2, BR-U5-2/13)
- [x] **Step 11 — HeroLanding + PhoneMockupFrame + AppShell(LC-1)**: AppShell 루트 레이아웃·라우팅·세션·바운더리·히어로 골격; PhoneMockupFrame(폰 풀블리드/태블릿+ 목업·리플로우 금지); HeroLanding(검색 CTA + 가입/로그인 유도). (US-H1, NFR-U1/U2)
- [x] **Step 12 — SecurityHeaders/CSP(LC-8)**: `next.config`/middleware — CSP(default-src self·object-src none·frame-ancestors self·base-uri self)+보안 헤더. (SEC-4, NFR-U5-S5)
- [x] **Step 13 — ObservabilityHooks(LC-9)**: 검색·로그인 경로 경량 계측(시작/종료·에러분류·지연), 구조화 로그. (NFR-U5-O1)
- [x] **Step 14 — 테스트**: Vitest+Testing Library(SearchScreen 상태머신·StateView 분기·ResultCard 7필드/이스케이프·ApiClient 재시도/정규화), **DTO 계약 테스트**(생성타입↔mock 정합), Playwright E2E 스캐폴드(히어로 흐름, data-testid). (BR-U5-22)
- [x] **Step 15 — 문서**: `frontend/README.md` 갱신(구조·실행·스택) + `aidlc-docs/construction/u5-frontend/code/README.md`(코드 요약·매핑·mock 계약·real 전환 절차).
- [x] **Step 16 — 배포 아티팩트**: 최소 빌드 설정(`Dockerfile` 또는 빌드 스크립트)·`.gitignore`(node_modules·.next). 구체 호스팅 토폴로지는 Infra 후속(스캐폴드만).

---

## 검증 기준 (Part 2 완료 시)
- `pnpm install` → `pnpm gen:types` → `pnpm lint` → `pnpm test` 통과(로컬). `pnpm build` 성공.
- 전 단계 체크박스 [x], 스토리(US-H1·US-D7·기여) 구현 표시.
- mock-first: 네트워크 없이 4분기·인증 흐름 동작. real 전환은 transport 교체만.

## 게이트 규약
- **승인 전 코드 미생성**(Part 1 게이트). 승인 시 Part 2 Step 1~16 순차 실행·체크박스 즉시 마킹.
- 미커밋(생성·검증 후 별도 커밋/푸시 승인). `shared/`·`backend/` 미편집.
- 커밋 메시지·코드·문서에 개발지침 파일명 비언급.
