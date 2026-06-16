# U2 Discovery — Code Generation 요약 (mock-first)

**단계**: CONSTRUCTION → Code Generation (Part 2 완료) · **유닛**: U2 Discovery · **트랙**: Track 3(@kyjness) · **일자**: 2026-06-16
**근거**: `construction/plans/u2-discovery-code-generation-plan.md`(승인) · FD/NFR Req/NFR Design 산출물
**상태**: ✅ 생성 완료 · **테스트 27 passed · ruff clean**

> 본 문서는 산출 코드의 **요약(마크다운)**이다. 애플리케이션 코드는 `backend/modules/discovery/`에 있다(aidlc-docs/ 아님).

---

## 생성 위치
- **애플리케이션 코드**: `backend/modules/discovery/` (Track 3 클린 레인)
- **문서**: 본 디렉터리(`aidlc-docs/construction/u2-discovery/code/`)

## 생성 파일 (Step 1~10)

| 영역 | 파일 | 책임 | 트레이스 |
|---|---|---|---|
| 구조 | `pyproject.toml` | 모듈 로컬(uv) — docsuri-shared path dep·pytest·hypothesis·api extra(fastapi) | CG-1 |
| 도메인 | `domain/models.py` | 내부 엔티티(NormalizedQuery·QueryPlan·Candidate·RankedResults·DegradeMode…) | — |
| 도메인 | `domain/validator.py` | 검증·NFC 정규화(다국어) | FR-1·SEC-5·BR-1/2·**PBT-02** |
| 도메인 | `domain/expander.py` | 임베딩(search_query)+lexical 확장; LLM 재작성 없음 | FR-2·BR-3·Q1=A |
| 도메인 | `domain/retriever.py` | k-NN∥BM25 → RRF → PaperId 디덥 | FR-2·BR-4·**PBT-07**·Q2=A |
| 도메인 | `domain/ranker.py` | baseline 점수순 상위 N=20 | FR-3·BR-5·**PBT-03**·Q3/Q10=A |
| 도메인 | `domain/grounding_adapter.py` | to_grounding_input/map_decision (**enforce 미호출**) | FR-5·BR-7/8·**INV-1** |
| 도메인 | `domain/assembler.py` | 카드 7필드·종단 상태·SEC-9 | FR-4/11·BR-6/9/15·**PBT-09**·INV-2 |
| 포트 | `ports/search_ports.py` | Embedding/VectorStore/Lexical/EventPublisher + 격리 예외 | RES-9·NFR-R2 |
| 캐시 | `cache/embedding_cache.py` | read-through·TTL 필수 | NFR-P1/C1·TD-U2-7 |
| 서비스 | `service/orchestrator.py` | 파이프라인(plan_and_retrieve/finalize)·degrade 매트릭스·비차단 발행 | 전 스토리·BR-11/13/14·INV-1/3 |
| API | `api/gateway_seam.py` | **단일 enforce invocation**(게이트웨이 대역) | INV-1 |
| API | `api/router.py` | thin FastAPI 라우터·fail-closed 핸들러 | SEC-15·⏳FastAPI |
| mock | `mocks/{fixtures,adapters,port_stubs,wiring}.py` | KO↔EN cross-lingual+QT-2 픽스처·mock 어댑터·U6 스텁·빌더 | MR-1~4·TD-3 |
| 테스트 | `tests/test_*` | PBT-02/03/07/09·종단 상태·degrade·RES-12 폴트 인젝션 | QT-3/4 |

## 핵심 설계 준수
- **INV-1(단일 근거화 게이트)**: orchestrator(도메인 코어)는 `enforce`를 호출하지 않는다. `api/gateway_seam.run_search`(U6 게이트웨이 대역)가 `plan_and_retrieve`와 `finalize` 사이에서 주입된 후크로 단일 호출.
- **INV-2(SEC-9)**: 카드는 7필드(`title·authors·year·arxivId·abstractSnippet·relevance·arxivUrl`)만; raw/RRF 점수·vector·chunkId 비노출. (테스트가 카드 키 집합 검증.)
- **INV-3(fail-closed)**: 인덱스 장애→`SearchUnavailable`(503 일반화); 검증 실패→ValidationErrorDTO. 빈 성공 페이지 금지(무매치→AbstainDTO).
- **cross-lingual(TD-3)**: mock 임베딩이 KO/EN 동의어를 동일 차원에 매핑 → 한국어 질의가 영어 논문 검색(테스트 검증). lexical-only(BM25)는 비-cross-lingual이라 한국어는 기권.
- **fail-fast(Q1)**: 임베딩 장애→lexical 폴백(저하), 인덱스 장애→fail-closed.

## 보안/복원력 준수 요약 (FD/NFR 고도)
- **SEC-5**(검증)·**SEC-9**(카드 7필드·일반화 에러)·**SEC-15**(fail-closed)·**SEC-3**(PII 로깅 금지 정책) = 반영(테스트 일부 검증).
- **SEC-8 인증·SEC-11 레이트리밋** = U6 게이트웨이 위임(U2 미구현, 경계 준수). **SEC-10 공급망** = backend 공유 CI(NFR Design).
- **RES-9/NFR-R2**(타임아웃·서킷·폴백) = 정책·폴백 경로 구현(수치는 Infra). **RES-12** = 폴트 인젝션 테스트.
- **PBT-02/03/07/09** = 차단성 속성 전부 테스트(Hypothesis).

## 검증
```
cd backend/modules/discovery && uv run pytest          # 27 passed
uv run ruff check src tests                              # All checks passed
```

## mock → real 전환 (후속)
- `ports/search_ports.py` 인터페이스 뒤 mock(`mocks/adapters.py`)을 real(OpenSearch opensearch-py·Bedrock boto3)로 교체. 계약(`SearchResponse`)·도메인 로직 불변(MR-4).
- U6 포트 스텁(`mocks/port_stubs.py`)은 U6 실구현으로 교체(근거화·비용·관측성 단일 권위).
- FastAPI/배포·캐시 스토어·수치는 app-shell 합의·Infra Design.
