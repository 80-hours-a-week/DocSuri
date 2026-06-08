# DocSuri 요약·번역 아키텍처 리포트

## 1. 목적과 범위

DocSuri의 요약·번역 모듈은 논문 검색 파이프라인이 수집한 논문 데이터를 기반으로, 사용자가 선택한 논문에 대해 anchor가 포함된 한국어 요약과 span 단위 학술 번역을 제공한다.

현재 구현 범위는 다음과 같다.

- FastAPI 기반 API 서버
- PostgreSQL 원본 논문 및 PGVector 청크 조회 계층
- Anthropic LLM 호출 계층과 로컬 데모용 mock LLM
- anchor 검증, 수식 마스킹, 세션 glossary 관리
- 브라우저에서 바로 실행 가능한 단순 데모 프론트엔드

논문 수집, PDF 파싱, 임베딩 생성, 논문DB 외부 검색은 이 모듈의 전단계로 보고, 본 리포트는 이미 저장된 논문 데이터를 조회해 요약·번역하는 후단 기능에 초점을 둔다.

## 2. 전체 구조

```text
Browser UI
  |
  | HTTP
  v
FastAPI App
  |
  +-- PaperRepository
  |     |
  |     +-- PostgresPaperRepository -> PostgreSQL papers
  |     |                            -> PostgreSQL paper_chunks + PGVector
  |     |
  |     +-- DemoPaperRepository      -> built-in demo paper
  |
  +-- LLMClient
  |     |
  |     +-- AnthropicLLMClient       -> Claude API
  |     |
  |     +-- MockLLMClient            -> local deterministic demo
  |
  +-- Processing Services
        |
        +-- anchor validation
        +-- span resolving
        +-- math masking/restoration
        +-- glossary lookup/update
```

핵심 설계는 API 계층, 데이터 접근 계층, LLM 계층, 후처리 계층을 분리하는 것이다. FastAPI 라우터는 요청을 조율하고, 실제 DB 스키마 탐색과 LLM 호출 세부사항은 별도 모듈로 숨긴다. 이 구조 덕분에 실제 운영 DB가 없어도 mock repository로 데모가 가능하고, LLM API 키가 없어도 UI와 API 흐름을 검증할 수 있다.

## 3. 디렉터리와 책임

```text
app/
  main.py                 FastAPI 앱, 라우팅, 의존 객체 초기화
  config.py               환경변수 기반 설정
  db.py                   asyncpg connection pool 생성
  models.py               요청/응답/도메인 Pydantic 모델
  repositories.py         PostgreSQL 및 데모 논문 저장소
  services/
    anchors.py            anchor 추출, evidence 조회, 간단 검증
    glossary.py           세션별 용어 사전
    llm.py                Anthropic/mock LLM 클라이언트
    processing.py         span 처리, 수식 보호, 응답 조립
static/
  index.html              데모 UI
  styles.css              데모 UI 스타일
  app.js                  API 호출 및 화면 렌더링
schema.sql                기본 PostgreSQL/PGVector 스키마
```

## 4. 런타임 초기화

FastAPI lifespan에서 다음 객체를 한 번 초기화해 `app.state`에 보관한다.

1. `Settings`
   `.env` 또는 환경변수에서 DB URL, LLM provider, Anthropic 모델명, 테이블명 등을 읽는다.

2. `PaperRepository`
   `DATABASE_URL`로 PostgreSQL 연결이 가능하면 `PostgresPaperRepository`를 사용한다. 연결 정보가 없거나 연결 실패 시 `DemoPaperRepository`로 fallback한다.

3. `LLMClient`
   `ANTHROPIC_API_KEY`가 있으면 `AnthropicLLMClient`를 사용한다. 키가 없으면 `MockLLMClient`를 사용한다.

4. `GlossaryStore`
   세션별 glossary를 메모리에 저장한다. 현재 MVP에서는 프로세스 메모리 기반이며, 운영 환경에서는 Redis 또는 PostgreSQL로 교체하는 것이 적절하다.

## 5. 데이터 계층

### 5.1 기본 스키마

`schema.sql`은 다음 테이블을 제안한다.

- `papers`
  원본 논문 단위의 메타데이터, 구조화 본문, PDF bytes를 저장한다.

- `paper_chunks`
  논문별 chunk 텍스트, anchor, page/paragraph 정보, embedding vector를 저장한다.

```sql
papers(id, title, abstract, structured_markdown, pdf_bytes, created_at)
paper_chunks(id, paper_id, chunk_index, anchor, section, page, paragraph, chunk_text, embedding, metadata)
```

