# Unit U0 — Foundation (공통 인프라)

> 참조: [`units_plan.md`](../../plans/units_plan.md) · [`epics.md`](../../requirements/epics.md) · [`nfr.md`](../../requirements/nfr.md) · [`handoff.md`](../../story-artifacts/handoff.md)

---

## 1. 정체성

- **ID**: U0
- **이름**: Foundation
- **미션 1줄**: 모든 도메인 unit(U1·U2·U3·U4)이 의존하는 *안정 인터페이스*(임베딩·LLM·캐시·익명 세션·관찰가능성)를 제공해, 도메인 unit이 결정의 *자세*가 아닌 *결과*만 가져다 쓰게 한다.
- **범위**:
  - **In**: 임베딩 클라이언트, LLM 게이트웨이, 캐시 어댑터, 익명 세션·필터 URL 직렬화, 관찰가능성 파이프라인, 학술 용어 사전 시드(50개)
  - **Out**: 도메인 비즈니스 로직(검색·요약·차별성·인용 트리). 비-MVP Epic 인프라(알림·재현성·영속 개인화) 비포함.

---

## 2. 포함 스토리

본 unit은 **인프라 unit**이므로 자체 user story를 갖지 않는다. 그러나 다음 스토리들의 *비기능 책임*을 모두 흡수한다.

