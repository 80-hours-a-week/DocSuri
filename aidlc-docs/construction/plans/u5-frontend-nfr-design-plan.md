# U5 Frontend — NFR Design Plan

**단계**: CONSTRUCTION → NFR Design · **일자**: 2026-06-16
**Owner**: Track 3 (@kyjness) · **Deploy unit**: ④ frontend (독립) · **브랜치**: `feature/u5`
**선행**: U5 NFR Requirements 완료·승인 (Next.js SSR·TS+생성타입·ApiClient seam·CSS Modules·쿠키 포워딩)
**근거**: `construction/u5-frontend/nfr-requirements/` 2종 · FD 4종 · components.md §U5

> 이 단계 목적: NFR 요구를 **설계 패턴 + 논리 컴포넌트**로 구체화(여전히 인프라 토폴로지·구체 px·호스팅은 후속). 스코프=히어로 슬라이스.

---

## A. NFR Design 작업 항목 (체크박스)

- [ ] A1. 복원력 패턴 — ApiClient 타임아웃/재시도/에러 정규화, 전역 에러 바운더리, 저하 배너 흐름
- [ ] A2. 성능 패턴 — SSR 렌더 경계(서버/클라 컴포넌트 분할)·코드 스플릿·번들 경량·캐싱(생성타입/정적 자산)
- [ ] A3. 보안 패턴 — 쿠키 포워딩 경계(서버 전용)·CSP/frame-ancestors·노출 필드 한정 렌더·링크 무해화
- [ ] A4. 확장성 패턴 — SSR stateless 수평확장(세션은 쿠키)·리스트 누적(후속 무한스크롤 계약)
- [ ] A5. 논리 컴포넌트 — SSR 렌더 경계·ApiClient(transport seam)·SessionContext·RouteGuard·ErrorBoundary·TypeGen 파이프라인 + FD 9컴포넌트 매핑
- [ ] A6. 관측 훅 — 검색/로그인 경로 계측 지점
- [ ] A7. 산출물: `nfr-design-patterns.md` · `logical-components.md`

---

## B. 결정 필요 질문 ([Answer] 태그에 답변 기입)

### B1. 복원력 — ApiClient 재시도 정책
> 검색=동기 단일 요청/응답. 백엔드 동기 호출.
- Q1. ApiClient 실패 처리를 **(A) 멱등 GET(검색·목록·세션)만 짧은 1회 재시도(지수 백오프 소량)+타임아웃, 상태변경(login/signup/save)은 재시도 없음(중복 방지) — 권장** / (B) 전 호출 재시도 / (C) 재시도 없음(타임아웃만) / (D) 기타
  - [Answer]: **A.** 멱등 GET(search·list·currentSession)만 1회 재시도(소량 백오프)+타임아웃. login/signup/save 등 상태변경은 재시도 없음(중복 방지). 4xx는 재시도 안 함(사용자 정정 필요).

### B2. 복원력 — SSR 데이터 로드 실패 경계
> SSR 중 게이트웨이 호출이 실패할 수 있음.
- Q2. SSR 서버 렌더 중 백엔드 실패 시 **(A) 서버에서 에러 상태로 렌더(StateView.error)하여 항상 완성된 페이지 응답, 클라에서 재시도 — 권장** / (B) 5xx 페이지 throw / (C) 기타
  - [Answer]: **A.** SSR 중 게이트웨이 실패는 StateView 에러/저하 상태로 렌더(완성 페이지 응답). 클라 하이드레이션 후 재시도 경로 제공. 스택/내부정보 비노출(SEC-15).

### B3. 성능 — SSR/클라 컴포넌트 분할
> Next.js App Router(서버 컴포넌트 기본).
- Q3. **(A) 기본 서버 컴포넌트, 인터랙션 필요한 곳(SearchScreen 입력·폼·ResultCard 액션)만 클라이언트 컴포넌트로 경계 — 권장** / (B) 전부 클라이언트 / (C) 기타
  - [Answer]: **A.** 기본 서버 컴포넌트(AppShell·PhoneMockupFrame·HeroLanding·ResultList·ResultCard 렌더). 클라 경계=SearchScreen 입력/제출·Signup/LoginForm·SessionContext·ErrorBoundary. 클라 번들 최소화.

