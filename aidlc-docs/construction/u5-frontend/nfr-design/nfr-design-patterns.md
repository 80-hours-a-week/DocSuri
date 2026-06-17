# U5 Frontend — NFR Design Patterns (NFR Design)

**단계**: CONSTRUCTION → NFR Design · **유닛**: U5 Frontend (Track 3) · **일자**: 2026-06-16
**스코프**: 히어로 슬라이스. **근거**: NFR Requirements 2종 · FD 4종 · components.md §U5.
**스택 전제**: Next.js(App Router SSR)·TS+생성타입·ApiClient transport seam·CSS Modules·httpOnly 쿠키 포워딩.

> 인프라 토폴로지·구체 헤더 값·px·호스팅은 후속(Infra). 여기선 패턴 수준.

---

## 1. 복원력 패턴 (Resilience)

### P-R1. ApiClient 차등 재시도 + 타임아웃
```
호출 분류:
  멱등 GET (search·listLibrary·listHistory·currentSession)
     → 타임아웃 + 1회 재시도(소량 지수 백오프)    [실패 일시성 흡수]
  상태변경 (signup·login·logout·save*·add*·remove*)
     → 재시도 없음(중복 부작용 방지) + 타임아웃
  4xx(검증·인증·권한)
     → 재시도 없음(사용자 정정/재인증 필요)
```
- 모든 응답 → `UserFacingError` 정규화(401/403/429/5xx/네트워크). 스택·내부 식별자 차단(SEC-15).
- 추적: NFR-U5-R2, RES-9, BR-U5-16/18.

### P-R2. SSR 로드 실패 = 완성 페이지 렌더
- SSR 중 게이트웨이 실패 → throw 대신 **에러/저하 상태로 렌더**(StateView). 항상 완성된 HTML 응답.
- 클라 하이드레이션 후 "다시 시도" 경로. 무한 로딩 금지.
- 추적: NFR-U5-R1/R2, BR-U5-10.

### P-R3. 2계층 에러 바운더리
```
RootBoundary (글로벌)  ── fail-closed 일반화 메시지·스택 차단(SEC-15)
  └ SegmentBoundary (검색/계정/…)  ── 부분 실패 격리 + 세그먼트 재시도
       └ StateView  ── 비기술 표시 표면(empty/abstain/degraded/error)
```
- 추적: NFR-U5-R1, BR-U5-11, FR-11.

### P-R4. 저하(degraded) 흐름
- `meta.degraded=true` → 상단 비기술 배너 + 카드 정상 렌더. `degradationMode` 원문 비노출.
- 추적: NFR-U5-R3, US-R2, QT-3, BR-U5-12.

---

## 2. 성능 패턴 (Performance)

### P-P1. 서버/클라 컴포넌트 경계
```
서버 컴포넌트(기본): AppShell·PhoneMockupFrame·HeroLanding·ResultList·ResultCard 렌더
클라 컴포넌트(경계): SearchScreen 입력/제출·SignupForm·LoginForm·SessionContext·ErrorBoundary
```
- 인터랙션 필요한 최소 영역만 클라이언트 → 클라 JS 번들 경량.
- 추적: NFR-U5-P1/P3.

### P-P2. 코드 스플릿 + 경량 번들
- 라우트 단위 코드 스플릿(App Router 기본). 무거운 의존 회피(Part 1). 정량 SLO는 측정 단계.
- 추적: NFR-U5-P1.

### P-P3. 캐싱 정책 (만료/무효화 명시)
| 대상 | 정책 |
|---|---|
| 정적 자산(JS/CSS/이미지) | 콘텐츠 해시 + immutable 장기 캐시 |
| 검색/세션/계정 응답 | `no-store`(개인화·인증, 무한 캐시 금지) |
| 생성 TS 타입 | 빌드 산출물(런타임 캐시 무관) |
- 추적: NFR-U5-P2, Part 2-A(캐시 만료 필수).

### P-P4. 단일 요청/응답 + 중복 제출 락
- 검색 제출 중 버튼 비활성·in-flight 디듀프. 로딩 표시 즉시.
- 추적: NFR-P1, BR-U5-18.

---

## 3. 보안 패턴 (Security)

### P-S1. server-only 호출 경계
- HttpTransport·쿠키 포워딩·게이트웨이 baseURL = **server-only 모듈**(클라 임포트 차단). 토큰은 서버↔게이트웨이 구간만. 클라는 서버 액션/라우트 핸들러 경유.
- 추적: NFR-U5-S1/S6, SEC-3/12, BR-U5-13/14.

### P-S2. CSP + 보안 헤더
- `default-src self`·`object-src none`·`frame-ancestors self`(SEC-4)·`base-uri self` + `X-Content-Type-Options`·`Referrer-Policy`. 구체 값/nonce는 코드/Infra.
- 추적: NFR-U5-S5, SEC-4.

### P-S3. 출력 무해화 (방어 심층)
- 외부 데이터 텍스트 이스케이프(원시 HTML 금지). `arxivUrl` http/https 스킴 검증 + `rel="noopener noreferrer"`. 노출 필드 7개로 한정(SEC-9).
- 추적: NFR-U5-S2/S3/S4, BR-U5-4~7.

### P-S4. 보호 라우트 가드
- `SessionContext` 클라 가드(편의) + 백엔드 401/403 권위. 비로그인 → 로그인 리다이렉트(목적지 보존).
- 추적: NFR-U5-S7, SEC-8, BR-U5-15.

---

## 4. 확장성 패턴 (Scalability)

### P-SC1. Stateless SSR 수평확장
- 서버 인메모리 세션·스티키 세션 없음(세션 권위=쿠키+백엔드) → 무상태 인스턴스 수평확장. 토폴로지/오토스케일은 Infra.
- 추적: NFR-U5-M3.

### P-SC2. 리스트 누적(후속 계약)
- 라이브러리/이력 커서 무한스크롤은 클라 누적 모델(말단 트리거 + 실패 재시도). 검색(top-N 단일)과 혼용 금지. 상세는 후속 패스.
- 추적: BR-U5-20.

---

## 5. 관측 패턴 (Observability)
### P-O1. 핵심 경로 계측
- 검색·로그인 경로에 경량 계측 훅(요청 시작/종료·에러 분류·지연). 구조화 로그. 외부 APM은 후속.
- 추적: NFR-U5-O1, Part 2-A.

---

## 6. 접근성 패턴 (Accessibility)
### P-A1. 포커스·라이브 영역
- 라우트 전환·상태 전이 시 포커스 이동, `aria-live`로 로딩/결과/에러 알림. 로딩=스켈레톤/스피너 일관. WCAG 2.1 AA 지향.
- 추적: NFR-U5-U2, BR-U5-21.