`paper_chunks.embedding`은 `vector(1536)`으로 정의되어 있으며, `ivfflat` cosine index를 생성한다. 실제 임베딩 모델 차원이 다르면 이 값을 조정해야 한다.

### 5.2 스키마 적응 방식

운영 DB는 ingestion 파이프라인에 따라 컬럼명이 다를 수 있으므로, repository는 몇 가지 흔한 컬럼명을 자동 탐색한다.

- 논문 본문 후보: `structured_markdown`, `full_text`, `extracted_text`, `body_text`, `abstract`
- PDF 후보: `pdf_bytes`, `pdf`, `raw_pdf`, `file_bytes`
- 제목 후보: `title`, `paper_title`, `name`
- 청크 텍스트 후보: `chunk_text`, `content`, `text`, `body`
- anchor 후보: `anchor`, `section_anchor`, `locator`
- 정렬 후보: `chunk_index`, `position`, `idx`, `id`

테이블명과 id 컬럼명은 `.env`에서 바꿀 수 있다.

```env
PAPER_TABLE=papers
PAPER_CHUNK_TABLE=paper_chunks
PAPER_ID_COLUMN=id
PAPER_CHUNK_PAPER_ID_COLUMN=paper_id
```

### 5.3 PDF fallback

논문 본문 컬럼이 비어 있고 PDF bytes가 있으면 `pypdf`로 텍스트 추출을 시도한다. 다만 PDF 직접 추출은 구조, 표, 수식, 캡션 품질이 제한적이므로 운영에서는 GROBID 같은 전처리기로 구조화 텍스트를 미리 저장하는 방식을 권장한다.

## 6. API 설계

### 6.1 논문 조회

`GET /api/papers`

논문 목록을 반환한다. UI의 paper selector에서 사용한다.

`GET /api/papers/{paper_id}`

논문 미리보기, 본문 길이, 일부 청크를 반환한다. 데모 UI에서 왼쪽 본문 패널을 구성한다.

### 6.2 요약

`POST /api/summarize`

요청 필드:

- `paper_id`
- `session_id`
- `length_preset`: `tldr`, `paragraph`, `page`
- `angle_preset`: `contribution`, `method`, `results`, `critical`

응답은 문장 단위로 구성된다.

- `text`: anchor를 포함한 요약 문장
- `anchors`: 추출된 anchor 목록
- `verification`: 검증 라벨과 근거
- `glossary`: 세션 용어 사전

### 6.3 번역

`POST /api/translate`

요청 방식은 두 가지다.

- `selected_text`: UI에서 사용자가 선택한 원문 span
- `char_start` / `char_end`: 전체 본문 기준 문자 offset

처리 결과는 source/translation unit 단위로 반환된다.

- `anchor`
- `source_text`
- `translated_text`
- `verification`
- `glossary`

### 6.4 Glossary 조회

`GET /api/glossary/{session_id}`

현재 세션에 누적된 용어 사전을 반환한다.

## 7. 요약 처리 흐름

```text
POST /api/summarize
  |
  v
Fetch paper from repository
  |
  v
Lookup/update session glossary using paper text
  |
  v
Call LLMClient.summarize()
  |
  v
Extract anchors from each generated sentence
  |
  v
Validate anchors against known paper anchors
  |
  v
Return structured SummaryResponse
```

요약 기능은 사양서의 세 가지 핵심 요구를 반영한다.

1. 길이 프리셋
   `tldr`, `paragraph`, `page`로 LLM prompt의 출력 길이 규칙을 바꾼다.

2. 관점 프리셋
   기여, 방법, 결과·실험, 비판적 검토 관점을 prompt에 전달한다.

3. anchor 강제
   Anthropic prompt에서 모든 문장에 `[§n.m]` 또는 `[p.X ¶Y]` 형식 anchor를 요구한다. 후처리에서는 실제 논문에 존재하는 anchor인지 검증한다.

현재 verifier는 경량 규칙 기반 검증이다. anchor가 실제 chunk 또는 본문 span과 매칭되면 `SUPPORTED`로 판정한다. 운영 고도화 단계에서는 사양서처럼 별도 verifier LLM을 호출해 `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / NOT_FOUND` entailment 판정을 수행하는 것이 적절하다.

## 8. 번역 처리 흐름

```text
POST /api/translate
  |
  v
Fetch paper from repository
  |
  v
Resolve selected_text or char_start/char_end into source span
  |
  v
Mask LaTeX/math expressions
  |
  v
Lookup/update session glossary from source span
  |
  v
Call LLMClient.translate()
  |
  v
Restore masked math expressions
  |
  v
Split source/translation into translation units
  |
  v
Attach nearest anchor and verification label
  |
  v
Return structured TranslateResponse
```

