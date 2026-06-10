# Component Model — 작업 계획 (Construction Phase)

> **Phase**: AIDLC Construction — Domain(Component) Model Creation
> **입력 산출물**: [`design-artifacts/units/`](../design-artifacts/units/) — U0 Foundation · U1 Discover · U2 Comprehend · U3 Differentiate · U4 Trace (14 user stories / 70 SP)
> **출력 산출물**: [`design-artifacts/component-model.md`](../design-artifacts/component-model.md) (코드 생성 없음 — 설계 문서만)
> **입력 범위 제약** (사용자 지시, 2026-06-10): `aidlc-docs/` 밖의 코드·문서는 입력으로 사용하지 않는다. 코드는 AI-DLC가 정의한 문서만으로 만든다.
> **승인 게이트**: 본 계획은 사용자 승인 후에만 실행한다. 각 단계 완료 시 체크박스를 갱신한다.

---

## 사전 확인 (완료)

- [x] **S0. 입력 소스 확정** — 사용자 확인 (2026-06-10): 컴포넌트 모델의 근거는 `aidlc-docs/design-artifacts/units/`의 unit 파일들이다. (당초 지시문의 `design/seo_optimization_unit.md`는 존재하지 않는 placeholder였음)
- [x] **S1. 5개 unit 파일 정독** — U0~U4의 스토리·AC·포트 시그니처·DTO 계약·NFR 책임·변경 정책을 모두 추출 완료.

---

## 사용자 클래리피케이션 (실행 전 확인 필요)

> ✅ 3개 모두 사용자 확인 완료 (2026-06-10).

- [x] **C1. 출력 파일 구조** — **단일 파일** (unit별 섹션 구분)로 확정. 위치는 사용자 추가 지시("aidlc-docs 밖 문서 배제")와 기존 컨벤션(units도 prompt의 `design/` 지시 → `design-artifacts/`에 배치됨)에 따라 `aidlc-docs/design-artifacts/component-model.md`로 확정.
- [x] **C2. 문서 언어** — **한국어** (식별자·시그니처는 영문 유지)로 확정. 기존 aidlc-docs 컨벤션과 일치.
- [x] **C3. 다이어그램 표기법** — **Mermaid** (관계도 + Must 스토리 시퀀스 다이어그램)로 확정.

---

## 실행 단계 (승인 후 진행)

### Part A — 컴포넌트 식별

- [x] **A1. 모델링 규약 정의** — 문서 서두에 컴포넌트 기술 양식을 고정: `이름 / 소속 unit / 책임 1줄 / 속성(attributes) / 행위(behaviours, 시그니처 포함) / 의존(uses) / 구현 NFR / 출처 스토리`.
- [x] **A2. U0 Foundation 컴포넌트 모델** — 8개 포트(`EmbeddingPort`·`LlmPort`·`CachePort`·`SessionPort`·`Telemetry`·`Glossary`·`CitationApi`)를 인터페이스 컴포넌트로, 비용 가드(NFR-COST)·재시도/오프라인 HTTP 정책(NFR-NET)을 횡단 컴포넌트로 모델링.
- [x] **A3. U1 Discover 컴포넌트 모델** — 검색 오케스트레이터, 키워드 확장기(DISC-03), 난이도 추정기(A7 휴리스틱), 한→영 매핑 표시기(DISC-04), 정렬·필터 상태(URL 직렬화, DISC-02), 결과 카드(데스크톱 6메타/모바일 3메타+펼침) — `SearchResult` DTO 산출까지.
- [x] **A4. U2 Comprehend 컴포넌트 모델** — PDF/URL 텍스트 추출기, 페르소나 분기 요약기(전문/학부, COMP-01·03), 섹션 토글 상태(COMP-02), 부분 번역기(드래그/롱프레스 분기, COMP-04), 시각자료 설명기(COMP-05) — `SummaryResult`·`TranslationResult` DTO 산출까지.
- [x] **A5. U3 Differentiate 컴포넌트 모델** — 주제 초안 입력 검증기, 유사도 비교기(임베딩), 차별성 노트 생성기(DIFF-01), 연구 공백 제안기(DIFF-02, evidence_ids 포함), 학부 모드 가벼운 점검기(DIFF-03) — `NoveltyReport` DTO 산출까지.
- [x] **A6. U4 Trace 컴포넌트 모델** — 1-hop 인용 조회기(캐시·폴백), 폼팩터 분기 렌더러(데스크톱 그래프 ≤30노드 / 모바일 리스트, NFR-MOBILE-05), 영향력 Top-3 선별기(TRACE-02) — `CitationView` DTO 산출까지.

### Part B — 상호작용 모델

- [x] **B1. 컴포넌트 관계도** — unit 경계를 명시한 전체 컴포넌트 다이어그램 1장 (U0 포트 의존 + U1→U3, U2→U3, U1→U4 DTO 의존, acyclic 검증 포함).
- [x] **B2. 스토리별 상호작용 흐름** — 14개 user story 각각에 대해 "사용자 → 컴포넌트 체인 → DTO" 시퀀스 기술. Must 스토리(DISC-01·02, COMP-01·03·04, DIFF-01)는 시퀀스 다이어그램, Should/Could는 번호 매긴 텍스트 흐름으로 경량화.
- [x] **B3. 횡단 관심사 매핑** — 캐시 키 전략(unit별 TTL 24h/7d), Telemetry 기록 지점, 비용 가드 적용 지점을 컴포넌트별 표로 정리.

### Part C — 검증·마감

- [x] **C-V1. 커버리지 매트릭스** — 14 스토리 × 컴포넌트 매핑 표 작성. *누락·중복 0* 확인 (units-overview §1과 동일 기준).
- [x] **C-V2. 계약 정합 검증** — 모델의 모든 인터페이스가 units-overview §4 "인터페이스 합의 표"와 1:1 정합인지 확인. 포트 시그니처 임의 변경 0건.
- [x] **C-V3. 변경 정책 위반 검사** — 각 unit의 "금지" 항목(예: U0에 도메인 로직, U3의 검색 재구현) 위반 여부 자가 검사.
- [ ] **C-V4. 최종 리뷰 요청** — 완성된 컴포넌트 모델 문서를 사용자에게 제출, 피드백 반영.

---

## 범위 밖 (Out of Scope)

- 코드 생성 — 본 단계는 설계 문서만 산출한다 (지시문 명시).
- D1~D10 기술 스택 결정 — 컴포넌트 모델은 *포트/인터페이스 수준*에서 기술 중립으로 작성, 구현체 선택은 후속 단계.
- 비-MVP 기능 (알림·재현성·다단계 인용 트리 등).
