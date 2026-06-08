# 01. 논문 검색 & 수집 (Paper Search & Ingest)

> 자연어/키워드 쿼리 → 복수 학술 DB 동시 검색 → 메타데이터·초록 수신 → 사용자가 고른 논문의 PDF 다운로드 → 청크화 후 벡터DB에 임베딩까지 수행하는 **모든 후속 기능의 토대**.

---

## 1. 핵심 요소

- **검색 컨텍스트 다양화**: 단일 키워드를 (a) 동의어/약어 확장, (b) 분야 필터, (c) 시기 필터, (d) 저자/기관 필터로 변환해 여러 쿼리 변형을 동시에 발사.
- **다중 학술 DB 라우팅**: arXiv / Semantic Scholar / OpenAlex / Crossref / PubMed 등 각자 다른 쿼리 문법을 한 추상화 레이어가 흡수.
- **DB별 쿼리 문법 RAG**: 각 DB의 공식 문법(예: arXiv의 `cat:cs.CL AND ti:"…"`, Semantic Scholar의 `fields`/`limit`/`year`)을 마크다운으로 정리 → 자체 RAG에 적재 → 에이전트가 쿼리 생성 시 참조.
- **결과 합성 + 재정렬**: DB별 결과를 (DOI/external_id로) dedupe → 임베딩 reranker로 사용자 쿼리에 대한 의미 유사도 정렬.
- **2단계 UX 분기**: 사용자가 결과 행 단위로 "초록만 본다" vs "PDF 전문 요약을 본다"를 선택.
- **PDF 인제스트**: 선택 시 PDF 다운로드 → GROBID로 섹션/문단/문장 구조화 → `(section_id, page, char_offset)` anchor 부여 → 청크 임베딩 → 벡터 DB 저장.

---

## 2. 주요 문제

- **DB별 쿼리 문법 상이성**: 동일 의도를 5개 DB에 정확히 옮기는 비용. → RAG 기반 쿼리 합성으로 완화하되, 실패 시 fallback 필요.
- **Rate limit & 인증**: Semantic Scholar는 무인증 호출이 분당 100회로 제한, PubMed E-utils는 초당 3회. 큰 결과셋 수집 시 backoff 필수.
- **PDF 접근권**: 비-OA(Open Access) 논문은 paywall. Unpaywall API로 OA 사본을 우선 탐색해야 함.
- **중복 제거**: 동일 논문이 arXiv preprint와 학회판으로 둘 다 잡힘. DOI 우선 → arXiv ID → title+author hash 순으로 dedupe.
- **PDF 파싱 정확도**: GROBID도 수식·표·다단 레이아웃에서 오류 발생. 청크 경계가 문장 중간을 가르면 임베딩 품질 하락.
- **저작권/라이선스**: 다운로드된 PDF의 영속 저장은 라이선스 위반 가능. 세션 범위 in-memory만 안전(AGENTS.md §4.2 정책 일치).
- **다국어**: 비영어 논문(중국어/일본어/한국어) 메타데이터를 어떻게 검색에 포함시킬지.

---

## 3. 파이프라인 설계 & 기술 스택

```
사용자 쿼리
    │
    ▼
┌────────────────────┐
│ Query Normalizer   │  (LLM + 검색 컨텍스트 다양화)
│  - 동의어 확장      │
│  - 분야/시기 필터   │
└─────────┬──────────┘
          │ canonical query
          ▼
┌────────────────────┐    DB-syntax RAG
│ Multi-DB Router    │ ───────────────►  (md docs)
│  - DB별 쿼리 변환  │   ◄───────────
└─────────┬──────────┘
          │ parallel calls
          ▼
┌──────────┬──────────┬──────────┬──────────┐
│ arXiv    │ S2       │ OpenAlex │ Crossref │  (asyncio.gather)
└────┬─────┴────┬─────┴────┬─────┴────┬─────┘
     └──────────┴──────────┴──────────┘
                    │
                    ▼
┌────────────────────┐
│ Dedupe + Merge     │  (DOI → arXivID → title-hash)
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Embedding Reranker │  (text-embedding-3-large)
└─────────┬──────────┘
          │ top-K
          ▼
┌────────────────────┐
│ Result UI          │  (초록 보기 | PDF 요약 보기)
└─────────┬──────────┘
          │ user picks paper
          ▼
┌────────────────────┐
│ PDF Fetcher        │  (Unpaywall → 직접 URL → 대안)
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ GROBID Parser      │  (section/para/sentence + anchor)
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Chunker + Embedder │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Vector DB Insert   │  (Qdrant / pgvector)
└────────────────────┘
```