| 흡수한 NFR 책임 | 출처 스토리 |
|---|---|
| LLM 호출 → [NFR-PERF-02](../../requirements/nfr.md#nfr-perf-02), [NFR-COST-01·02](../../requirements/nfr.md#nfr-cost-01) | [US-COMP-01](../../story-artifacts/user_stories.md#us-comp-01), [COMP-04](../../story-artifacts/user_stories.md#us-comp-04), [DIFF-01](../../story-artifacts/user_stories.md#us-diff-01), [DIFF-02](../../story-artifacts/user_stories.md#us-diff-02) |
| 임베딩 검색 → [NFR-PERF-01](../../requirements/nfr.md#nfr-perf-01), [NFR-MOBILE-03](../../requirements/nfr.md#nfr-mobile-03) | [US-DISC-01](../../story-artifacts/user_stories.md#us-disc-01), [DISC-03](../../story-artifacts/user_stories.md#us-disc-03), [DISC-04](../../story-artifacts/user_stories.md#us-disc-04) |
| 캐시 TTL → [NFR-DATA-03](../../requirements/nfr.md#nfr-data-03), [NFR-NET-04](../../requirements/nfr.md#nfr-net-04) | (모든 unit이 의존) |
| 익명 세션 → [NFR-SEC-01](../../requirements/nfr.md#nfr-sec-01) | (모든 unit이 의존) |
| 관찰가능성 → [NFR-OBS-01·02](../../requirements/nfr.md#nfr-obs-01) | (모든 unit이 의존) |

---

## 3. Cross-unit 의존 (인터페이스 계약)

### 입력 (외부 → U0)

| 출처 | 인터페이스 | 비고 |
|---|---|---|
| 운영자 | `CorpusIndex` (1회 빌드) | arXiv 메타데이터 + 임베딩 인덱스. [A1](../../story-artifacts/handoff.md#a-1) 가정. |
| 운영자 | `GlossarySeed` (50개) | [A6](../../story-artifacts/handoff.md#a-6) 가정. 학술 용어 정규 번역. |
| 외부 | LLM Provider API | [D4](../../story-artifacts/handoff.md#d-4) 결정 후 확정. |
| 외부 | Embedding Provider API | [D3](../../story-artifacts/handoff.md#d-3) 결정 후 확정. |
| 외부 | Semantic Scholar API | [A1](../../story-artifacts/handoff.md#a-1) 가정. [R4](../../story-artifacts/handoff.md#r-4) 위험 인지. |

### 출력 (U0 → U1·U2·U3·U4) — 본 unit의 **유일한 약속**

| 포트 이름 | 시그니처(개념) | 사용 unit |
|---|---|---|
| `EmbeddingPort` | `embed(text: str, lang: 'ko'\|'en') -> Vector` | U1, U3 |
| `EmbeddingPort.search` | `search(vec: Vector, k: int, filters?) -> [PaperHit]` | U1, U3 |
| `LlmPort` | `complete(prompt: str, persona: 'pro'\|'undergrad', budget_tokens: int) -> Completion` | U2, U3 |
| `CachePort` | `get(key) -> bytes\|None`, `set(key, value, ttl_s)` | U1, U2, U4 |
| `SessionPort` | `session() -> { anon_id, persona_mode, filters_url }` | U1~U4 (URL 직렬화 사용 시) |
| `Telemetry` | `record({op, latency_ms, tokens_in, tokens_out, cache_hit, persona})` | U1~U4 (모든 외부 호출) |
| `Glossary` | `lookup(term) -> KoTranslation?` | U2, U3 |
| `CitationApi` | `oneHop(paper_id) -> { outgoing: [PaperHit], incoming: [PaperHit] }` | U4 |

> **계약 안정성**: 위 포트 시그니처는 [`handoff.md §6`](../../story-artifacts/handoff.md) 변경 정책에 따른다. 변경 시 모든 의존 unit과 동기.

---

## 4. Cross-cutting NFRs

본 unit이 **시스템 전역에서 책임지는** NFR.

| NFR 키 | 책임 경계 |
|---|---|
| [NFR-PERF-01·02·03](../../requirements/nfr.md#nfr-perf-01) (데스크톱·WiFi 기준) | LLM/임베딩 호출 P95 측정·기록은 U0가, *비즈니스 응답 시간*은 호출 unit이 종합 책임 |
| [NFR-MOBILE-03](../../requirements/nfr.md#nfr-mobile-03) (4G 목표) | 동일 — U0는 *raw* 응답 시간만, *체감 시간*은 unit별 분리 |
| [NFR-DATA-03](../../requirements/nfr.md#nfr-data-03) (캐시 24h/7d), [NFR-NET-04](../../requirements/nfr.md#nfr-net-04) (오프라인 24h 읽기) | `CachePort`가 단일 정책 제공 — 호출 unit은 키만 결정 |
| [NFR-NET-01·02·03](../../requirements/nfr.md#nfr-net-01) | 데이터 절약·재시도·오프라인 빈 상태는 U0의 HTTP 클라이언트가 표준 제공 |
| [NFR-SEC-01·03](../../requirements/nfr.md#nfr-sec-01) (비로그인·환경 변수 키 관리) | `SessionPort` + 환경변수 로딩이 단일 진입 |
| [NFR-COST-01·02](../../requirements/nfr.md#nfr-cost-01) | LLM 비용 누적치는 U0의 `Telemetry`가 산정. *상한 가드*는 U0의 게이트웨이가 강제. |
| [NFR-OBS-01·02](../../requirements/nfr.md#nfr-obs-01) | 모든 외부 호출은 `Telemetry`로 자동 기록 |

---

## 5. 데이터·외부 의존 (본 unit이 닫는 결정)

본 unit이 *진입과 동시에* 닫아야 하는 [`handoff.md §4`](../../story-artifacts/handoff.md) Open Decisions.

- [D1](../../story-artifacts/handoff.md#d-1) **백엔드 언어/프레임워크** — `EmbeddingPort`/`LlmPort` 구현의 호스트 결정.
- [D2](../../story-artifacts/handoff.md#d-2) **임베딩 인덱스** — `EmbeddingPort.search` 구현(FAISS/pgvector/Chroma 중 택1).
- [D3](../../story-artifacts/handoff.md#d-3) **임베딩 모델** — `EmbeddingPort.embed` 구현.
- [D4](../../story-artifacts/handoff.md#d-4) **LLM 모델** — `LlmPort.complete` 구현. [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01) 시뮬레이션 동반.
- [D8](../../story-artifacts/handoff.md#d-8) **오프라인 캐시 메커니즘** — `CachePort`의 클라이언트측 구현.
- [D9](../../story-artifacts/handoff.md#d-9) **호스팅 환경** — U0 서비스의 배포 형태.
- [D10](../../story-artifacts/handoff.md#d-10) **관찰가능성 스택** — `Telemetry` 백엔드.

---

## 6. 빌드 가능 정의 (Definition of Buildable)

U0는 다음이 모두 작동할 때 *빌드 가능*하다 — 다른 unit 없이 단독 시연 가능.

> ✅ **6/6 통과** (2026-06-11, 사용자 승인으로 체크 갱신) — 검증: `backend/tests/test_u0_buildable.py`(pytest 14/14) + `backend/scripts/u0_demo.py`(6/6, mock 모드). 빌드 기록: [`u0_build_plan.md`](../../plans/u0_build_plan.md) · PR #14.

- [x] `EmbeddingPort.embed("transformer")` → 임의 vector 반환 (실모델 OR 결정적 mock) — *결정적 mock, 32차원*
- [x] `EmbeddingPort.search(v, k=5)` → 5개 `PaperHit` 반환 (시드 코퍼스 100편 기준) — *arXiv 실수집 100편*
- [x] `LlmPort.complete(prompt, persona='pro', budget=2000)` → 한국어 200~400자 응답 — *261자 확인*
- [x] `CachePort` 24h TTL 동작 시연 (set → 25h 후 miss) — *시간 주입식 시뮬레이션*
- [x] `Telemetry` 출력에 latency·토큰·캐시 적중 키가 존재 — *latency_ms·tokens_in/out·cache_hit*
- [x] [NFR-COST-01](../../requirements/nfr.md#nfr-cost-01) 시뮬레이션 — 데모 트래픽 가정 월 $50 이내인지 추정 보고서 — *[ADR §13](../architecture_decision_record.md): 월 ~$45 + CostGuard 하드 거부*

---

## 7. 미해결 위험 (본 unit이 닫는 위험)

- [R3](../../story-artifacts/handoff.md#r-3) **LLM 비용 변동성** — `LlmPort` 게이트웨이의 상한 가드·요약 입력 압축으로 흡수.
- [R4](../../story-artifacts/handoff.md#r-4) **인용 그래프 API 의존** — `CitationApi`에 *캐시 + 폴백* 적용 (U4가 사용).
- [R5](../../story-artifacts/handoff.md#r-5) **학술 용어 사전 수기 50개** — `Glossary` 인터페이스가 *사후 확장* 가능하도록 설계 (자동 시드 도구 후속 사이클).
- [R6](../../story-artifacts/handoff.md#r-6) **오프라인 24h 캐시** — `CachePort`의 클라이언트측 구현이 닫음.

---

## 8. 변경 정책

- **이 unit 단독 변경 가능**: 포트 *구현체* 교체 (예: pgvector → FAISS), `Telemetry` 백엔드 교체.
- **cross-unit 영향 발생**: 포트 *시그니처* 변경 (필드 추가/제거/타입 변경). 이 경우 모든 의존 unit의 인터페이스 합의 갱신 필요.
- **금지**: 도메인 로직(요약 톤 결정·차별성 노트 형식 등)을 U0에 박는 것. 도메인 로직은 호출 unit이 결정.
