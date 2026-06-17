# U5 Frontend — Functional Design Plan

**단계**: CONSTRUCTION → Functional Design (유닛 루프 진입) · **일자**: 2026-06-16
**Owner**: Track 3 (@kyjness) · **Deploy unit**: ④ frontend (독립) · **브랜치**: `feature/u5`
**근거 문서(발명 금지)**:
- `inception/application-design/components.md` §U5 (AppShell·PhoneMockupFrame·SearchScreen·ResultList·ResultCard·StateView·ApiClient)
- `inception/application-design/unit-of-work.md` / `unit-of-work-story-map.md` (US-H1 주·US-D7 주 + US-D1/D4/A1/A2/L1/L2/L3 기여)
- `shared/dtos/search.schema.json` (SearchResponse union), `accounts.schema.json`, `library.schema.json`
- `construction/u2-discovery/code/` (mock U2 계약 — mock-first 개발 대상)

> **기술 무관 원칙**: 이 단계는 비즈니스 로직·화면 구조·인터랙션·상태 전이만 다룬다. 프레임워크/SSR/타입 생성·번들·렌더링 등 기술 스택 결정은 **NFR Requirements(§5-D)** 로 보류한다.

---

## A. Functional Design 작업 항목 (체크박스)

- [ ] A1. U5 화면 맵(라우트 ↔ 스토리 ↔ 컴포넌트) 정의 — 히어로/검색/결과/계정(가입·로그인)/라이브러리/이력/상태
- [ ] A2. 컴포넌트 계층 + 책임 경계 확정 (components.md §U5 7컴포넌트 기준; 분해/추가는 Part 1 근거 있을 때만)
- [ ] A3. SearchResponse union(4분기: page/abstain/degraded/validationError) → StateView UX 전이 모델
- [ ] A4. ResultCard 뷰모델 — 7필드(title·authors·year·arxivId·abstractSnippet·relevance·arxivUrl)만, 내부필드 차단(SEC-9)
- [ ] A5. ApiClient 호출 표면(method 목록·요청/응답 계약·U6 게이트웨이 단일 진입) + mock-first 시나리오
- [ ] A6. 인증·보호 라우트 가드(SEC-8 클라이언트 반영)·세션 컨텍스트 전파 모델
- [ ] A7. 폼/입력 검증 규칙(검색 ≤500자 SEC-5; 가입·로그인 필드는 U3 DTO 미러)
- [ ] A8. 빈/실패/저하/로딩 상태·전역 에러 바운더리(FR-11, NFR-R1, SEC-15 스택트레이스 차단)
- [ ] A9. 폰 목업 프레임 거동(NFR-U2 뷰포트 분기·리플로우 금지) — 기술무관 규칙으로 기술
- [ ] A10. 라이브러리/이력 목록 — 커서 기반 조회 계약(U4 DTO), 검색결과(top-N 단일응답)와 구분
- [ ] A11. data-testid 명명 규약(자동화 친화 UI 규칙)
- [ ] A12. 산출물 작성: `business-logic-model.md`·`business-rules.md`·`domain-entities.md`·`frontend-components.md`

---

## B. 결정 필요 질문 ([Answer] 태그에 답변 기입)

### B1. 화면/스코프
> 이번 FD에서 다룰 화면 범위. US-H1(히어로)·US-D7(상태UX)이 U5 **주** 스토리, 나머지(A1/A2/L1/L2/L3)는 기여.
- Q1. 이번 FD 1패스에 **전 화면(검색·결과·가입·로그인·라이브러리·이력·상태)** 을 다 설계할지, 아니면 **히어로 슬라이스(가입→검색→근거화 결과+상태UX)** 먼저 좁게 설계하고 라이브러리/이력은 후속 패스로 미룰지?
  - [Answer]: **히어로 슬라이스 우선** (가입→검색→근거화 결과+상태UX). 라이브러리/이력은 후속 패스.

