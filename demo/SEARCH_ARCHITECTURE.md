# 검색 파이프라인 아키텍처

## 전체 흐름

```
사용자 쿼리
    │
    ▼
POST /api/search
    │
    ▼
┌─────────────────────────────────────────────────┐
│  MultiDBRouter.search()                         │
│                                                 │
│  1. QueryNormalizer.normalize()                 │
│     ├─ 정제 (HTML 제거, 허용 문자만 필터링)           │
│     ├─ arXiv 카테고리 자동 감지                     │
│     └─ [expand=True] LLM 동의어 확장               │
│                                                 │
│  2. Redis 캐시 확인 (hit → 즉시 반환)               │
│                                                 │
│  3. 병렬 팬아웃 (동시 실행)                          │
│     ├─ ArxivAdapter        (Atom XML)           │
│     ├─ SemanticScholarAdapter  (Graph API)      │
│     ├─ OpenAlexAdapter     (Works API)          │
│     ├─ PubMedAdapter       (eSearch + eFetch)   │
│     └─ PgVector 시맨틱 검색  (cosine similarity) │
│                                                 │
│  4. RRF 병합 + 3단계 중복 제거                      │
│     └─ DOI → arXiv ID → title+year 해시          │
│                                                 │
│  5. CrossRef DOI 보강 (비동기, best-effort)        │
│                                                 │
│  6. Redis 캐시 저장 (TTL 3600s)                   │
│                                                 │
│  7. 백그라운드 태스크 등록                            │
│     └─ 새 논문만 임베딩 → pgvector upsert           │
└─────────────────────────────────────────────────┘
    │
    ▼
SearchResponse (results, normalized, expanded, count)
```

---

## 파일 구조

```
app/
├── api/
│   └── routes_search.py          # HTTP 엔드포인트
├── domain/papers/
│   ├── search.py                 # 핵심 파이프라인 (MultiDBRouter, 어댑터)
│   ├── normalizer.py             # 쿼리 정규화 + LLM 확장
│   └── models.py                 # PaperSummary, Anchor
├── infra/
│   ├── http/
│   │   ├── arxiv.py              # arXiv API 클라이언트
│   │   ├── semantic_scholar.py   # Semantic Scholar API 클라이언트
│   │   ├── openalex.py           # OpenAlex API 클라이언트
│   │   ├── crossref.py           # CrossRef API 클라이언트
│   │   └── pubmed.py             # PubMed (NCBI eUtils) 클라이언트
│   ├── storage/
│   │   ├── pgvector.py           # 벡터 DB (cosine similarity)
│   │   └── redis_cache.py        # 쿼리 결과 캐시
│   └── embedding/
│       └── openai.py             # text-embedding-3-large (3072-dim)
├── crosscutting/ratelimit/
│   ├── circuit_breaker.py        # 어댑터별 서킷 브레이커
│   └── backoff.py                # 토큰 버킷 + 지수 백오프 재시도
└── container.py                  # 의존성 주입 (lru_cache 팩토리)
```

---

## 핵심 컴포넌트

### MultiDBRouter (`search.py`)

| 역할 | 설명 |
|------|------|
| 쿼리 정규화 | `QueryNormalizer`에 위임 |
| 캐시 I/O | 진입 시 hit 확인, 종료 시 저장 |
| 병렬 팬아웃 | `asyncio.gather()` — 4개 어댑터 + pgvector 동시 실행 |
| 결과 병합 | `rrf_merge()` → `dedupe()` |
| DOI 보강 | CrossRef 병렬 직접 조회 |
| 백그라운드 임베딩 | `_register_bg_tasks()` → `_bg_embed_and_store()` |

### SearchAdapter (Protocol)

각 어댑터가 구현하는 인터페이스: `.search(nq: NormalizedQuery, limit: int) → list[PaperSummary]`

| 어댑터 | DB | 속도 제한 | 특이사항 |
|--------|-----|-----------|---------|
| `ArxivAdapter` | arXiv | 3 req/s | Atom XML 파싱 |
| `SemanticScholarAdapter` | S2 Graph API | 1 req/s | - |
| `OpenAlexAdapter` | OpenAlex Works | 10 req/s | inverted-index abstract 재구성 |
| `PubMedAdapter` | NCBI eUtils | 3 req/s (키 없을 때) | esearch → efetch 2단계 |
| `CrossRefAdapter` | CrossRef | 5 req/s | 팬아웃 제외, DOI 보강 전용 |

