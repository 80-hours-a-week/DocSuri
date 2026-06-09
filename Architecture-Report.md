# DocSuri Architecture Report

DocSuri는 PostgreSQL 원본 논문 데이터와 PGVector 청크를 기반으로 요약 및 번역을 수행하는 FastAPI 애플리케이션이다. 런타임은 PostgreSQL과 AWS Bedrock Runtime 접근 권한을 필수 구성으로 요구한다.

## Runtime Components

```text
FastAPI
  ├─ PostgreSQL / PGVector
  │   ├─ papers: 원문, 제목, 초록, PDF bytes
  │   └─ paper_chunks: anchor, chunk_text, embedding
  ├─ AWS Bedrock TwelveLabs Marengo Embed
  │   └─ 요청 텍스트 → query embedding
  ├─ AWS Bedrock Claude
  │   ├─ 요약 생성
  │   └─ 번역 생성
  └─ Static Frontend
      └─ 논문 보기, 요약, 선택/전체 번역 UI
```

## Request Flow

### Summary

```text
POST /api/summarize
→ paper_id로 PostgreSQL에서 논문 로드
→ 길이/관점 기반 retrieval query 생성
→ Bedrock Marengo embedding 생성
→ PGVector에서 관련 chunk top-k 검색
→ Bedrock Claude에 원문 일부 + anchor/chunk context 전달
→ 요약 생성
→ anchor 검증
→ SummaryResponse 반환
```

### Translation

```text
POST /api/translate
→ paper_id로 PostgreSQL에서 논문 로드
→ selected_text 또는 char span 확정
→ 주변 문맥 기반 retrieval query 생성
→ Bedrock Marengo embedding 생성
→ PGVector에서 관련 chunk top-k 검색
→ 수식/LaTeX 마스킹
→ Bedrock Claude에 source span + anchor/chunk context 전달
→ 번역 생성
→ 수식/LaTeX 복원
→ anchor 매칭 및 검증
→ TranslateResponse 반환
```

## Required Environment

```env
DATABASE_URL=postgresql://...
AWS_REGION=ap-northeast-2
ANTHROPIC_MODEL=anthropic.claude-opus-4-6-v1
ANTHROPIC_VERIFIER_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0
EMBEDDING_MODEL=twelvelabs.marengo-embed-3-0-v1:0
RETRIEVAL_TOP_K=8
```

AWS 자격 증명은 boto3 credential chain을 사용한다. `EMBEDDING_MODEL`은 `paper_chunks.embedding`을 생성할 때 사용한 모델과 동일해야 한다.

## Data Assumptions

기본 스키마는 `schema.sql`을 따른다.

- `papers.id`
- `papers.title`
- `papers.abstract`
- `papers.structured_markdown` 또는 `papers.full_text`
- `papers.pdf_bytes`
- `paper_chunks.paper_id`
- `paper_chunks.chunk_text`
- `paper_chunks.anchor`
- `paper_chunks.chunk_index`
- `paper_chunks.embedding`

테이블명과 주요 컬럼명은 `.env`에서 override할 수 있다.

## Failure Policy

앱은 필수 외부 의존성이 없으면 시작하지 않는다.

- PostgreSQL 연결 실패: startup 실패
- `DATABASE_URL` 누락: startup 실패
- AWS Bedrock 자격 증명/권한 누락: Bedrock 호출 실패
- PGVector embedding 컬럼 누락: retrieval 요청 실패

이 정책은 운영 중 잘못된 데이터 소스나 비실제 LLM 결과가 사용자에게 노출되는 것을 방지하기 위한 것이다.