### B2. 상태 관리 전략
> Part 1: 전역 상태는 타당한 사유 있을 때만.
- Q2. 클라이언트 상태를 **세션 컨텍스트 + 화면 로컬 상태**로 최소화(전역 스토어 없음)하는 방향이 맞는지? 검색 결과/이력 캐싱이 필요하다면 어느 화면에서?
  - [Answer]: **맞음.** 전역은 AppShell의 세션 컨텍스트(`useSession`)만. 검색 결과는 SearchScreen 로컬 상태(단일 요청/응답이라 별도 캐시 불필요). 라이브러리/이력은 화면 로컬 + 커서 페이지 누적(후속 패스). 서버상태는 ApiClient 어댑터로 격리 → 클라/서버 상태 분리. 전역 스토어는 도입 안 함(Part 1 — 사유 없음).

### B3. SearchResponse 4분기 UX
> union: SearchResultPageDTO / AbstainDTO / DegradedResultDTO / ValidationErrorDTO.
- Q3-a. **abstain(기권)** 과 **빈 결과(page·resultCount 0)** 를 사용자에게 **다른 메시지**로 구분 표시할지? (FD §Q4=A "빈 성공 금지" 정신 반영)
  - [Answer]: **예, 구분.** abstain = "확실한 근거를 찾지 못해 결과를 표시하지 않았습니다"(재질의 유도). empty = "검색 결과가 없습니다"(질의 조정 유도). 두 상태를 같은 화면으로 뭉개지 않음(StateView.renderEmpty vs 기권 분기).
- Q3-b. **degraded(저하)** 시 상단 배너 문구 톤 — 비기술적 안내(예: "일부 결과만 표시")로 통일, degradationMode 원문 노출 금지 맞는지?
  - [Answer]: **맞음.** `meta.degraded=true`일 때만 상단 비기술 배너("일부 결과만 표시됩니다") + 결과 리스트는 정상 렌더. `degradationMode`(lexical-only 등) 원문은 화면 비노출 — 내부 분기 힌트로만(QT-3, SEC-9).

### B4. ResultCard relevance 표시
> `relevance`는 표시 전용 파생값(raw 점수 비노출 SEC-9). DTO상 display type은 U2 FD에서 정제.
- Q4. 카드의 relevance를 **순서(랭킹)만으로 암시**할지, **등급/배지(예: 높음·보통)** 로 보일지, 아니면 U2가 주는 표시값을 그대로 렌더만 할지?
  - [Answer]: **U2가 주는 표시값을 그대로 렌더.** U5는 relevance를 자체 계산/등급화하지 않음. 기본은 랭킹 순서 보존으로 관련도 암시, U2가 표시용 grade를 주면 그 값만 배지로 출력. raw 점수·내부 신호는 절대 비노출(SEC-9). display type 정의 권위는 U2 FD.

### B5. 인증·보호 라우트
- Q5. 보호가 필요한 라우트 목록(예: 라이브러리·이력·검색저장)과, **비로그인 접근 시 거동**(로그인 화면 리다이렉트 vs 인라인 안내)? 검색 자체는 인증 필수(U2 FD §Q5=A)이므로 히어로에서 검색 전 가입/로그인 유도 흐름이 맞는지?
  - [Answer]: **맞음.** 검색은 인증 필수 → 히어로 비로그인 진입에서 검색 시도 시 가입/로그인 유도. 보호 라우트: 검색실행·검색저장·라이브러리·이력. 비로그인 접근 → 로그인 화면 리다이렉트(원래 목적지 보존 후 복귀). 클라 가드는 SEC-8의 편의 반영일 뿐, 권위는 백엔드(게이트웨이 401/403). **이번 슬라이스 1패스 범위: 가입→로그인→검색까지.** 라이브러리/이력 가드는 후속 패스(계약만 명시).

### B6. 폼 검증 출처
> 클라 검증은 UX 보조일 뿐, 권위는 백엔드(U3). 규칙 중복 정의는 드리프트 위험.
- Q6. 가입/로그인 폼의 클라이언트 검증 규칙을 **`shared/dtos/accounts.schema.json`에서 파생(미러)** 하고, 미정의 규칙(예: 비밀번호 복잡도 메시지)은 백엔드 응답 메시지에 위임하는 방향이 맞는지?
  - [Answer]: **맞음.** 형식·필수·길이 등은 accounts.schema.json 파생(드리프트 0). 비밀번호 복잡도·블랙리스트 같은 정책 위반 메시지는 백엔드(U3) 응답에 위임. `password`는 입력 전용 — 본문/로그/URL/클라 저장소 노출 금지(SEC-12/3). 검색 질의 ≤500자(SEC-5)는 클라 인라인 검증.

