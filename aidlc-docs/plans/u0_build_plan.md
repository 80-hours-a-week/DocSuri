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

- [ ] **A1. 프로젝트 골격** — `backend/` + `pyproject.toml`(Python 3.12, fastapi·boto3·httpx·pydantic·pytest) + `.env.example`([NFR-SEC-03](../requirements/nfr.md#nfr-sec-03) — 키 평문 금지) + README(U0 §6 시연 방법).
- [ ] **A2. 포트 인터페이스 + DTO** — `docsuri/u0/ports.py`: [component-model §2](../design-artifacts/component-model.md) 시그니처 그대로 7개 포트(Protocol) + `PaperHit`·`Completion`·`KoTranslation` 등 DTO(pydantic). **시그니처 임의 변경 0건** — 변경 필요 시 중단하고 사용자 확인(U0 §8 변경 정책).
- [ ] **A3. 설정 로딩** — `docsuri/u0/config.py`: 환경 변수(리전 ap-northeast-1, 모델 ID, 테이블명, 어댑터 모드 mock/aws), 시작 시 검증.

### Part B — 어댑터

- [ ] **B1. Mock 어댑터 7종** — `docsuri/u0/adapters/mock/`: 결정적 임베딩(해시 기반 vector) · 코퍼스 fixture 검색(필터 지원) · canned 한국어 LLM 응답(페르소나별 톤 분기) · **시간 주입식** in-memory TTL 캐시(25h 경과 시뮬 가능) · JSONL Telemetry · Glossary fixture · Citation fixture.
- [ ] **B2. AWS 어댑터** — `docsuri/u0/adapters/aws/`: Bedrock InvokeModel(Cohere v3 임베딩) · Bedrock Converse(`global.` Haiku 4.5) · KB Retrieve(메타데이터 필터) · DynamoDB TTL 캐시 · DynamoDB Glossary · CloudWatch EMF Telemetry — ADR §12 매핑 1:1. 자격 증명 없으면 통합 테스트 자동 skip.
- [ ] **B3. CostGuard + HttpClientPolicy** — 월 누적·상한 검사(거부 정책은 실행 중 사용자 확인 1회) · httpx 지수 백오프 1·2·4초 최대 3회([NFR-NET-02](../requirements/nfr.md#nfr-net-02)).
- [ ] **B4. CitationApi** — Semantic Scholar oneHop + 캐시(24h) + 폴백(스테일 허용 → 빈 상태) — [R4](../story-artifacts/handoff.md#r-4) 대응.

### Part C — 정적 자산

- [ ] **C-A1. 시드 코퍼스** — 수집 스크립트(`scripts/build_corpus.py`) + `data/corpus_seed.json` (100편, 제목·저자·연도·인용수·분야 태그·초록).
- [ ] **C-A2. Glossary 시드** — `data/glossary_seed.json` (50개 초안, 팀 검토 표시).

### Part D — 검증 (U0 §6과 1:1)

- [ ] **D1. pytest 스위트** — ① embed→vector ② search(v, k=5)→PaperHit 5건 ③ complete(persona='pro', budget=2000)→한국어 200~400자 ④ 캐시 set→25h 후 miss(시간 주입) ⑤ Telemetry 출력에 latency·tokens·cache_hit 키 ⑥ CostGuard 상한 거부.
- [ ] **D2. 시연 스크립트** — `scripts/u0_demo.py`: U0 §6 체크리스트를 순서대로 실행·출력 (mock 모드, 자격 증명 불필요).
- [ ] **D3. 비용 시뮬 보고** — [ADR §13](../design-artifacts/architecture_decision_record.md)이 이미 충족(월 ~$45) — U0 §6 마지막 항목은 참조로 닫음.
- [ ] **D4. U0 §6 체크리스트 갱신** — unit-u0-foundation.md의 빌드 가능 정의 체크박스를 갱신할지 사용자 확인 (동결 문서 — handoff §6 절차 대상 여부 포함).
- [ ] **D5. 사용자 최종 리뷰** — 코드·테스트 결과 제출, 피드백 반영, 커밋(C6 전략대로).

---

## 범위 밖 (Out of Scope)

- U1~U4 도메인 로직·HTTP 엔드포인트 (다음 라운드 — U0는 포트 라이브러리 + 시연).
- 배포·IaC(SAM/CDK)·Lambda 패키징 — 환경 구축 라운드로 분리 (ADR §14 검증 4건 포함).
- CI 구성 — 데모 단계 정책상 없음. 테스트는 로컬 pytest.
- 프론트엔드(Next.js) — U1 진입 시.
