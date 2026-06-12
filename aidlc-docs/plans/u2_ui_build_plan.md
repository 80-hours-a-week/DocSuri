# U2 Comprehend HTTP+UI 빌드 — 작업 계획

> **Phase**: AIDLC Construction — Code Generation (U2 노출 라운드, 사용자 배정 2026-06-12)
> **전제**: U2 백엔드 도메인 모듈(`docsuri/u2/` — 타 팀원 작성, develop 머지됨)은 **무수정 재사용**이 원칙. 본 라운드는 U1·U4 전례의 "HTTP 표면 + BFF + UI"만 얹는다.
> **입력**: [`unit-u2-comprehend.md`](../design-artifacts/units/unit-u2-comprehend.md) (스토리 5·빌드 가능 정의) · [`component-model.md §4`](../design-artifacts/component-model.md) · U2 모듈 실코드(models·summary_engine·translator·document_ingestor·figure_explainer·section_toggle)
> **승인 게이트**: 사용자 승인 후 실행, 단계별 체크박스 갱신.

## 설계 결정 (실코드 근거 — 기본값)

- **본문 소스 = arXiv 초록**: `DocumentIngestor.ingest(arxiv_url)`이 이미 초록 기반 PaperText를 구성 — COMP-04의 "본문 부분 번역"은 MVP 데모에서 *초록 패널* 대상으로 한다 (PDF 전문 파싱은 U2 백엔드도 후속 — pdf_path 지원은 있으나 업로드 표면 없음).
- **COMP-02 섹션 토글 = 프론트 sessionStorage**: 백엔드 `SectionToggleController`는 SessionPort 기반인데 Lambda 무상태·익명 쿠키 미도입 — "동일 세션 내 기본값 유지" AC는 클라이언트 세션 저장이 정합. 백엔드 컨트롤러는 무수정 보존.
- **엔벨로프**: `{ summary: SummaryResult(동결 §3), readability: ReadabilityReport }` — UI 보조 필드는 U1 `query_mapping` 전례.
- **과금 가드**: 요약은 실 LLM 호출(예산 1200tok, 7d 캐시) — 입력 검증은 u1 `safety` 패턴(arxiv_url/id 형식·excerpt 최대 길이).

## 사용자 클래리피케이션

- [x] **C1. COMP-05 범위** — **이번 라운드 제외** 확정 (2026-06-12). arXiv API가 그림 캡션을 제공하지 않아 데모에 표시할 figure 데이터가 없음 — FigureExplainer는 백엔드에 보존, PDF 파싱 도입 시 후속.
- [x] **C2. 머지 후 재배포** — **포함** 확정 — PR 머지 후 내가 `deploy_lambda.sh`(백엔드)+Amplify 자동 빌드 확인까지 수행해 데모 URL에서 U2 기능 검증으로 종결.
- [x] **C3. 계획 승인** — 승인 (2026-06-12). 브랜치 `feature/aidlc-construction-u2-ui` → develop PR.

## 실행 단계

### Part A — 백엔드 HTTP 표면 (U2 모듈 무수정)

- [x] **A1. `u2/service.py`** — `build_u2(u0)` 팩토리 (u1 전례): Ingestor·SummaryEngine·SelectionTranslator 조립.
- [x] **A2. `u2/api.py`** — `POST /api/summaries` `{ paper_id|arxiv_url, mode }` → 엔벨로프 / `POST /api/translations` `{ source_excerpt, input_mode }` → TranslationResult. 입력 검증(safety 패턴). `app.py` 등록.
- [x] **A3. pytest** — stub ingestor 주입 라우트 테스트 6건 (4섹션·톤 분기·용어 적중·7d 캐시·422·404) — **전체 64 passed**. 엔벨로프에 `paper`(원문 초록) 보조 필드 추가.

### Part B — 프론트 (BFF + UI)

- [x] **B1. 계약 미러·BFF** — types 추가(동결 미러 주석) · `app/api/summaries|translations/route.ts` · `lib/comprehend-service.ts`(프록시+mock 폴백) · `lib/mock-comprehend.ts`(결정적).
- [x] **B2. `comprehend-flow.tsx`** — citation-flow 패턴 Drawer: 모드 토글(전문/학부, COMP-01·03) · 4섹션 접기/펼치기 + sessionStorage 기본값(COMP-02, 키보드 토글 NFR-A11Y-02) · 어휘 풀이 칩 · 학부 모드 readability 표시.
- [x] **B3. 초록 번역 패널** — 영문 초록 표시 + 데스크톱 드래그/모바일 롱프레스(500ms) 선택 → "번역"(≥44px, 1탭) → 데스크톱 인접 패널/모바일 바텀시트에 TranslationResult+용어 일관 표시 (COMP-04 AC).
- [x] **B4. 진입점** — paper-card footer에 "요약 보기" 버튼 추가(기존 "인용 흐름 보기"와 병렬 — footer prop 재사용, U1 파일 무수정).

### Part C — 검증·마감

- [x] **C-V1.** pytest 64 · lint/build 0 · **브라우저 E2E 통과**: 4섹션 렌더 → 학부 토글 톤 분기 → '방법' 접기 → **다른 논문 요약에 접힘 기본값 유지(COMP-02 AC)** → 더블클릭 선택 → 번역 인접 패널+용어 칩(attention→어텐션). 비고: 구 서버의 3002 점유로 1회 재기동.
- [x] **C-V2.** 커밋 분리·**PR #30** (U2 작성자 리뷰 요청 명시) — 머지 완료.
- [x] **C-V3.** 재배포·검증 완료 — Lambda 2회 배포(+**실모델 발견 수정**: Haiku가 마크다운 헤딩으로 응답해 섹션 파서가 fallback으로 밀리던 결함 → 헤딩 인식 보강+회귀 테스트, 65 passed) · Amplify 잡6 SUCCEED · 데모 URL 실 LLM 검증(전문 8.7s 4섹션 정확, 학부 가독성 7.75어절 통과, 번역+용어 칩) · U2 §6 **3/5 부분 표기**(COMP-05 제외·모바일 실기기 잔여).
- [ ] **C-V4.** 사용자 최종 리뷰.

## 범위 밖

- COMP-05 UI (C1) · PDF 업로드/전문 파싱 · 전역 페르소나 모드(요약 모드 토글은 화면 로컬 — U4 학부 토글과 동일 원칙) · U2 백엔드 모듈 수정.
