# U5 Frontend — Logical Components (NFR Design)

**단계**: CONSTRUCTION → NFR Design · **유닛**: U5 Frontend (Track 3) · **일자**: 2026-06-16
**스코프**: 히어로 슬라이스. **근거**: nfr-design-patterns.md · FD frontend-components.md · NFR Requirements.
**스택**: Next.js App Router SSR · TS+생성타입 · ApiClient transport seam · CSS Modules.

> NFR 패턴을 실현하는 논리 컴포넌트와 경계. 인프라(호스팅·CDN)는 후속.

---

## 1. 논리 토폴로지

```
                          ┌─────────────────────────── 브라우저 (클라) ───────────────────────────┐
                          │  RootBoundary → SegmentBoundary → StateView                            │
                          │  SearchScreen(입력/제출) · Signup/LoginForm · SessionContext(useSession)│
                          └───────────────▲───────────────────────────────┬───────────────────────┘
                                          │ 하이드레이션                    │ 서버 액션/라우트 핸들러 호출
   ┌──────────────────────────────────────┴───────────────────────────────▼───────────────────────┐
   │                              Next.js SSR 서버 (stateless)                                       │
   │  서버 컴포넌트 렌더(AppShell·PhoneMockupFrame·HeroLanding·ResultList·ResultCard)               │
   │  ┌───────────────── server-only 경계 ─────────────────┐                                         │
   │  │ ApiClient ── HttpTransport ── 쿠키 포워딩 · baseURL │  ←── 토큰은 이 구간만                   │
   │  └────────────────────────┬───────────────────────────┘                                         │
   └───────────────────────────┼─────────────────────────────────────────────────────────────────┘
                               │ (mock 단계: MockTransport ← DTO 파생 픽스처)
                               ▼
                        U6 게이트웨이(단일 진입) ──▶ U2 / U3 / U4
```

---

## 2. 논리 컴포넌트 명세

### LC-1. SSR 렌더 경계 (서버/클라 분할)
- **책임**: 서버 컴포넌트 기본 렌더 + 클라 경계 최소화(P-P1). 첫 콘텐츠 SSR 제공.
- **클라 경계**: SearchScreen 입력/제출, Signup/LoginForm, SessionContext, ErrorBoundary.
- **NFR**: NFR-U5-P1/P3. FD 매핑: AppShell·PhoneMockupFrame·HeroLanding·ResultList·ResultCard(서버) / SearchScreen·폼(클라).

### LC-2. ApiClient + Transport Seam (server-only)
- **책임**: 타입드 호출·차등 재시도(P-R1)·타임아웃·UserFacingError 정규화·중복 디듀프.
- **경계**: `HttpTransport`·쿠키 포워딩·baseURL은 server-only(클라 임포트 차단, P-S1). `MockTransport`(DTO 파생)↔`HttpTransport` 설정 교체.
- **NFR**: NFR-U5-S1/S6, R2, P4. FD 매핑: ApiClient.

### LC-3. SessionContext (클라, AppShell 제공)
- **책임**: `SessionInfo`(userId·expiresAt) 보유·전파, `useSession`. 토큰 미보유(쿠키 transport).
- **NFR**: NFR-U5-S1/S7. FD 매핑: AppShell.useSession.

### LC-4. RouteGuard
- **책임**: 보호 라우트(검색실행·검색저장·라이브러리·이력) 가드. anonymous→로그인 리다이렉트(목적지 보존). 백엔드 401/403 권위.
- **NFR**: NFR-U5-S7, SEC-8. FD 매핑: AppShell 가드.

### LC-5. ErrorBoundary (2계층)
- **책임**: RootBoundary(글로벌 fail-closed·스택 차단) + SegmentBoundary(부분 격리·재시도)(P-R3). 표시 표면=StateView.
- **NFR**: NFR-U5-R1, SEC-15. FD 매핑: AppShell 전역 바운더리 + StateView.

### LC-6. StateView (표시 표면)
- **책임**: loading/empty/abstain/degraded/invalid/error 비기술 렌더. 기권≠빈결과 구분. 저하 배너.
- **NFR**: NFR-U5-R3/U4, FR-11. FD 매핑: StateView.

### LC-7. TypeGen 파이프라인 (빌드)
- **책임**: `shared/dtos/*.schema.json` → TS 타입 생성(빌드/CI 단계). 생성물 SSOT 파생(직접 수정 금지).
- **NFR**: NFR-U5-M2, BR-U5-19. + DTO 계약 테스트(생성 타입↔mock 정합).

### LC-8. SecurityHeaders / CSP
- **책임**: CSP(default-src self·object-src none·frame-ancestors self·base-uri self)+보안 헤더(P-S2). 구체 값/nonce는 코드/Infra.
- **NFR**: NFR-U5-S5, SEC-4.

### LC-9. ObservabilityHooks
- **책임**: 검색·로그인 경로 계측(시작/종료·에러분류·지연), 구조화 로그(P-O1).
- **NFR**: NFR-U5-O1.

---

## 3. FD 컴포넌트 ↔ 논리 컴포넌트 매핑
| FD 컴포넌트 | 렌더 경계 | 관련 LC |
|---|---|---|
| AppShell | 서버 + 클라(세션/가드/바운더리) | LC-1/3/4/5 |
| PhoneMockupFrame | 서버 | LC-1 |
| HeroLanding | 서버 | LC-1 |
| SignupForm/LoginForm | 클라 | LC-1, LC-2 |
| SearchScreen | 클라(입력/제출) | LC-1, LC-2, LC-6 |
| ResultList/ResultCard | 서버 | LC-1, LC-6(위임) |
| StateView | 서버/클라 공용 | LC-5/6 |
| ApiClient | server-only 경계 | LC-2, LC-7 |

---

## 4. 조율·후속 표시
- **⏳ U6 게이트웨이 미배포**: HttpTransport 비활성 → MockTransport(DTO 파생)로 개발. real 전환=transport 설정 교체.
- **⏳ Infra**: 호스팅(노드 SSR vs 정적+엣지)·CDN·오토스케일·구체 CSP/헤더·정량 성능 SLO.
- **트랙 경계**: `shared/`·`backend/` U5 브랜치 편집 금지.
- **다음 단계**: Code Generation(mock-first) — `frontend/` 코드 생성(승인 시).