### B4. 성능 — 캐싱 정책
> Part 2-A: 캐시는 만료/무효화 명시(무한 캐시 금지).
- Q4. **(A) 정적 자산=장기 캐시(콘텐츠 해시), 검색/세션 응답=no-store(개인화·인증), 생성타입=빌드 산출물 — 권장** / (B) 검색 결과도 단기 캐시 / (C) 기타
  - [Answer]: **A.** 정적 자산=콘텐츠 해시 immutable 장기 캐시. 검색/세션/계정 응답=no-store(개인화·인증, 무한 캐시 금지). 생성 TS 타입=빌드 산출물(런타임 캐시 무관).

### B5. 보안 — 쿠키 포워딩 경계
- Q5. **(A) 게이트웨이 호출은 서버 전용 모듈(server-only)로 격리, 쿠키 포워딩·baseURL은 서버 코드에서만 접근, 클라 번들에 유출 0 — 권장** / (B) 기타
  - [Answer]: **A.** HttpTransport·쿠키 포워딩·게이트웨이 baseURL을 server-only 모듈로 격리(클라 임포트 차단). 토큰은 서버↔게이트웨이 구간만. 클라는 서버 액션/라우트 핸들러 경유로만 호출.

### B6. 보안 — CSP / 프레임 정책
- Q6. **(A) CSP 기본 적용(script-src self·object-src none 등) + frame-ancestors self(SEC-4), 구체 헤더 값은 코드/Infra에서 확정 — 권장** / (B) CSP 후속 / (C) 기타
  - [Answer]: **A.** CSP(default-src self·object-src none·frame-ancestors self·base-uri self) + 보안 헤더(X-Content-Type-Options·Referrer-Policy). 구체 값/nonce 전략은 코드/Infra에서 확정. frame-ancestors self로 SEC-4 부합.

### B7. 확장성 — SSR 수평확장
- Q7. **(A) SSR 서버 stateless(세션은 httpOnly 쿠키, 서버 인메모리 세션 없음) → 무상태 수평확장, 인스턴스 토폴로지는 Infra — 권장** / (B) 기타
  - [Answer]: **A.** SSR 서버 stateless(세션 권위는 쿠키+백엔드, 서버 인메모리 세션·스티키 불필요) → 무상태 수평확장. 인스턴스 수/오토스케일은 Infra.

### B8. 논리 컴포넌트 — 에러 바운더리 계층
- Q8. **(A) 2계층: 라우트 세그먼트 바운더리(부분 실패 격리) + 루트 글로벌 바운더리(fail-closed 일반화·스택 차단 SEC-15) — 권장** / (B) 단일 루트 바운더리만 / (C) 기타
  - [Answer]: **A.** 2계층 — 세그먼트 error 바운더리(검색/계정 등 부분 실패 격리·재시도) + 루트 글로벌 바운더리(fail-closed 일반화 메시지·스택/내부 차단 SEC-15). StateView가 표시 표면.

### B9. 추가 패턴 우려
- Q9. 위에서 안 다뤄진 NFR 설계 우려(접근성 포커스 관리·로딩 스켈레톤·중복 제출 락 등) 있으면. (없으면 "없음")
  - [Answer]: 접근성 포커스 관리(라우트 전환·상태 전이 시 포커스 이동, aria-live로 상태 알림). 로딩=스켈레톤/스피너 일관. 중복 제출 락(in-flight 동안 제출 버튼 비활성, BR-U5-18). 그 외 새 우려 없음.

---

## C. 게이트 규약
- `[Answer]` 전부 채워지면 → 모호 답변 후속 질문(필요시) → **Step 6 산출물 생성**(`nfr-design-patterns.md`·`logical-components.md`) → 완료 메시지(리뷰 게이트).
- 승인 전 산출물 생성·커밋·push/PR 없음. `shared/`·`backend/` 편집 없음.
- 승인 시 `audit.md` 로그 + `aidlc-state.md` U5 NFR Design 완료 표시. 다음 단계: Code Generation(mock-first) 또는 Infra(후속).