번역 기능은 전체 논문 번역이 아니라 선택 span 번역을 기본 단위로 한다. 이는 비용과 품질을 모두 고려한 설계다. 사용자가 필요한 문장 또는 문단만 선택하면 해당 span과 세션 glossary를 LLM에 전달한다.

수식 보호는 번역 전 `$...$`, `$$...$$`, `\(...\)`, `\[...\]` 패턴을 placeholder로 바꾸고, 번역 후 원래 문자열로 복원한다. 이 방식은 간단하지만 실용적이며, 향후 코드블록, 표, 복잡한 LaTeX 환경까지 확장할 수 있다.

## 9. LLM 계층

### 9.1 인터페이스

`LLMClient`는 두 가지 메서드를 정의한다.

- `summarize(paper, length_preset, angle_preset, glossary)`
- `translate(paper, source_text, glossary)`

API 계층은 구체 provider를 모르고 이 인터페이스만 호출한다.

### 9.2 Anthropic 구현

`AnthropicLLMClient`는 Claude 메시지 API를 사용한다.

요약 prompt 특징:

- 한국어 학술 요약 지시
- 모든 문장에 anchor 포함 강제
- JSON 응답 강제: `{"sentences": ["..."]}`
- 논문 전문을 system block으로 제공
- `cache_control: {"type": "ephemeral"}` 적용

번역 prompt 특징:

- 한국어 `한다`체 학술 번역
- LaTeX, 인용, 숫자, 고유명사 보존
- JSON 응답 강제: `{"translation": "..."}`
- 논문 전문 context와 세션 glossary 제공

### 9.3 Mock 구현

`MockLLMClient`는 API key 없이도 데모가 가능하도록 deterministic 응답을 만든다. 실제 품질을 목표로 하지 않고, API shape, UI 렌더링, DB 연결, anchor 검증 흐름을 검증하는 용도다.

## 10. Glossary 설계

`GlossaryStore`는 `session_id`별로 용어 매핑을 관리한다.

현재 구현은 다음 특징을 가진다.

- 프로세스 메모리 기반
- 기본 용어 사전에서 source text와 매칭되는 용어를 자동 등록
- 첫 등장 여부를 `first_seen`으로 표시
- 요약과 번역 API가 같은 `session_id`를 공유하면 glossary도 공유

운영 환경에서는 다음 개선이 필요하다.

- Redis hash 또는 PostgreSQL table로 영속화
- TTL 정책 적용
- 사용자 수정 API 추가
- 잘못된 glossary 수정 시 과거 번역 재처리 옵션 추가
- 논문별, 사용자별, 세션별 scope 분리

## 11. Anchor와 검증

anchor는 요약과 번역 UI 신뢰도의 핵심이다. 현재 구현은 다음 형식을 인식한다.

```text
[§1.1]
[p.3 ¶2]
```

검증 흐름은 다음과 같다.

1. 생성 문장에서 anchor를 정규식으로 추출한다.
2. 논문 본문과 chunk 목록에서 알려진 anchor set을 구성한다.
3. anchor가 존재하지 않으면 `NOT_FOUND`로 판정한다.
4. anchor가 존재하고 evidence span이 조회되면 `SUPPORTED`로 판정한다.

현재 검증은 "anchor가 실제 위치를 가리키는가"에 초점이 있다. "문장 의미가 원문 evidence에 의해 함의되는가"는 별도 LLM verifier로 확장해야 한다.

권장 고도화 구조:

```text
Generated sentence + anchors
  |
  v
Fetch evidence spans
  |
  v
Verifier LLM
  |
  v
SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / NOT_FOUND
```

## 12. 프론트엔드 구조

프론트엔드는 별도 빌드 도구 없이 정적 파일로 구성된다.

- `index.html`: 화면 구조
- `styles.css`: 반응형 2-column 레이아웃
- `app.js`: API 호출, 상태 관리, 결과 렌더링

화면은 크게 세 영역이다.

1. 논문 선택 toolbar
2. 원문 preview panel
3. 요약, 번역, glossary control panel

사용자는 왼쪽 본문에서 텍스트를 선택하면 번역 textarea에 자동 입력되고, `선택 span 번역` 버튼으로 번역 API를 호출한다.

## 13. 운영 배포 관점

### 13.1 프로세스 구성

개발 환경:

```text
uvicorn app.main:app --reload --port 8000
```

운영 환경:

```text
gunicorn/uvicorn workers
  |
  +-- FastAPI app
  +-- asyncpg pool per worker
  +-- Redis glossary/session store
  +-- external LLM API
```

### 13.2 환경변수

필수 또는 주요 설정:

