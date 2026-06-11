# U0 Foundation 빌드 — 작업 계획 (Code Generation Phase)

> **Phase**: AIDLC Construction — Code Generation (U0 진입 라운드)
> **입력 산출물**: [`unit-u0-foundation.md`](../design-artifacts/units/unit-u0-foundation.md) (빌드 가능 정의 §6) · [`component-model.md §2`](../design-artifacts/component-model.md) (포트 시그니처 — **동결, 단일 진실**) · [`architecture_decision_record.md §12`](../design-artifacts/architecture_decision_record.md) (확정 구현 매핑)
> **입력 범위 제약**: `aidlc-docs/` 밖 문서·기존 코드(demo/·app/·web/)는 참조하지 않는다.
> **승인 게이트**: 본 계획은 사용자 승인 후에만 실행. 각 단계 완료 시 체크박스 갱신.
> **통과 기준**: [U0 §6 빌드 가능 정의](../design-artifacts/units/unit-u0-foundation.md) 6항목 — *다른 unit 없이 단독 시연 가능*.

---

## 사전 확인 (완료)

- [x] **S0. 입력 정독** — U0 §3 포트 8종 시그니처, §6 빌드 가능 정의 6항목, ADR §12 구현 매핑(전부 확정), §13 비용 시뮬(보고서 충족 상태) 추출.
- [x] **S1. 결정 전제 확인** — D1~D10 전부 확정(ADR) → U0 §5 "진입과 동시에 닫아야 하는 결정" 조건 충족. 코드는 Python 3.12 + FastAPI, 어댑터는 Bedrock(도쿄)·DynamoDB·S3 Vectors 대상.

---

## 사용자 클래리피케이션 (실행 전 확인 필요)

> ✅ 6건 + 삭제 범위 모두 사용자 확인 완료 (2026-06-11).

- [x] **C1. 코드 디렉터리 구조** — `backend/` + `docsuri/` 패키지(모듈러 모놀리스, unit=모듈) 확정. **추가 지시**: 기존 파일 전부 삭제 — 범위 확인 결과 **`aidlc-docs/`·`.gitignore`·`.github/`만 유지**, 나머지(AGENTS.md·README·Sprint-Backlog*·app/·demo/·web/·static/·db/ 등) 전부 삭제. README는 새로 작성. (git 이력으로 복구 가능)
- [x] **C2. 어댑터 모드** — **mock 우선 + 실 AWS 어댑터 병행** 확정. 환경 변수로 선택, AWS 통합 테스트는 자격 증명 없으면 skip.
- [x] **C3. 시드 코퍼스** — **arXiv 실제 수집** 확정: 수집 스크립트 + `data/corpus_seed.json` fixture. 인용수는 Semantic Scholar 배치 API 시도, 실패 시 결정적 placeholder + 표기.
- [x] **C4. Glossary 시드** — **50개 초안을 내가 작성** 확정, 파일에 "팀 검토 필요" 표시.
- [x] **C5. 패키지 관리** — **uv + pyproject.toml** 확정 (uv 미설치 환경 대비 pip 호환 유지).
- [x] **C6. 커밋 전략** — **새 브랜치 분기** 확정: `feature/aidlc-construction-u0-foundation` (현 브랜치에서 분기, stacked PR — base = `feature/aidlc-construction-component-model`).

---

## 실행 단계 (승인 후 진행)

### Part A — 골격

- [x] **A1. 프로젝트 골격** — `backend/` + pyproject(uv) + `.env.example` + README + 루트 README 신규 작성 완료.
- [x] **A2. 포트 인터페이스 + DTO** — `docsuri/u0/ports.py`: 포트 7종(Protocol) + DTO 8종(pydantic). **시그니처 임의 변경 0건** 확인.
- [x] **A3. 설정 로딩** — `docsuri/u0/config.py`: 도쿄 리전·모델 ID·S3 Vectors 버킷/인덱스·테이블·상한, mock/aws 모드 검증.

### Part B — 어댑터

- [x] **B1. Mock 어댑터 7종** — `adapters/mock.py`: 결정적 임베딩·코퍼스 검색(연도·분야 필터)·한국어 canned LLM(페르소나 톤 분기)·시간 주입식 TTL 캐시·ListTelemetry·Glossary fixture·Citation fixture·익명 세션(URL 직렬화 왕복).
- [x] **B2. AWS 어댑터** — `adapters/aws.py`: Bedrock InvokeModel(Cohere v3)·Converse(`global.` Haiku 4.5)·**S3 Vectors query_vectors 직접 조회**(KB Retrieve는 텍스트 전용이라 search(vec,…) 시그니처와 부정합 — ADR-D2 결과 3의 문서화된 직접 API 경로 채택, 적재는 KB 관리)·DynamoDB TTL 캐시·Glossary·비용 누적·CloudWatch EMF. 실호출 검증은 환경 구축 라운드(ADR §14).
- [x] **B3. CostGuard + HttpClientPolicy** — **하드 거부 확정(사용자, 2026-06-11)**: 상한 도달 시 한국어 안내와 함께 예외. 백오프 1·2·4s + 4회차 한국어 알림.
- [x] **B4. CitationApi** — Semantic Scholar 1-hop + 24h 캐시 + 실패 시 빈 결과 폴백(R4).

### Part C — 정적 자산

- [x] **C-A1. 시드 코퍼스** — `scripts/build_corpus.py` 실행: **arXiv 실수집 100편 저장**. Semantic Scholar 배치는 거부(레이트 리밋) → 인용수는 결정적 placeholder, 파일에 `citations_source` 표기 (재실행으로 보강 가능).
- [x] **C-A2. Glossary 시드** — `data/glossary_seed.json` 50개 초안 작성, "팀 검토 필요" 표시.

### Part D — 검증 (U0 §6과 1:1)

- [x] **D1. pytest 스위트** — **14/14 통과** (빌드 가능 6항목 + 필터·페르소나 톤·URL 왕복·용어집·인용·CostGuard·백오프).
- [x] **D2. 시연 스크립트** — `scripts/u0_demo.py` 실행: **6/6 통과** (mock 모드, 자격 증명 불필요).
- [x] **D3. 비용 시뮬 보고** — ADR §13 참조로 닫음 (월 ~$45 ≤ $50) + 데모 출력에 누적치 표시.
- [x] **D4. U0 §6 체크리스트 갱신** — 사용자 승인 (2026-06-11: "검사 되면 통과") → unit-u0-foundation.md §6 6항목 [x] 처리 + 검증 출처 주석.
- [ ] **D5. 코드 리뷰** — 사용자 지시 (2026-06-11): **리뷰는 별도 PR에서 문서로 작성** → `aidlc-docs/reviews/u0-code-review.md` (stacked PR) 진행 중.

---

## 범위 밖 (Out of Scope)

- U1~U4 도메인 로직·HTTP 엔드포인트 (다음 라운드 — U0는 포트 라이브러리 + 시연).
- 배포·IaC(SAM/CDK)·Lambda 패키징 — 환경 구축 라운드로 분리 (ADR §14 검증 4건 포함).
- CI 구성 — 데모 단계 정책상 없음. 테스트는 로컬 pytest.
- 프론트엔드(Next.js) — U1 진입 시.
