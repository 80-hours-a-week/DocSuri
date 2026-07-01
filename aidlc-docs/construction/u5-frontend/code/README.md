# U5 Frontend — Code Summary

**단계**: CONSTRUCTION → Code Generation · **유닛**: U5 Frontend (Track 3) · **배포 단위**: ④
**코드 위치**: `frontend/` (Next.js App Router SSR)
**계획서(SSOT)**: `construction/plans/u5-frontend-code-generation-plan.md`(mock-first) → `…/u5-frontend-production-pass-plan.md`(production 패스)

> **현재 상태(2026-06-17 production 패스 완료)**: 히어로 + 라이브러리/저장검색/이력 전 화면 구현. 실 백엔드 라우트에 계약 정렬, 실 transport(BFF) 배선. 검증: `tsc` 0 · `vitest` **48 passed(9 files)** · `next lint` clean · `next build` 성공(라우트 10개, `/bff/[...path]` 동적). 아래 "production 패스" 절 참조. 그 위 본문은 최초 mock-first 슬라이스(2026-06-16) 기록.

---

## (최초) mock-first 슬라이스 — 2026-06-16

**스코프**: 히어로 슬라이스

## 검증 결과 (로컬)
- `pnpm install` → OK · `pnpm exec tsc --noEmit` → **0 errors** · `pnpm test` → **32 passed (7 files)** · `pnpm build` → **성공**(전 라우트 컴파일, First Load JS ~113–116kB)
- mock-first: 백엔드/게이트웨이 없이 검색 4분기 + 인증 흐름 동작.

## 구조
```
frontend/
├── app/                      # 라우트 + 레이아웃(AppShell) + 에러 바운더리
│   ├── layout.tsx            # SSR 루트(SessionProvider + PhoneMockupFrame)
│   ├── page.tsx              # 히어로 랜딩(US-H1)
│   ├── error.tsx / global-error.tsx   # 2계층 에러 바운더리(LC-5, SEC-15)
│   ├── search/{page,error}.tsx        # 보호 라우트(RouteGuard) + SearchScreen
│   ├── signup/page.tsx · login/page.tsx
│   └── globals.css           # CSS 변수 토큰(라이트/다크)
├── components/               # PhoneMockupFrame·HeroLanding·SearchScreen·ResultList·
│   │                         #  ResultCard·StateView·Signup/LoginForm·AppHeader·RouteGuard
│   └── session/SessionContext.tsx     # useSession(LC-3)
├── lib/
│   ├── api/                  # apiClient·transport·mockTransport·httpTransport(server-only)·
│   │                         #  classify·errors(UserFacingError)·validate·index(factory)
│   └── observability.ts      # 핵심 경로 계측(LC-9)
├── mocks/                    # DTO 파생 픽스처(search 4분기·계정)
├── types/generated/          # shared/dtos 파생 TS 타입(큐레이트)
├── test/ · e2e/              # Vitest+Testing Library · Playwright
├── middleware.ts             # CSP/보안 헤더(LC-8, SEC-4)
└── Dockerfile                # Next standalone(배포 ④, 토폴로지는 Infra)
```

## 스토리 커버리지
- **US-H1**(주): 가입→로그인→검색→근거화 결과 흐름 + 히어로 랜딩.
- **US-D7**(주): StateView 빈/기권/저하/로딩/에러(기권≠빈결과 구분).
- 기여: **US-D1/D4**(SearchScreen·ResultCard 7필드), **US-A1/A2**(Signup/LoginForm).
- 계약만(후속 패스): **US-L1/L2/L3** — ApiClient에 시그니처 stub만(`listLibrary` 등 호출 시 후속 패스 안내).

## 핵심 설계 실현
- **Transport seam(BR-U5-19)**: `ApiClient` ← `Transport`. 현재 `MockTransport`(DTO 파생, 키워드 분기로 4분기 데모). **real 전환 = `HttpTransport`(server-only)로 설정 교체** — 컴포넌트/ApiClient 불변.
- **토큰 비노출(SEC-3/12)**: `HttpTransport`는 `import 'server-only'`로 클라 번들 차단. 세션 토큰은 httpOnly 쿠키 transport, `SessionInfo`만 화면 동기화.
- **SEC-9 7필드 한정**: `ResultCard`는 7필드만 렌더. relevance=U2 표시값 그대로(raw 미노출). 외부 텍스트 이스케이프, `arxivUrl` http/https + noopener.
- **차등 재시도(P-R1)**: 멱등 GET만 1회 재시도+타임아웃+in-flight 디듀프. 상태변경 재시도 없음. 실패는 `UserFacingError`로 정규화(스택 차단 SEC-15).
- **2계층 에러 바운더리(LC-5)**: 세그먼트(검색) + 루트/글로벌 fail-closed.
- **CSP(SEC-4)**: `frame-ancestors 'self'` 등 미들웨어 적용.

## ⚠️ 설계 결정 플래그 (TypeGen)
- 계획은 `shared/dtos/*.schema.json` → TS **자동 생성**. 그러나 SSOT 스키마는 (a) accounts/library가 **루트 타입 없이 $defs만** 보유, (b) `relevance` 등 **무타입 필드**라 `json-schema-to-typescript` 직접 생성물이 사용 불가(루트 캐치올·과도한 object 타입).
- 조치: `types/generated/*.ts`는 **스키마의 노출 계약을 충실히 미러한 큐레이트 타입**(빌드 소비). `pnpm gen:types`는 원시 생성물을 `types/.schema-raw/`에 덤프해 **드리프트 검토**용으로 보관. 노출 필드 집합은 스키마와 1:1 → 드리프트 0 유지.
- **승인 필요 사항**: 자동 생성 대신 큐레이트+드리프트검토 방식 채택(스키마 한계 대응). 팀이 원하면 후속에서 codegen 후처리 파이프라인으로 대체 가능.

