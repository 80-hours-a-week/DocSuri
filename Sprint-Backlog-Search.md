## 스프린트 백로그 — 01a. 논문 검색 (Paper Search)

> 자연어/키워드 쿼리 → 다중 학술 DB 라우팅 → dedupe·rerank → 검색 결과 표시.
> **PDF 인입(GROBID → 청크 → 벡터DB)은 #01b Ingest 백로그로 분리.** 사용자가 "PDF 요약 보기" 선택 시 #01b로 트리거.
> **`infra/embedding` Owner 기능** — #01b 인입과 공유.
> 모듈 경계: `domain/papers/` (search-side) + `crosscutting/{ratelimit,audit}/` + `infra/{llm,vectordb,storage,embedding}/`.
> 출처: `feature-specs/01-paper-search-and-ingest.md` (전반부), AGENTS.md §3.2.

---

### Sprint 1 — Search MVP (단일 DB 검색 walking skeleton)

**Sprint 1 DoD:** arXiv 단일 DB로 자연어 쿼리 → 결과 목록 + 초록/PDF 분기 UI까지 동작.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/papers: Multi-DB Router 추상화 + arXiv 어댑터 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 모든 후속 행이 이 추상화에 의존 | Router interface + arXiv 어댑터 통합 테스트 5건 통과 |
| 2 | crosscutting/ratelimit: tenacity backoff + 분당/초당 quota 관리 (S2 100rpm, PubMed 3rps) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 외부 호출 안전망 우선 | 5xx/429 자동 재시도 + quota 초과 시 RetryError raise |
| 3 | domain/papers: Query Normalizer — Claude Haiku 호출, 동의어/분야/시기 필터 확장 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | LLM 호출 + 프롬프트 단순 | 동의어/필터 expand 10 unit 시나리오 통과 |
| 4 | domain/papers: DB-syntax RAG 인덱스 — 5개 DB 문법 md → Qdrant 자체 인덱스 (vectordb 베이스 설정 포함) | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 5 DB 문법 정리 + Qdrant 베이스 셋업 (#01b chunks collection이 이 위에 추가) | "arXiv 분야 검색" → `cat:cs.CL` 합성 검증 + Qdrant client healthcheck |
| 5 | frontend: 검색 결과 UI + 초록 vs PDF 요약 2단계 분기 ("PDF 요약" 클릭 → #01b 인입 트리거) | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 페이지 + 상태 + 분기 UX | 결과 카드 N건 + 초록/PDF 토글 + 빈/에러 상태 처리 + 인입 트리거 이벤트 발송 |

**Sprint 1 합계: 21 포인트**

---

### Sprint 2 — Multi-DB Federation + Embedding Owner

**Sprint 2 DoD:** 5 DB 합성 + DOI dedupe + 임베딩 reranker. 캐시 적중. **`infra/embedding` 어댑터가 #01b Sprint 2에 export 가능 상태.**

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/papers: Semantic Scholar / OpenAlex / Crossref / PubMed 어댑터 | 8 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 어댑터 + 각 API 인증·rate limit | 4 어댑터 각각 통합 테스트 통과 + auth/rate limit 검증 |
| 2 | **[Owner: infra/embedding]** domain/papers: 임베딩 reranker — text-embedding-3-large 어댑터 + cosine 정렬 (#01b 인입과 공유) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Owner 포트 — #01b Sprint 2부터 의존 | 어댑터 호출 + cosine 정렬 안정성 + #01b 호출 호환성 단위 테스트 |
| 3 | domain/papers: Dedupe (DOI → arXivID → title-hash) + Merge | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 알고리즘 단순 3단 fallback | 5 DB 잡힌 동일 논문 1건만 반환 + 정확도 95%+ |
| 4 | infra/storage: Redis 쿼리 캐시 24h TTL (AGENTS.md §4.1 캐시 정책 준수) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 표준 캐시 패턴 | 동일 쿼리 2회차 캐시 히트 로깅 + 24h 자동 만료 |

**Sprint 2 합계: 16 포인트**

---

### Sprint 3 — Search Hardening + Ops

**Sprint 3 DoD:** quota·감사 강제 + 5 DB 합성 회귀 통과 + SLO 대시보드/알림/runbook 출시.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | crosscutting/audit: 쿼리 폭발 방지 메트릭 + 사용자별 quota — AGENTS.md §4.2/§4.5 정책 준수 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 로깅 + 알림 + 메트릭 | quota 초과 시 429 응답 + Prometheus 메트릭 노출 |
| 2 | tests: 5개 DB 쿼리 합성 통합 + dedupe 정확도 + Query Normalizer flake | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 통합 + flaky API 핸들링 | 2 시드 시나리오 CI 통합 + flake율 < 1% |
| 3 | **[Ops]** crosscutting/ops: SLO(p95 검색 < 500ms, DB error < 1%) + S2 rate limit 잔여 + Redis 캐시 히트율 + runbook (DB 장애 fallback) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 운영 가시성 + 사고 대응 | Grafana 3 패널 + Alertmanager 2 룰 + `/runbooks/search-db-failure.md` |

**Sprint 3 합계: 11 포인트**

**전체 합계: 48 포인트**