### B7. 폰 목업 프레임
- Q7. 데스크톱/태블릿 목업 프레임 진입 **뷰포트 경계 기준**(폰 풀블리드 ↔ 목업 전환 폭)을 FD에서 의미적으로만 정하고(예: "태블릿 이상에서 목업"), 구체 px/CSS는 NFR/코드로 미룰지?
  - [Answer]: **예, 의미적으로만.** FD 규칙: "폰 뷰포트=풀블리드, 태블릿/데스크톱 이상=중앙 폰 목업 프레임, 프레임 내부폭=폰 뷰포트로 고정(리플로우 금지)". 구체 px 브레이크포인트·CSS는 NFR/코드 단계. NFR-U2 + SEC-4(frame-ancestors=self) 마크업 부합.

### B8. 라이브러리/이력 페이지네이션
- Q8. 라이브러리·이력 목록은 **커서 기반 무한스크롤**(`library.schema.json` 커서 계약)로 설계, 검색 결과는 top-N 단일 응답(페이지네이션 없음)으로 명확히 구분 — 이 구분이 맞는지? 무한스크롤 트리거(스크롤 말단 vs "더 보기" 버튼)는?
  - [Answer]: **맞음.** 라이브러리/이력 = 커서 무한스크롤(library.schema.json 커서), 검색결과 = top-N(~20) 단일응답(페이지네이션 없음). 트리거: 스크롤 말단 자동 로드 + 실패 시 "다시 시도" 폴백(무한 로딩 금지). **이번 슬라이스 1패스 범위 밖 — 계약/구분만 명시하고 구현은 후속 패스.**

### B9. mock-first 경계
- Q9. U2는 mock 응답(`construction/u2-discovery/code/` 계약)으로 선행 개발. U3 계정·U4 라이브러리 백엔드도 **mock으로 동시 진행**할지, 아니면 이미 머지된 U3/U4 모듈 응답을 직접 가정할지(게이트웨이 U6 미배포 상태 고려)?
  - [Answer]: **전부 DTO 계약 기준 mock-first.** mock은 머지된 모듈 내부가 아니라 `shared/dtos/*.schema.json`(SSOT)에서 파생. ApiClient를 transport seam으로 설계 → 지금은 DTO 파생 픽스처(MockTransport), U6 게이트웨이 + U2 real infra 도입 시 **transport를 http로 설정 교체**(컴포넌트·StateView 리라이트 없음). 머지된 U3/U4 모듈 내부 응답 모양은 직접 가정하지 않음(게이트웨이가 정규화하므로). 향후 로드맵: U6까지 신속 개발 후 U2 real 어댑터 부착 — 이때 transport만 스왑.

### B10. 추가 우려/제약
- Q10. 위에서 안 다뤄진 화면·인터랙션·접근성·엣지케이스 제약이 있으면 여기에. (없으면 "없음")
  - [Answer]: 접근성 기본(시맨틱 마크업·키보드/스크린리더·충분한 대비). **XSS**: 논문 제목·초록 등 외부 데이터는 텍스트 이스케이프 렌더(원시 HTML 주입 금지). **외부 링크**: `arxivUrl`은 http/https 스킴 검증 + `rel="noopener noreferrer"`. data-testid 명명 규약(B-A11). 그 외 새 제약 없음.

---

## C. 게이트 규약
- 본 플랜의 `[Answer]` 전부 채워지면 → 모호 답변 후속 질문(필요시) → **Step 6 산출물 생성** → 완료 메시지(리뷰 게이트).
- 승인 전 산출물 생성·커밋·push/PR 없음. `shared/`·`backend/` 편집 없음(트랙 소유 경계).
- 승인 시 `audit.md` 로그 + `aidlc-state.md` U5 FD 완료 표시.
