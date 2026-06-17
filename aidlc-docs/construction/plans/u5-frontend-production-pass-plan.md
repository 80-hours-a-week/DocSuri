# U5 Frontend — Production Pass Code-Generation Plan (real wiring + library/history)

**단계**: CONSTRUCTION → Code Generation (후속 패스, Part 1 계획) · **일자**: 2026-06-17
**Owner**: Track 3 (@kyjness) · **Deploy unit**: ④ frontend (독립) · **브랜치**: `feature/u5-v2`
**선행**: U5 mock-first Code Generation 완료(PR #47); develop에 U2 실어댑터(#57)·U3 정정(#52/#55/#56)·U4(#49)·U6 통합(#51) 머지됨
**스택**: 변경 없음 — Next.js(App Router SSR)·TypeScript·생성타입·ApiClient transport seam·CSS Modules·pnpm·Vitest/Playwright

> **이 계획서가 본 패스 Code Generation의 SSOT다.** 생성은 이 단계 순서를 정확히 따른다(임의 로직 금지).

## 목표 (이번 패스의 정의)
mock-first 히어로 슬라이스를 **production-ready 앱 코드**로 끌어올린다 — 실 백엔드 계약에 정렬 + 실 transport 배선 + 라이브러리/이력 화면 풀 구현. **인프라/CD/호스팅 토폴로지는 본 패스 범위 밖**(공통 인프라 단계 ⑦에서 U1 등과 함께).

## 확정 결정 (리뷰에서 권장안으로 합의, 2026-06-17)
- **D-Q1 (auth 갭)**: 게이트웨이가 세션쿠키→`request.state.principal`을 주입하지 않는 결함은 **`backend/` 조율존(@ELSAPHABA) + 공통 인프라 단계의 일**로 분리한다. U5는 계약 정렬 + 실 transport 배선까지 production-ready로 만들고, **검증은 mock·계약 테스트**로 한다. → 아래 §의존성 플래그.
- **D-Q2 (MFA UX)**: TOTP MFA는 시딩 관리자 전용(BR-A7)이므로 **본 패스 범위 밖**. 일반 사용자 로그인만 지원하고, 백엔드가 MFA-required를 반환하면 **명확한 안내 메시지로 graceful 처리**(챌린지 화면 미구현).
- **D-Q3 (검증)**: `tsc --noEmit` 0 / `vitest` 전통과 / `next build` 성공 + **계약 테스트(생성타입 ↔ shared DTO 1:1)**. 실 백엔드 docker e2e는 auth 갭(D-Q1)이 닫히는 ⑦ 단계로 보류.

## 계약 드리프트 — 정렬 대상 (실 백엔드 = SSOT)
프런트가 머지된 백엔드 실 라우트에 맞춘다. `shared/`·`backend/`는 **미편집**(읽기/타입생성만).

| 프런트(현재) | 실 백엔드 라우트 | 비고 |
|---|---|---|
| `POST /search` | `POST /api/search` | discovery router |
| `POST /accounts/signup` | `POST /auth/signup` (201) | accounts |
| `POST /accounts/login` | `POST /auth/login` | MFA-required 응답 graceful (D-Q2) |
| `POST /accounts/logout` | `POST /auth/logout` | |
| `GET /accounts/session` | `GET /auth/session` | 401=익명 |
| `listSavedSearches()` stub | `GET /library/saved-searches?limit&cursor` | 커서 페이지 |
| `saveSearch()` stub | `POST /library/saved-searches` {query,label?} (201) | |
| `deleteSavedSearch()` stub | `DELETE /library/saved-searches/{id}` (204) | |
| (없음) | `POST /library/saved-searches/{id}/rerun` | → SearchResultSetDTO(=검색 union) |
| `listLibrary()` stub | `GET /library/items?limit&cursor` | 커서 페이지 |
| `addToLibrary()` stub | `POST /library/items` {arXivId, meta} (201) | meta=카드 스냅샷 |
| `removeFromLibrary()` stub | `DELETE /library/items/{id}` (204) | |
| `listHistory()` stub | `GET /library/history?limit&cursor` | 커서 페이지 |
| (없음) | `POST /library/history/{id}/rerun` | → SearchResultSetDTO |
| (없음) | `DELETE /library/history` (204) | 이력 비우기 |

**DTO 주의**: 와이어 필드명은 `arXivId`(대문자 X). `meta` 스냅샷 = ResultCard 7필드 파생(`title·authors·year·arxivId·abstractSnippet·arxivUrl`, `LibraryItemMeta` 형상). rerun 응답은 `search.schema.json#SearchResultPageDTO` 재사용 → 기존 `classifySearchResponse` 그대로 사용.

## 잔여 UI 결정 (권장 기본값 — 리뷰 게이트 override 가능)
- **D1 라우트**: `/library`(라이브러리), `/library/saved`(저장검색), `/library/history`(이력) — 셋 다 RouteGuard 보호.
- **D2 내비**: 인증 상태일 때 `AppHeader`에 라이브러리/이력 진입 노출(폰-퍼스트, 터치 타깃).
- **D3 진입점**: "라이브러리 담기"=`ResultCard` 액션 버튼(현재 카드 meta 스냅샷 전송), "검색 저장"=`SearchScreen` 액션(현재 질의 저장).
- **D4 페이지네이션**: 커서 방식만(`nextCursor`로 "더 보기"); 오프셋/총건수 가정 금지. 멱등 GET이므로 ApiClient 차등 재시도 적용.
- **D5 상태 UX**: 각 목록 화면에 로딩/빈/에러 상태(StateView 패턴 재사용); 무한 로딩 금지·재시도 경로 제공.
- **D6 멱등 add**: `addToLibrary` 재호출이 동일 항목 반환(서버 멱등)해도 UI는 "이미 담김"으로 안전 처리.

## 의존성 플래그 (U5 외부 — 팀에 올림)
- **🔴 backend auth 주입 갭 (Blocker for e2e, not for this pass)**: `backend/middleware/gateway.py`가 세션쿠키를 `request.state.principal`로 변환하지 않음 → assembled 앱에서 `/library/*`·`/api/search`가 401(`get_principal` fail-closed). discovery·library 공통 횡단. **@ELSAPHABA 조율존(`backend/`) + 공통 인프라 단계 ⑦**에서 해소 필요. U5 코드는 env로 분리되어 unblocked; 실 e2e만 이 갭에 의존.
- **인프라/CD/호스팅(NFR 후속)**: 호스팅 토폴로지·구체 CSP 값·정량 SLO·CD 파이프라인은 ⑦ 공통 인프라 단계.

---

## 생성 단계 (번호순·체크박스)

### P1 — 계약 정렬
- [x] **Step 1 — 경로/메서드 정렬**: `lib/api/apiClient.ts`의 활성 메서드 경로를 실 백엔드로 교정(`/api/search`, `/auth/signup|login|logout|session`). 상태코드 매핑 재확인(signup 201, login MFA-required 분기).
- [x] **Step 2 — 생성타입 드리프트 갱신(LC-7)**: `pnpm gen:types`로 `types/.schema-raw/` 재덤프 후 `types/generated/*.ts` 큐레이트 타입을 라이브러리 DTO(SavedSearch/Library/History/Page + `LibraryItemMeta`)·검색 union과 1:1 동기화. SSOT 미편집(읽기만).
- [x] **Step 3 — 로그인 MFA-required graceful(D-Q2)**: `login` 응답이 MFA-required 형상이면 `UserFacingError`(안내 메시지)로 정규화. 챌린지 화면 미구현·크래시 금지.

### P2 — 실 transport 배선
- [x] **Step 4 — getApiClient env 분기(LC-2)**: `lib/api/index.ts`가 `DOCSURI_GATEWAY_URL` 설정 시 서버 경로에서 `HttpTransport` 선택, 미설정 시 `MockTransport`. 클라 번들엔 `HttpTransport` 미포함(`server-only` 유지).
- [x] **Step 5 — 쿠키 포워딩 경계**: 서버 컴포넌트/route handler/서버 액션에서 인바운드 `Cookie` 헤더를 `HttpTransport`에 주입(게이트웨이 hop에만 토큰 존재, SEC-3/12). 상태변경 요청(POST/DELETE)은 서버 액션 경유 + CSRF 안전(SameSite 쿠키 전제).
- [x] **Step 6 — MockTransport 경로 동기화**: mock의 라우트도 실 경로(`/api/search`·`/auth/*`)로 맞춰 mock↔real 동작 동일성 유지(테스트 신뢰성).

### P3 — 라이브러리/이력 화면 (US-L1/L2/L3)
- [x] **Step 7 — ApiClient 실 메서드**: stub 7개(`listSavedSearches/saveSearch/deleteSavedSearch/listLibrary/addToLibrary/removeFromLibrary/listHistory`) + 신규(`rerunSavedSearch/rerunHistory/clearHistory`)를 실 경로·DTO로 구현. 커서 페이지·차등 재시도(GET). rerun은 `classifySearchResponse` 재사용.
- [x] **Step 8 — 라이브러리 화면(US-L2)**: `/library` — `LibraryPageDTO` 렌더(meta 스냅샷=카드 7필드, SEC-9 비노출 준수), 담기 해제(DELETE), 커서 "더 보기", 로딩/빈/에러(StateView). `data-testid=library-*`.
- [x] **Step 9 — 저장검색 화면(US-L1)**: `/library/saved` — 목록·삭제·**rerun→검색 결과 union 렌더**(기존 SearchScreen 결과 컴포넌트 재사용). `data-testid=saved-*`.
- [x] **Step 10 — 이력 화면(US-L3)**: `/library/history` — `HistoryPageDTO`(query·executedAt·resultCount), rerun, 전체 비우기(DELETE). `data-testid=history-*`.
- [x] **Step 11 — 진입점/내비(D2/D3)**: `AppHeader`에 인증 시 라이브러리/이력 진입; `ResultCard`에 "담기", `SearchScreen`에 "검색 저장" 액션. RouteGuard로 신규 라우트 보호.
- [x] **Step 12 — Mock 픽스처 확장**: `mocks/`에 library/saved/history 페이지 픽스처(커서 페이지네이션 포함) + MockTransport 라우팅. shared DTO 파생.

### P4 — 검증/문서
- [x] **Step 13 — 테스트(D-Q3)**: Vitest+TL(라이브러리/저장검색/이력 화면 상태·rerun·페이지네이션·삭제, ApiClient 신규 메서드 재시도/정규화, MFA-required graceful) + **계약 테스트 확장**(생성타입 ↔ shared DTO 라이브러리 계열 1:1). Playwright 히어로 e2e는 경로 변경 반영.
- [x] **Step 14 — 문서**: `aidlc-docs/construction/u5-frontend/code/README.md` 갱신(real 전환 완료·라이브러리/이력 추가·잔여 의존성 플래그) + `frontend/README.md` 실행/환경변수(`DOCSURI_GATEWAY_URL`).

---

## 검증 기준 (생성 완료 시)
- `pnpm install` → `pnpm gen:types`(드리프트 0 확인) → `pnpm lint` → `pnpm test`(신규 포함 전통과) → `pnpm build` 성공.
- 전 단계 체크박스 [x]. US-L1/L2/L3 구현 표시(stub 제거). 히어로 흐름 실 경로로 회귀 통과.
- mock-first 유지: `DOCSURI_GATEWAY_URL` 미설정 시 네트워크 없이 전 화면 동작. real 전환=env 설정만.
- **적대적 자기검토**: SEC-9(라이브러리 meta가 카드 7필드만·내부 score 비노출), SEC-8(owner 비노출·cross-owner 404), 커서 페이지 경계, rerun 401/저하/기권 분기, MFA-required 비크래시.

## 게이트 규약
- **승인 전 코드 미생성**(Part 1 게이트). 승인 시 Step 1~14 순차 실행·체크박스 즉시 마킹.
- 생성·검증 후 별도 커밋; **push/PR은 명시 승인 후**. `shared/`·`backend/` 미편집.
- 커밋 메시지·코드·문서에 개발지침 파일명 비언급.
