# U5 Frontend — Business Logic Model (Functional Design)

**단계**: CONSTRUCTION → Functional Design · **유닛**: U5 Frontend (Track 3) · **일자**: 2026-06-16
**스코프**: 히어로 슬라이스(가입→로그인→검색→근거화 결과 + 상태 UX). 라이브러리/이력 = 계약만(후속 패스).
**원칙**: 기술 무관. 비즈니스 로직 = **화면 상태 전이 + ApiClient 경유 데이터 흐름**. 모든 백엔드 호출은 U6 게이트웨이 단일 진입(직접 모듈 호출 금지).

---

## 1. 핵심 흐름 (히어로: US-H1)

```
[히어로 랜딩] ─(검색 시도)─▶ 인증?
   │ anonymous                    │ authenticated
   ▼                              ▼
[가입/로그인 유도] ─성공─▶ [검색 화면] ─submitQuery─▶ [결과/상태]
```

US-H1 "매직 모먼트" = 비로그인 진입 → 가입/로그인 → **첫 질의 → 근거화된 결과 카드**. 검색은 인증 필수(U2 FD §Q5=A)이므로 게이트 통과가 선행.

---

## 2. 검색 상태 머신 (SearchScreen + StateView, FR-11)

```
        submitQuery (클라 검증 통과)
 idle ───────────────────────────▶ loading
   ▲                                  │ ApiClient.search(SearchRequest)
   │ reset/재질의                      ▼
   │                      ┌──── SearchResponse union 분기 ────┐
   │                      ▼            ▼          ▼           ▼
   │              SearchResultPage  Abstain   Degraded   ValidationError
   │                 │  meta.count                          │
   │          ┌──────┴──────┐                               │
   │          ▼             ▼                               ▼
   │       page(>0)      empty(=0)                       invalid
   │          │             │                               │
   └──────────┴─────────────┴───────────────────────────────┘
                       │ (전송/네트워크/5xx 예외)
                       ▼
                     error  ── "다시 시도" 경로 제공(무한 로딩 금지)
```

### 2.1 상태별 처리
| 상태 | 트리거 | 화면 | 컴포넌트 |
|---|---|---|---|
| `loading` | 제출 직후 | 진행 표시(단일 요청/응답, NFR-P1) | StateView.renderLoading |
| `page` | SearchResultPageDTO & count>0 | 랭킹순 카드 N개 | ResultList→ResultCard |
| `empty` | SearchResultPageDTO & count=0 | "검색 결과가 없습니다"(질의 조정 유도) | StateView.renderEmpty |
| `abstain` | AbstainDTO | "확실한 근거를 찾지 못했습니다"(재질의 유도) | StateView(기권 분기) |
| `degraded` | DegradedResultDTO | 상단 저하 배너 + 카드 리스트 | ResultList + 배너 |
| `invalid` | ValidationErrorDTO | 인라인 필드 메시지 | StateView.renderError(인라인) |
| `error` | 전송 실패/5xx(예외) | 일반 에러 + 재시도 | StateView.renderError |

> **기권 ≠ 빈 결과**(B3-a): 두 상태는 다른 메시지·다른 분기. "빈 성공 금지" 정신.
> **저하 배너**(B3-b): `meta.degraded=true`일 때만 비기술 문구. `degradationMode` 원문 비노출.

---

## 3. ApiClient 데이터 흐름 (단일 진입점)

```
컴포넌트 ──타입드 호출──▶ ApiClient ──▶ Transport ──▶ U6 게이트웨이 ──▶ U2/U3/U4
                            │                              │
                  세션 쿠키 자동 동봉              401/403/429/5xx
                            │                              │
                            ◀──── UserFacingError 정규화 ───┘ (SEC-8/11/15)
```

- **Transport seam(B9)**: 지금은 `MockTransport`(DTO 스키마 파생 픽스처), 추후 `HttpTransport`(게이트웨이 baseURL)로 **설정 교체**. 컴포넌트는 transport를 모른다.
- **에러 정규화**: 401→로그인 유도, 403→권한 없음, 429→레이트리밋 안내, 5xx/네트워크→일반 에러+재시도. 스택트레이스·내부 식별자 차단(SEC-15, fail-closed).
- **중복 호출 방지**: 동일 요청 in-flight 시 재제출 차단(디듀프, 로딩 중 버튼 비활성).

### 3.1 메서드 표면 (components.md §U5 ApiClient)
- 슬라이스 1패스 활성: `search`, `signup`, `login`, `logout`, `currentSession`
- 계약만(후속): `listSavedSearches`/`saveSearch`/`deleteSavedSearch`, `listLibrary`/`addToLibrary`/`removeFromLibrary`, `listHistory`

---

## 4. 인증 흐름 (US-A1/A2 기여)

```
[가입] signup(SignupRequest) ─성공(SignupResult.accountId)─▶ [로그인 유도]
[로그인] login(LoginRequest) ─성공(Set-Cookie: 세션)─▶ currentSession() ─▶ SessionContext.authenticated
[로그아웃] logout() ─▶ 쿠키 무효화 ─▶ SessionContext.anonymous
```

- 실패는 **일반화된 인증 에러**로 표시(자격증명 존재 비노출 — U3 계약). 정책 위반 메시지는 백엔드 응답을 그대로 노출.
- 보호 라우트 접근 시 `SessionContext.status` 가드 → anonymous면 로그인 화면 리다이렉트(원래 목적지 보존). 권위는 백엔드 401/403.

---

## 5. 폰 목업 프레임 흐름 (NFR-U2)

```
classifyViewport(뷰포트)
   ├─ phone     → 풀블리드(앱 = 뷰포트 전체)
   └─ tablet+   → 중앙 폰 목업 프레임(내부폭=폰 뷰포트 고정, 리플로우 금지)
```
의미 규칙만 정의(B7). 구체 px 경계·CSS는 NFR/코드 단계. 프레임 내부 콘텐츠 로직은 뷰포트와 무관(동일 컴포넌트 트리).

---

## 6. 라이브러리/이력 (계약만, 후속 패스)
커서 기반 무한스크롤: 말단 도달 → 다음 커서 요청 → 누적. 실패 시 "다시 시도"(무한 로딩 금지). 검색 결과(top-N 단일응답)와는 페이지네이션 모델이 다름 — 혼용 금지. 상세는 후속 패스.
