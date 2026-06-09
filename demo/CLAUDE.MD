# CLAUDE.md — 프로젝트 전체 규칙

## 프로젝트 개요

DocSuri: AI Agent 기반 학술 논문 검색·분석 서비스.
FastAPI 모듈러 모노리스 on ECS Fargate.
팀 프로젝트 / 포트폴리오 — 현재 규모에 맞되 확장 가능한 구조.
기술 선택과 패턴 도입은 실제 문제를 기반으로 결정하고, 판단 근거를 설명할 수 있어야 한다.

## 기술 스택 (확정)

- **API**: FastAPI + Pydantic v2
- **검색 라우터**: MultiDBRouter + SearchAdapter Protocol
- **LLM**: Claude Haiku (쿼리 확장, 분류) / Claude Sonnet (요약, 챗봇)
- **임베딩**: text-embedding-3-large (OpenAI, 3072차원)
- **벡터 검색**: pgvector (PostgreSQL 익스텐션)
- **DB**: PostgreSQL (pgvector 포함)
- **캐시 / 세션 / 락**: ElastiCache Redis
- **비동기 작업**: FastAPI BackgroundTasks → SNS+SQS (확장 예정)
- **LangGraph**: 확장 예정 (현재 미사용)

## 디렉토리 구조

```
demo/
├── app/
│   ├── api/           # FastAPI 라우터만. 비즈니스 로직 금지
│   ├── crosscutting/  # 도메인 비의존 공통 유틸 (ratelimit, audit, verifier 등)
│   ├── domain/        # 도메인별 비즈니스 로직
│   │   └── papers/    # search.py, normalizer.py, models.py, ingest.py
│   └── infra/         # 외부 시스템 클라이언트
│       ├── http/      # 논문 소스별 HTTP 클라이언트
│       ├── embedding/ # 임베딩 클라이언트
│       ├── llm/       # LLM 클라이언트
│       └── storage/   # DB, Redis, pgvector
├── tests/
├── scripts/
└── seed/
```

## 절대 금지

- OFFSET/LIMIT 페이지네이션 → `WHERE id > cursor` 커서 방식만 허용
- TTL 없는 Redis 키 → 모든 키에 TTL 명시 필수
- 직접 DDL 수정 → Alembic 마이그레이션으로만 스키마 변경
- api/ 레이어에 비즈니스 로직 작성
- domain/ 에서 infra/ 직접 import → container.py 의존성 주입 사용
- domain ↔ domain 순환 참조
- AGENTS.md에 명시된 모듈 경계 위반
- API Key 등 Secrets 하드코딩 → 환경변수(.env)로만 관리
- 타당한 사유 없이 새 파일·모듈 생성

## 코드 품질 기준

모든 함수·메서드 구현 시 아래를 기본으로 포함한다.

- 단일 책임: 함수 하나가 한 가지 일만 한다
- 시간/공간 복잡도를 docstring 또는 주석에 명시한다
- 고부하 엣지케이스(대용량 입력, 동시 요청, 외부 소스 전체 실패 등)를 주석에 남긴다
- 에러 처리를 기본으로 포함한다 (예외 무시 금지)

```python
async def rrf_merge(ranked_lists: list[list[PaperSummary]], k: int = 60):
    """RRF 점수 병합.

    Time: O(N*M) where N=소스 수, M=소스당 결과 수
    Edge: 모든 소스 CB Open → ranked_lists 빈 리스트 → 빈 결과 반환
    """
```

## 보안 위협과 대응 위치

| 위협 | 발생 지점 | 대응 위치 |
|---|---|---|
| 권한 없는 리소스 접근 | 사용자별 리소스 조회·수정 | api/ JWT 인증 + user_id 검증 |
| 입력 삽입 | 외부 쿼리 → LLM·DB 전달 | normalizer.py sanitize |
| Prompt Injection | 논문 데이터 → LLM 전달 | system/user 프롬프트 분리 |
| 콘텐츠 삽입 (XSS) | 제목·초록 화면 출력 | schema 직렬화 시 이스케이프 |
| 내부망 접근 (SSRF) | 외부 소스 URL 직접 요청 | crosscutting/verifier/port.py |
| 요청 위조 (CSRF) | 상태 변경 요청 | JWT Bearer 토큰 인증 강제 |
| 인증 토큰 | 로그인·토큰 갱신 | auth 도메인 전담 처리 |
| Secrets 노출 | API Key 사용 | 환경변수만 사용, 로그 출력 금지 |
| 요청 남용 | 검색·LLM 비용 발생 엔드포인트 | crosscutting/ratelimit + SlowAPI |

## LLM 호출 규칙

- system 프롬프트와 외부 데이터(논문 본문, 사용자 입력)를 반드시 분리된 파라미터로 전달
- 단일 문자열로 합쳐서 전달 금지
- 불필요한 컨텍스트 제거 → 논문 전체 본문 대신 초록·핵심 섹션만 전달
- 동일 입력 중복 호출 방지 → Redis 캐시 적용 필수
- 검색된 문서 외 내용을 생성하지 않도록 system 프롬프트에 명시
- LLM에 전달 전 외부 입력 sanitization 필수
- 모든 LLM 호출 Langfuse 추적 필수 (토큰, 비용, 레이턴시)

## 캐싱 규칙

- 캐시 미스 시 원본에서 읽어 캐시에 쓰는 방식(read-through) 사용
- 모든 Redis SET에 TTL 명시 필수 (ex= 생략 금지)

```python
# 네임스페이스
search:{query_hash}      # TTL 1h
expand:{query_hash}      # TTL 6h
embed:large:{text_hash}  # TTL 24h
summary:{paper_id}       # TTL 48h
session:{session_id}     # TTL 24h
```

## 공통 에러 처리

```python
# 성공
{"data": ..., "next_cursor": ..., "error": null}

# 실패
{"data": null, "error": {"code": "RATE_LIMIT_EXCEEDED", "message": "..."}}
```

스택 트레이스, 내부 경로, Secrets는 응답에 절대 포함하지 않는다.

## 관측성

- 모든 요청: 구조화된 JSON 로그 (request_id 포함)
- 외부 소스 호출: OpenTelemetry span 계측 (구간별 시간 추적)
- LLM 호출: Langfuse 추적
- 핵심 지표: API 레이턴시, 오류율, Redis 캐시 히트율, CB 상태