- `DATABASE_URL`
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`
- `ANTHROPIC_VERIFIER_MODEL`
- `PAPER_TABLE`
- `PAPER_CHUNK_TABLE`

LLM API key가 없는 경우 mock provider로 동작하므로, 데모와 CI에서는 외부 비용 없이 API shape를 검증할 수 있다.

### 13.3 장애 fallback

현재 fallback 정책:

- PostgreSQL 연결 실패: demo repository 사용
- Anthropic key 없음: mock LLM 사용

운영에서는 DB 연결 실패를 조용히 demo로 넘기면 안 된다. production 환경에서는 `APP_ENV=production` 같은 플래그를 두고 DB 연결 실패 시 앱 시작을 실패시키는 것이 안전하다.

## 14. 보안과 개인정보

논문 PDF와 본문은 저작권 및 접근권한 이슈가 있을 수 있다. 운영 설계에서는 다음 정책이 필요하다.

- 사용자가 접근 권한을 가진 논문만 처리
- 원본 PDF 다운로드 URL 또는 bytes 접근 권한 검증
- API 인증 및 사용자별 paper access control
- LLM provider로 전송되는 텍스트 범위와 보존 정책 고지
- request/response log에 논문 전문 또는 번역 span을 과도하게 남기지 않기

현재 MVP에는 인증/인가가 없다. 내부 데모 또는 로컬 개발용으로 봐야 한다.

## 15. 성능과 비용 고려사항

### 15.1 Prompt caching

Anthropic system block에 논문 전문을 넣고 `cache_control: ephemeral`을 적용했다. 같은 논문에 대해 길이/관점만 바꿔 재요약하거나 여러 span을 연속 번역할 때 입력 토큰 비용을 낮추는 구조다.

### 15.2 긴 논문 처리

현재 MVP는 논문 전문을 LLM context에 넣는 단순 구조다. 긴 논문에서는 다음 전략이 필요하다.

- PGVector similarity search로 관련 chunk만 선택
- section별 hierarchical summary 생성
- 표/그림/caption 별도 extraction
- context budget 기반 prompt builder 추가
- chunk coverage metadata를 응답에 포함

### 15.3 Verifier 비용

모든 문장에 verifier LLM을 호출하면 비용이 증가한다. 운영에서는 다음 정책을 선택할 수 있다.

- 요약 문장은 전수 검증
- 번역 문장은 sampling 검증
- critical mode는 전수 검증
- 사용자가 anchor hover 또는 상세 확인을 열 때 lazy verification

## 16. 확장 로드맵

우선순위가 높은 고도화 항목은 다음과 같다.

1. 실제 verifier LLM 추가
   현재 규칙 기반 anchor 검증을 entailment 검증으로 확장한다.

2. PGVector 검색 활용
   `paper_chunks.embedding`을 이용해 긴 논문에서 관련 chunk를 선별한다.

3. Redis glossary 저장소
   메모리 glossary를 다중 worker 환경에서도 공유되게 만든다.

4. 사용자 수정 glossary API
   사용자가 용어 번역을 수정하면 즉시 이후 요약/번역에 반영한다.

5. anchor hover UI
   요약 문장 anchor에 마우스를 올리면 원문 evidence span을 보여준다.

6. 인증/인가
   사용자별 논문 접근 권한과 세션 관리를 추가한다.

7. 작업 큐
   긴 요약, 다량 번역, verifier batch를 Celery/RQ/Arq 같은 worker로 분리한다.

## 17. 현재 MVP의 한계

- 실제 PGVector similarity query는 아직 API 흐름에 포함되어 있지 않다.
- verifier는 LLM 기반 의미 검증이 아니라 anchor 존재 검증 중심이다.
- glossary는 메모리 기반이라 서버 재시작 시 사라진다.
- 데모 UI는 기능 확인용이며, production UX 수준의 evidence hover/diff view는 없다.
- 인증, 사용자 권한, 논문 접근 정책이 없다.
- PDF parsing은 fallback 용도이며, 구조화 extraction 품질을 보장하지 않는다.

## 18. 결론

현재 구현은 요약·번역 기능의 end-to-end 골격을 갖춘 MVP다. PostgreSQL/PGVector에서 논문과 청크를 읽고, LLM 계층을 통해 anchor가 포함된 요약과 span 번역을 생성하며, glossary와 간단한 검증 결과를 API 응답으로 반환한다.

운영 수준으로 발전시키려면 PGVector 기반 context selection, LLM verifier, Redis glossary, 인증/인가, evidence hover UI를 순차적으로 추가하는 것이 가장 자연스럽다. 현재 모듈 경계는 이러한 확장을 위해 repository, LLM client, processing service를 분리해 두었으므로, 각 기능을 독립적으로 교체하거나 강화할 수 있다.