### 기술 스택

| 레이어 | 선택 | 이유 |
|---|---|---|
| 쿼리 정규화 | Claude Haiku | 저비용·저레이턴시, 동의어 확장 충분 |
| 외부 API SDK | `arxiv`, `semanticscholar`, `pyalex` | 공식/준공식 파이썬 클라이언트 존재 |
| 쿼리 RAG | 자체 벡터 인덱스 (Qdrant) | 5개 DB 문법 md 파일 임베딩, 검색 |
| HTTP | `httpx` (async) + `tenacity` (retry) | rate limit 대응 |
| PDF 가져오기 | Unpaywall API + `httpx` | OA 사본 우선 탐색 |
| PDF 파싱 | GROBID (Docker) | 학술 PDF 구조 인식 표준 |
| 임베딩 | `text-embedding-3-large` 또는 `voyage-3` | 학술 도메인 성능 비교 후 선택 |
| 벡터 DB | Qdrant (셀프호스트) | 메타데이터 필터링·payload 강력 |
| 잡 큐 | Celery + Redis | PDF 파싱 비동기화 |
| 캐시 | Redis (24h TTL) | 동일 쿼리 재호출 방지 (`AGENTS.md §4.1` 준수) |

---

## 4. 차별화 포인트

- **쿼리 문법 RAG 자체화**: 시중 대부분의 학술 검색 도구는 단일 DB나 단순 페더레이션. DB별 고급 문법(부울/필드/날짜)을 RAG에 넣어 *에이전트가 적절히 활용*하는 접근은 드묾.
- **초록 vs 전문요약 분기 UX**: 검색 결과 단계에서 사용자가 "여기까지만 볼지" 결정할 수 있어 PDF 파싱 비용을 사용자 의도와 정렬.
- **anchor 보존 청킹**: 단순 fixed-size 청킹이 아니라, GROBID의 섹션/문단 경계를 우선 존중 → 후속 요약/번역에서 `[§4.2 ¶3]` 형식 인용이 자연스럽게 작동.

---

## 5. 위험 요소

- **API 정책 변경**: Semantic Scholar는 2024년 무인증 호출 제한을 강화. 사용량 폭증 시 API 키 신청 필요 (학술 기관 인증 필수).
- **저작권 클레임**: 출판사가 paywall PDF의 의도치 않은 다운로드/배포를 문제 삼을 수 있음. 영속 저장 금지 + 사용자별 격리 + ToS 게시 필수.
- **쿼리 폭발**: "검색 컨텍스트 다양화"가 과도해지면 한 사용자 쿼리가 50개 DB 호출로 증폭, rate limit 즉시 소진.
- **GROBID 의존성**: GROBID는 Java 기반 무거운 서비스(~2GB 메모리). 가벼운 대안(`unstructured`, `pymupdf`)은 정확도 trade-off.
- **벡터 DB 운영비**: 사용자가 늘면 임베딩 저장량이 선형 증가. 청크당 ~3KB × 평균 200청크/논문 = 논문당 ~600KB. 10만 논문 = 60GB 인덱스.

---

## 6. 예상 비용

### 초기 (MVP, 사용자 100명 / 월간 검색 1만 회)

| 항목 | 단가 | 월 비용 |
|---|---|---|
| 외부 학술 API | 무료 티어 | $0 |
| Claude Haiku (쿼리 정규화) | $0.25/1M in, $1.25/1M out | ~$5 |
| 임베딩 (검색 reranker용) | $0.13/1M tokens (text-embedding-3-large) | ~$20 |
| GROBID 호스팅 (단일 인스턴스) | $20/월 (DO 4GB droplet) | $20 |
| Qdrant 셀프호스트 | $40/월 (8GB instance) | $40 |
| Redis (캐시) | $15/월 | $15 |
| **합계 (MVP)** | | **~$100/월** |

### 스케일업 (사용자 1만 명 / 월간 검색 100만 회)

| 항목 | 월 비용 |
|---|---|
| API 키 (S2 paid tier 또는 학술 인증) | ~$0 (학술 free) ~ $500 (commercial) |
| LLM (쿼리 정규화) | ~$500 |
| 임베딩 | ~$2,000 |
| GROBID (k8s 3 replicas) | ~$200 |
| Qdrant (managed, 100GB) | ~$300 |
| Redis (managed) | ~$100 |
| **합계** | **~$3,100~$3,600/월** |

> 비용 변동의 가장 큰 요인은 **PDF 파싱·임베딩 처리량**. 사용자 행동(검색만 vs 실제 PDF 처리)에 따라 2~3배 폭이 발생.
