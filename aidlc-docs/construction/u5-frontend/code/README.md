# U5 Frontend — Code Summary (mock-first)

**단계**: CONSTRUCTION → Code Generation (Part 2) · **유닛**: U5 Frontend (Track 3) · **일자**: 2026-06-16
**코드 위치**: `frontend/` (Next.js App Router SSR) · **배포 단위**: ④ · **스코프**: 히어로 슬라이스
**계획서(SSOT)**: `construction/plans/u5-frontend-code-generation-plan.md`

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