### RRF 병합 (`rrf_merge`, k=60)

```
score(paper) = Σ 1/(60 + rank_i)   for each adapter i that returned this paper
```

동일 논문 식별 우선순위: **DOI > arXiv ID > title+year 해시**

---

## 쿼리 정규화 (`normalizer.py`)

```
raw query
    │
    ├─ _sanitize()     → HTML 이스케이프, [a-zA-Z0-9가-힣 ] 필터
    ├─ _strip_punct()  → 특수문자 제거 (._- 제외)
    ├─ _detect_fields()→ 키워드 → arXiv 카테고리 매핑 (~12개 규칙)
    └─ [expand=True]   → LLM에 동의어 요청 → synonyms 필드 채움
    ↓
NormalizedQuery(raw, canonical, fields, synonyms, expanded)
```

각 어댑터용 쿼리 빌더:
- `for_arxiv()` → `(all:term1 OR all:term2) AND (cat:cs.CL OR ...)`
- `for_semantic_scholar()`, `for_openalex()`, `for_pubmed()`, `for_crossref()`

---

## 저장소 / 캐싱

### Redis (`redis_cache.py`)
- 캐시 키: `search:{sha256(canonical_query)}`
- TTL: 3600초
- REDIS_URL 없으면 no-op (graceful degradation)

### pgvector (`pgvector.py`)
- 테이블: `papers(id, title, abstract, year, embedding vector(3072))`
- 쿼리: `embedding <=> $1::vector` (cosine distance)
- DATABASE_URL 없으면 skip (graceful degradation)

### OpenAI Embeddings (`embedding/openai.py`)
- 모델: `text-embedding-3-large` (3072차원)
- 임베딩도 Redis에 별도 캐시: `embed:large:{sha256(text)}`

---

## 복원력 레이어

### 서킷 브레이커 (`circuit_breaker.py`)

```
CLOSED ──(5번 연속 실패)──▶ OPEN ──(30초 후)──▶ HALF-OPEN ──(성공)──▶ CLOSED
                                                      └──(실패)──▶ OPEN
```
- 어댑터별 독립 인스턴스
- OPEN 상태에서 호출 → `CircuitBreakerOpen` 예외 → 해당 어댑터 skip
- 모든 어댑터 실패 → `AllAdaptersFailedError` → HTTP 503

### 토큰 버킷 + 재시도 (`backoff.py`)
- 어댑터별 속도 제한 (토큰 버킷)
- 재시도 조건: `TransportError`, HTTP 429, HTTP 5xx (최대 3회, 지수 백오프)
- `TimeoutException`은 즉시 실패 (fast-fail)

---

## API

| 엔드포인트 | 메서드 | 요청 | 응답 |
|-----------|--------|------|------|
| `/api/search` | POST | `{query, limit(1-50), expand}` | `SearchResponse` |
| `/api/search/health` | GET | - | `SearchHealth` (어댑터별 상태) |

---

## 의존성 주입 (`container.py`)

환경변수에 따라 자동 선택:

| 컴포넌트 | 조건 |
|----------|------|
| LLM | `AWS_BEDROCK_REGION` → Bedrock / `ANTHROPIC_API_KEY` → Claude / 없으면 MockLLM |
| Embedding | `OPENAI_API_KEY` 필요 |
| pgvector | `DATABASE_URL` 필요 |
| Redis | `REDIS_URL` 필요 |

---

## 설계 원칙 요약

- **팬아웃 + RRF 병합**: 여러 DB를 병렬 조회해 단일 DB의 커버리지 한계 극복
- **3단계 중복 제거**: DOI > arXiv ID > title 해시 — 소스마다 ID 체계가 다를 때 대응
- **Graceful Degradation**: Redis, pgvector, OpenAI 키 없어도 검색 동작
- **백그라운드 임베딩**: 검색 응답 지연 없이 점진적으로 벡터 DB 구축
- **도메인 경계 유지**: `search.py`는 요약/번역 등 다른 도메인을 import하지 않음
