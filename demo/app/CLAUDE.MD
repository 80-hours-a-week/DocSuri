# CLAUDE.md — app 레이어 공통 규칙

## 실제 코드 구조

domain/papers/ 구조:

```
domain/papers/
├── search.py      # MultiDBRouter, SearchAdapter Protocol, 어댑터 클래스
├── normalizer.py  # NormalizedQuery, normalize() — 쿼리 정규화·확장
├── models.py      # PaperSummary 등 도메인 모델
└── ingest.py      # PDF 인입 트리거 (#01b)
```

## 레이어별 책임 경계

**api/ (routes_*.py)**
- JWT 인증 (`Depends(get_current_user)`)
- Pydantic 입력 검증
- Rate Limit 적용 (crosscutting/ratelimit)
- BackgroundTasks 의존성 주입
- domain 호출 후 Response Formatter 통과시켜 반환
- 비즈니스 로직, DB 접근 금지

**domain/papers/search.py**
- MultiDBRouter: 어댑터 팬아웃, dedupe, RRF 병합
- SearchAdapter Protocol: 새 소스 = 새 어댑터 클래스 하나
- normalizer.py의 normalize() 호출
- infra 직접 import 금지 → container.py 주입 사용

**domain/papers/normalizer.py**
- 쿼리 sanitization (LLM 전달 전 필수)
- Claude Haiku로 쿼리 확장 (동의어, 영문 변환, 분야 필터)
- NormalizedQuery: for_arxiv(), for_openalex() 등 소스별 쿼리 생성

**infra/**
- 외부 시스템 클라이언트만
- 비즈니스 로직 금지
- 모든 외부 호출 타임아웃 명시

## SearchAdapter Protocol 확장 규칙

새 소스 추가 시 반드시 이 Protocol을 구현한다.

```python
class SearchAdapter(Protocol):
    source: str

    async def search(self, nq: NormalizedQuery, *, limit: int) -> list[PaperSummary]:
        ...

    async def healthcheck(self) -> bool:
        ...
```

어댑터 내부에서 도메인 로직 작성 금지.
응답 파싱만 담당하고 매핑은 `_to_summary()` 헬퍼로 분리.

## BackgroundTasks 규칙

현재 SNS+SQS 대신 FastAPI BackgroundTasks 사용.

```python
# api/routes_search.py
@router.get("/search")
async def search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    router: MultiDBRouter = Depends(get_router),
):
    results, nq = await router.search(
        request.query,
        limit=request.limit,
        background_tasks=background_tasks,
    )
    return format_response(results, nq)
```

BackgroundTasks로 등록하는 작업:
- 신규 논문 임베딩 생성 → pgvector 저장 (검색 결과 기준)

Citation 저장은 현재 구현 범위 밖. 추가하지 않는다.

**제약 및 대응**

BackgroundTasks는 프로세스 종료 시 실행 중인 작업이 유실될 수 있다.
아래 두 가지로 보완한다.

1. 멱등 보장: 작업 실행 전 중복 체크 필수
2. 실패 로깅: 예외 발생 시 반드시 구조화된 로그 기록 (무시 금지)

```python
async def _embed_paper(paper: PaperSummary) -> None:
    try:
        existing = await repo.get_embedding(paper.id)
        if existing:
            return  # 멱등: 이미 있으면 스킵
        embedding = await embedding_client.embed(paper.abstract)
        await repo.save_embedding(paper.id, embedding)
    except Exception:
        logger.exception(  # 실패 감지: 로그 필수
            "embed_paper_failed",
            extra={"paper_id": paper.id},
        )
        raise
```

## LLM 호출 규칙

```python
# 금지 — system과 user 합치기
prompt = f"{system_instruction}\n\nUser: {user_input}"

# 허용 — 분리된 파라미터
await llm.complete(
    system="학술 논문 검색 쿼리를 확장한다. JSON만 반환.",
    user=f"<query>{sanitized_query}</query>",
)
```

논문 본문·초록을 LLM에 전달할 때는 반드시 `<document>` 태그로 격리.

```python
user = f"<document>{sanitized_content}</document>\n위 논문을 요약하라."
```

불필요한 컨텍스트 제거: 논문 전체 본문 대신 초록 또는 핵심 섹션만 전달.
동일 입력 중복 호출 방지: LLM 호출 전 Redis 캐시 확인 필수.