# CLAUDE.md — domain/papers 규칙

## 검색 파이프라인 흐름 (MultiDBRouter.search())

```
1. normalize()          — sanitization + Claude Haiku 쿼리 확장
2. Redis 캐시 체크      — 히트 시 즉시 반환
3. asyncio.gather()     — 5개 어댑터 병렬 팬아웃
4. pgvector 검색        — 의미 기반 검색 병렬 수행
5. dedupe               — DOI → arxivID → title-hash 3단 fallback
6. RRF(k=60) 병합       — 소스별 순위 기반 점수 병합
7. Redis 캐시 저장      — TTL 1h
8. BackgroundTasks 등록 — 신규 논문 임베딩 생성만
```

순서 변경 금지.
1번(normalize/sanitize)은 LLM·외부 소스 전달 전 반드시 먼저 실행.
2번 캐시 체크는 LLM 호출(3번) 전에 위치 — 중복 호출 방지.

## 논문 소스 목록 (5개 고정)

```python
PAPER_SOURCES = [
    "arxiv",            # 프리프린트
    "semantic_scholar", # 인용 관계 포함
    "openalex",         # 일반 학술 검색
    "pubmed",           # 의학·생명과학
    "crossref",         # DOI 기반 검색
]
```

각 소스는 독립 Circuit Breaker.
Open 상태면 해당 소스 스킵, 나머지로 결과 구성.
모든 소스 CB Open → 빈 리스트 반환 (503 에러, 200 아님).
CrossRef는 DOI 기반 조회에 우선 활용.

## SearchAdapter 구현 패턴

ArxivAdapter를 기준으로 모든 어댑터를 동일한 패턴으로 구현한다.

```python
class CrossRefAdapter:
    source = "crossref"

    def __init__(self, client: CrossRefClient | None = None) -> None:
        self._client = client or CrossRefClient()

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        """CrossRef API 검색.

        Time: O(N) where N=결과 수
        Edge: DOI 없는 결과 → title-hash fallback dedupe 사용
        """
        query = nq.for_crossref()
        entries = await self._client.search(query, limit=limit)
        return [_to_summary(e) for e in entries]

    async def healthcheck(self) -> bool:
        return await self._client.healthcheck()
```

`_to_summary()` 헬퍼는 어댑터마다 별도 정의.
도메인 모델(PaperSummary)로 변환만 담당, 비즈니스 로직 금지.

## NormalizedQuery 소스별 메서드

새 소스 추가 시 normalizer.py의 NormalizedQuery에 메서드를 추가한다.

```python
class NormalizedQuery:
    def for_arxiv(self) -> str: ...
    def for_semantic_scholar(self) -> str: ...
    def for_openalex(self) -> str: ...
    def for_pubmed(self) -> str: ...
    def for_crossref(self) -> str: ...  # 신규 추가
```

## normalizer.py sanitization 규칙

```python
async def normalize(query: str, expand: bool = False) -> NormalizedQuery:
    # 1. sanitize 먼저 — LLM·외부 소스 전달 전 필수
    clean = _sanitize(query)
    # HTML 이스케이프, 길이 제한 512자, 허용 문자 필터 (영문/한글/숫자/공백)

    # 2. 캐시 확인 후 LLM 확장
    if expand:
        cached = await redis.get(f"expand:{_hash(clean)}")
        if cached:
            return NormalizedQuery.from_cache(cached)
        expanded = await _expand_with_llm(clean)
        await redis.set(f"expand:{_hash(clean)}", expanded, ex=21600)  # TTL 6h
        return expanded

    return NormalizedQuery(raw=clean)
```

LLM 확장 실패 시 폴백: 원본 sanitized 쿼리로 진행.
검색 자체는 LLM 실패와 무관하게 동작해야 한다.

LLM 프롬프트 구조:
```python
system = "학술 논문 검색 쿼리를 확장한다. JSON만 반환. 설명 텍스트 금지."
user = f"<query>{clean}</query>\n{{\"keywords\": [...], \"english\": [...], \"synonyms\": [...]}}"
# 검색된 문서 외 내용 생성 금지 — system에 명시
```

## dedupe 규칙

```python
def dedupe(papers: list[PaperSummary]) -> list[PaperSummary]:
    """DOI → arxivID → title-hash 3단 fallback 중복 제거.

    Time: O(N), Space: O(N)
    Edge: DOI/arxivID 없는 논문 → title+year 해시로 fallback
    """
    seen: set[str] = set()
    result = []
    for p in papers:
        key = p.doi or p.arxiv_id or _title_hash(p.title, p.year)
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result
```

## RRF 병합 (k=60 고정)

```python
def rrf_merge(
    ranked_lists: list[list[PaperSummary]], k: int = 60
) -> list[PaperSummary]:
    """Reciprocal Rank Fusion 점수 병합.

    Time: O(N*M), Space: O(N*M)
    Edge: ranked_lists 빈 리스트(전체 CB Open) → 빈 결과 반환
    k=60: 변경 금지. 상위 결과 간 점수 차이 완화 표준값.
    """
    scores: dict[str, float] = defaultdict(float)
    papers: dict[str, PaperSummary] = {}
    for ranked in ranked_lists:
        for rank, paper in enumerate(ranked, start=1):
            key = paper.doi or paper.arxiv_id or paper.id
            scores[key] += 1.0 / (k + rank)
            papers[key] = paper
    return sorted(
        papers.values(),
        key=lambda p: scores[p.doi or p.arxiv_id or p.id],
        reverse=True,
    )
```

소스별 점수 스케일이 달라 단순 합산 금지.

## pgvector 검색 패턴

```python
# infra/storage/ 에서 구현
SELECT id, title, abstract,
       1 - (embedding <=> $1::vector) AS score
FROM papers
WHERE ($2::int IS NULL OR year >= $2)
ORDER BY embedding <=> $1::vector
LIMIT $3;
```

임베딩 모델: `text-embedding-3-large` (3072차원)
pgvector 인덱스: hnsw (Alembic 마이그레이션으로 생성)
모델 변경 시 마이그레이션으로 컬럼 차원 재설정 + 전체 재임베딩 필수.

## 논문 upsert 규칙

```python
INSERT INTO papers (doi, title, abstract, year, source, ...)
VALUES (...)
ON CONFLICT (doi) DO UPDATE SET
    title = EXCLUDED.title,
    updated_at = NOW()
WHERE papers.updated_at < EXCLUDED.updated_at;
```

DOI 없는 논문: `(title, year, source)` 조합을 unique key로 사용.
멱등 보장: 동일 논문 중복 삽입 시 ON CONFLICT로 처리.

## 커서 페이지네이션

```python
async def list_papers(cursor: str | None, limit: int = 20):
    """커서 기반 페이지네이션.

    OFFSET/LIMIT 금지 — 논문 추가 시 동일 레코드 중복/누락 가능.
    Time: O(log N) with index on id
    """
    where = "WHERE id > $1" if cursor else ""
    rows = await db.fetch(
        f"SELECT * FROM papers {where} ORDER BY id LIMIT $2",
        cursor, limit + 1,
    )
    has_next = len(rows) > limit
    next_cursor = str(rows[limit - 1].id) if has_next else None
    return rows[:limit], next_cursor
```