# U5 Frontend — Business Rules (Functional Design)

**단계**: CONSTRUCTION → Functional Design · **유닛**: U5 Frontend (Track 3) · **일자**: 2026-06-16
**스코프**: 히어로 슬라이스. 라이브러리/이력 규칙은 계약 수준만.
각 규칙은 근거 ID(FR/SEC/NFR/US)에 추적. 발명 금지.

---

## A. 입력 검증 규칙 (클라이언트 = UX 보조, 권위 = 백엔드)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-U5-1 | 검색 질의는 1~500자. 공백만 입력 거부, 제출 전 trim·정규화(무해화). 위반 시 인라인 메시지·제출 차단 | FR-1, SEC-5 |
| BR-U5-2 | 가입/로그인 폼 검증은 `accounts.schema.json` 파생(필수·형식·길이). 비밀번호 복잡도·블랙리스트 등 **정책 메시지는 백엔드 응답에 위임**(클라에서 중복 정의 금지 — 드리프트 방지) | FR-7, US-A1/A2 |
| BR-U5-3 | 클라 검증 통과 ≠ 최종 승인. 백엔드 `ValidationErrorDTO`/4xx를 항상 우선 신뢰해 표시 | FR-1, FR-11 |

## B. 출력/렌더 규칙 (SEC-9 비노출 + XSS)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-U5-4 | ResultCard는 **7필드(title·authors·year·arxivId·abstractSnippet·relevance·arxivUrl)만** 렌더. 그 외 카드 필드·내부 점수·owner id·debug meta 렌더 금지 | SEC-9, FR-4 |
| BR-U5-5 | `relevance`는 U2 제공 표시값 그대로 렌더. U5가 raw 점수를 계산·노출·등급화하지 않음 | SEC-9, FR-3/4 |
| BR-U5-6 | 외부 데이터(title·authors·abstractSnippet 등)는 **텍스트로 이스케이프** 렌더. 원시 HTML 주입 금지 | SEC-5(콘텐츠 삽입) |
| BR-U5-7 | `arxivUrl` 링크는 **http/https 스킴만** 허용 + `rel="noopener noreferrer"`. 그 외 스킴 차단 | 안전하지 않은 링크 |
| BR-U5-8 | `degradationMode` 원문·내부 코드값은 화면 비노출. 저하는 `meta.degraded=true`일 때만 비기술 배너로 | SEC-9, QT-3 |

## C. 상태 전이 규칙 (FR-11)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-U5-9 | `SearchResponse` 4분기를 **각각 독립 상태**로 처리. 기권(abstain)과 빈 결과(page·count=0)를 동일 화면으로 합치지 않음 | FR-11, FD §Q4=A |
| BR-U5-10 | 로딩·실패·빈 상태를 항상 함께 설계. 응답/예외 없이 무한 로딩 금지 — 타임아웃·실패 시 "다시 시도" 경로 제공 | FR-11, RES-9, NFR-R1 |
| BR-U5-11 | 전역 에러 바운더리는 fail-closed 일반화 에러만 표시. 스택트레이스·내부 식별자 노출 금지 | SEC-15, NFR-R1 |
| BR-U5-12 | degraded 상태는 카드 리스트는 정상 렌더하되 상단 저하 배너를 동반(부분 결과 명시) | US-D7, US-R2, QT-3 |

## D. 인증·세션 규칙 (SEC-3/8/12)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-U5-13 | `password`는 입력 전용. 응답 본문·로그·URL·클라 저장소 어디에도 보관·표시 금지 | SEC-12, SEC-3 |
| BR-U5-14 | 세션 토큰은 secure/httpOnly 쿠키(transport)로만. JS·본문에서 토큰 접근·저장 안 함. 화면 동기화는 `SessionInfo`(userId·expiresAt)만 사용 | SEC-3, SEC-9 |
| BR-U5-15 | 보호 라우트(검색실행·검색저장·라이브러리·이력)는 `SessionContext` 가드. anonymous 접근 시 로그인 리다이렉트(목적지 보존). 클라 가드는 편의일 뿐, 백엔드 401/403이 권위 | SEC-8 |
| BR-U5-16 | 인증 실패는 일반화 메시지(자격증명 존재 비노출). 백엔드가 준 일반 에러를 그대로 표시 | SEC-12 |

## E. 데이터 흐름·호출 규칙

| ID | 규칙 | 근거 |
|---|---|---|
| BR-U5-17 | 모든 백엔드 호출은 ApiClient 단일 진입 → U6 게이트웨이 경유. 컴포넌트의 직접 fetch·모듈 호출 금지 | components.md §U5, SEC-8 |
| BR-U5-18 | 동일 요청 중복 호출 방지(in-flight 디듀프·제출 버튼 비활성) | NFR-P1 |
| BR-U5-19 | mock은 `shared/dtos`(SSOT) 파생만 사용. 머지된 U3/U4 모듈 내부 응답 모양을 직접 가정하지 않음. real 전환은 transport 스왑 | README, Q9 |
| BR-U5-20 | 라이브러리/이력은 커서 기반 무한스크롤(library.schema.json). 검색 결과(top-N 단일응답)에 오프셋·페이지네이션 가정 금지 — 두 모델 혼용 금지 | 목록 조회 규칙 |

## F. 접근성·자동화 규칙

| ID | 규칙 | 근거 |
|---|---|---|
| BR-U5-21 | 시맨틱 마크업·키보드 조작·스크린리더 라벨·충분한 대비를 기본 적용(모바일 우선) | 접근성 |
| BR-U5-22 | 상호작용 요소에 안정적 `data-testid` 부여(자동화 친화 UI 규칙) | 자동화 |

> 라이브러리/이력 관련 규칙(BR-U5-15의 일부, BR-U5-20)은 **계약 수준 명시**이며 구현 상세는 후속 패스 FD에서 확정.
