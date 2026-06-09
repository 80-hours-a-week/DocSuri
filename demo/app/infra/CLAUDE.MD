# CLAUDE.md — app/infra 레이어 규칙

## infra 레이어 원칙

외부 시스템 클라이언트만 작성한다.
비즈니스 로직, 도메인 규칙 금지.
domain에서 infra 직접 import 금지 → container.py 주입 사용.

## 디렉토리 구조

```
infra/
├── embedding/              # 임베딩 생성 클라이언트
├── grobid/                 # PDF 파싱 (client.py, tei_parser.py)
├── http/                   # 논문 소스 HTTP 클라이언트
│   ├── arxiv.py            # 기존
│   ├── semantic_scholar.py # Sprint 2 신규
│   ├── openalex.py         # Sprint 2 신규
│   ├── pubmed.py           # Sprint 2 신규
│   └── crossref.py         # Sprint 2 신규 (DOI 기반)
├── llm/                    # LLM 클라이언트 (claude.py, protocol.py, cache_keys.py)
├── pdf/                    # PDF 파서
└── storage/                # DB, Redis, pgvector
```

## HTTP 클라이언트 공통 패턴

arxiv.py를 기준으로 모든 클라이언트를 동일한 패턴으로 구현한다.

```python
class CrossRefClient:
    """CrossRef API 클라이언트.

    Rate limit: 50 req/s (폴라이트 풀 사용 시 더 높음)
    Edge: DOI 없는 결과 포함 가능 → 어댑터에서 처리
    """
    TIMEOUT = 5.0                          # 고정, 변경 금지
    BASE_URL = "https://api.crossref.org"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        bucket: TokenBucket = _CROSSREF_BUCKET,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=self.TIMEOUT)
        self._owns_client = client is None
        self._bucket = bucket

    @RateLimitedRetry(max_attempts=3)
    async def _get(self, params: dict) -> dict:
        await self._bucket.acquire()
        resp = await self._client.get(self.BASE_URL + "/works", params=params)
        resp.raise_for_status()
        return resp.json()

    async def search(self, query: str, *, limit: int = 10) -> list[CrossRefEntry]:
        ...

    async def healthcheck(self) -> bool:
        ...

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
```

## Circuit Breaker 규칙

Circuit Breaker 클래스: `app/crosscutting/ratelimit/circuit_breaker.py`
예외 클래스: `CircuitBreakerOpen` (CB Open 상태에서 호출 시 발생)

**재시도(RateLimitedRetry)와 Circuit Breaker는 반드시 독립적으로 동작한다.**

재시도 로직 안에 CB 상태 확인 금지.
CB 안에 재시도 로직 포함 금지.

```python
# 금지 — 재시도 안에 CB 로직
@RateLimitedRetry(max_attempts=3)
async def search(self, ...):
    if self.cb.state == "open":   # CB를 재시도 안에서 확인 금지
        return []

# 허용 — CB는 어댑터 레벨, 재시도는 클라이언트 레벨에서 독립 동작
class CrossRefAdapter:
    async def search(self, nq, *, limit):
        async with self.cb:                      # CB: 어댑터 레벨
            return await self._client.search(...)  # 재시도: 클라이언트 내부
```

소스별 독립 CB 인스턴스 (container.py에서 생성):

```python
arxiv_cb         = CircuitBreaker(fail_max=5, reset_timeout=30)
semantic_cb      = CircuitBreaker(fail_max=5, reset_timeout=30)
openalex_cb      = CircuitBreaker(fail_max=5, reset_timeout=30)
pubmed_cb        = CircuitBreaker(fail_max=5, reset_timeout=30)
crossref_cb      = CircuitBreaker(fail_max=5, reset_timeout=30)
```

CB Open 상태: 해당 소스 스킵, 나머지 소스로 결과 구성.
전체 CB Open: 빈 리스트 반환 → 호출 레이어에서 503 처리.

## 재시도 정책

```python
# crosscutting/ratelimit/backoff.py 기존 패턴 사용
@RateLimitedRetry(max_attempts=3)
async def _get(self, ...):
    ...
```

재시도 횟수: 3회 (고정)
대기 시간: 지수 백오프 1s → 2s → 4s
재시도 대상: 타임아웃, 5xx
재시도 제외: 4xx (클라이언트 오류 — 재시도해도 동일 결과)
정책은 반드시 코드에 명시한다. "무제한" 또는 "정책 미정" 금지.

## SSRF 화이트리스트

외부 URL 서버 요청 전 반드시 crosscutting/verifier/port.py 통과.

```python
ALLOWED_DOMAINS = {
    "export.arxiv.org",
    "api.semanticscholar.org",
    "api.openalex.org",
    "eutils.ncbi.nlm.nih.gov",   # PubMed
    "api.crossref.org",           # CrossRef (신규)
}
```

내부망 IP(10.x, 172.16.x, 192.168.x, 127.x) 요청 차단.
화이트리스트 외 도메인 요청 → 즉시 차단, 로그 기록.

## 임베딩 클라이언트 규칙

모델: `text-embedding-3-large` (3072차원)
이전 모델(text-embedding-3-small, 1536차원)과 차원이 다름.
모델 변경 시 Alembic 마이그레이션으로 pgvector 컬럼 차원 재설정 필수.

캐시 키에 모델명 포함 (모델 바뀌면 기존 캐시 자동 무효화):
```python
# infra/llm/cache_keys.py
EMBEDDING_KEY = "embed:large:{text_hash}"  # TTL 24h
```

## LLM 클라이언트 규칙

```python
# infra/llm/protocol.py
class LLMProtocol(Protocol):
    async def complete(
        self,
        system: str,   # system 프롬프트 — 반드시 분리된 파라미터
        user: str,     # 사용자 입력 / 외부 데이터
        model: str,
        max_tokens: int,
    ) -> str: ...
```

system과 user를 단일 문자열로 합쳐서 전달하는 패턴 금지.
Secrets(API Key)는 환경변수로만 관리. 로그에 출력 금지.

## 고부하 엣지케이스 주석 기준

모든 클라이언트 메서드에 아래를 docstring 또는 주석으로 명시한다.

```python
async def search(self, query: str, *, limit: int = 10) -> list[CrossRefEntry]:
    """CrossRef 검색.

    Time: O(N) where N=결과 수
    Rate limit: TokenBucket 50 req/s
    Edge: API 응답 지연 → TIMEOUT=5.0s 후 TimeoutException → RateLimitedRetry 3회
    Edge: DOI 필드 누락 가능 → CrossRefEntry.doi Optional[str]
    """
```