## real 전환 절차(후속, U6 배포 시)
1. `lib/api/httpTransport.ts`에 게이트웨이 baseURL/쿠키 주입(서버 액션/route handler 경유).
2. `lib/api/index.ts`의 `getApiClient`가 서버 경로에서 `HttpTransport` 선택하도록 환경변수(`DOCSURI_GATEWAY_URL`) 분기.
3. 컴포넌트/상태머신/StateView 변경 없음.

---

## production 패스 — 2026-06-17 (브랜치 `feature/u5-v2`, 리뷰 게이트)

mock-first 슬라이스를 production-ready 앱 코드로 끌어올림. **스코프: 풀 기능(히어로 + 라이브러리/저장검색/이력) ①②③** (인프라/CD ④는 공통 인프라 단계로 분리). 확정 결정: auth 갭=백엔드 트랙 분리 · MFA=범위 밖 · 검증=로컬+계약테스트.

### P1 계약 정렬
- 프런트 경로를 머지된 실 백엔드에 정렬: 검색 `/search`→**`/api/search`**, 계정 `/accounts/*`→**`/auth/*`**.
- **login 계약 정정**: 실 `POST /auth/login`은 httpOnly 쿠키만 세팅하고 `{status,message}`만 반환(SessionInfo 미반환). `ApiClient.login()`을 `Promise<void>`로 바꾸고, 화면은 `GET /auth/session`(`currentSession`)으로 세션 동기화(`LoginForm`은 이미 `refresh()` 호출 — 무변경).
- **MFA**: 실 login엔 MFA-required 분기 없음(관리자 전용 `/auth/mfa/*`). 비-200은 user-facing 에러로 정규화 → graceful.
- 생성타입 드리프트 갱신: `types/generated/library.ts`에 `SavedSearchPageDTO·LibraryItem*·LibraryItemMeta·*PageDTO·History*·SearchResultSetDTO` 추가(shared 스키마 1:1; 와이어 `arXivId`(대문자 X) vs meta `arxivId`(소문자) 차이 충실 미러).

### P2 실 transport 배선 (BFF 패턴)
- **`app/bff/[...path]/route.ts`**(신규, 서버): 동일출처 catch-all. `DOCSURI_GATEWAY_URL` 있으면 `HttpTransport`(쿠키 포워딩+Set-Cookie 릴레이)로 게이트웨이 프록시, 없으면 `MockTransport`. 토큰은 서버 hop에만.
- **`lib/api/routeHandlerTransport.ts`**(신규, 클라이언트): 모든 호출을 `/bff/*`로. 동일출처라 httpOnly 쿠키 자동 첨부.
- `getApiClient`가 `NEXT_PUBLIC_DOCSURI_REAL_API` 플래그로 mock(인브라우저) vs BFF 선택. `HttpTransport`는 `import 'server-only'` — 클라 번들 미포함(빌드로 확인).
- 호출처 5곳(`SearchScreen·SessionContext·LoginForm·SignupForm`)을 `getMockApiClient`→`getApiClient`로 교체.

### P3 라이브러리/이력 화면 (US-L1/L2/L3)
- `ApiClient` stub 7개 제거→실구현 + `rerunSavedSearch·rerunHistory·clearHistory` 신규. 커서 페이지(`?limit&cursor`), rerun은 `classifySearchResponse` 재사용.
- 화면: `/library`(라이브러리, 담기 해제·더보기), `/library/saved`(저장검색, 삭제·다시검색 인라인), `/library/history`(이력, 다시검색·비우기). 공용 `usePaginatedList` 훅·`OutcomeView`·`LibraryTabs`·`cardFromMeta`(meta→카드, relevance 제거=SEC-9).
- 진입점: `AppHeader` 검색/라이브러리 내비, `ResultCard` "담기"(`SaveToLibraryButton`, 멱등 add), `SearchScreen` "검색 저장"(`SaveSearchButton`). `ResultCard`에 `action` 슬롯 + 선택필드(year/snippet/url) 가드 추가.

### P4 검증
- `tsc --noEmit` 0 · `next lint` clean · `next build` 성공. `vitest` **48 passed**(신규 `apiLibrary`·`libraryScreens` + `contract` 라이브러리 DTO 계약 확장). 적대적 자기검토: SEC-9(라이브러리 meta 6필드·relevance 미노출), SEC-8(owner 미노출), 커서 경계, rerun 분기, login 계약 정정, server-only 클라 미유출.

### ⚠️ 의존성 플래그(U5 외부)
- **게이트웨이 auth 주입 갭**: 조립된 백엔드가 세션쿠키→`request.state.principal`을 안 넣어 `/library/*`·`/api/search`가 실 백엔드에서 401(fail-closed). `backend/` 조율존 + 시스템 인프라 단계. U5 코드는 env 분리로 unblocked, 실 e2e만 이 갭 의존.
- **reCAPTCHA**: `/auth/login`의 선택 토큰 미전송(사이트키=시크릿/인프라 필요, 실배포 와이어링).
- **인프라/CD/호스팅·구체 CSP·정량 SLO**: 공통 인프라 단계(④).
