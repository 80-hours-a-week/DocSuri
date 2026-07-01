# U7 Summarization — Integration Test Instructions

**단계**: CONSTRUCTION → Build & Test · **유닛**: U7 Summarization · **일자**: 2026-06-19
**원칙(real-first)**: 통합 테스트는 **실 의존성**(Bedrock·S3·Redis·RDS·U6 후크·U1 전문)을 대상으로 한다. 자격증명/엔드포인트 부재 시 **self-skip**(단위 CI 레인은 green 유지). 실행은 별도 게이트 레인(스코프 CI 역할).

## Test Scenarios

### S1. U7 → Bedrock (생성·근거화)
- **설명**: 실 Sonnet/Haiku 호출 → §3 JSON 파싱 → U7 결정적 근거화 통과/기권.
- **검증**: 근거 있는 논문 → `SummaryResultDTO`(앵커 실재); 근거 없는 입력 → `AbstainDTO`.

### S2. U7 → S3 + Redis (캐시)
- **설명**: write-through(S3 영구 + Redis 핫) → read-through HIT(LLM 0콜)·immutable 키.
- **검증**: 두 번째 호출 `cached=true`·재생성 없음.

### S3. U7 → S3 (U1 전문 read) + 폴백
- **설명**: `stored_full_text_ref` read; 부재 시 초록 폴백(메타 표기).

### S4. U7 → RDS (개인 용어집, owner 격리)
- **설명**: `user_glossary` upsert→`glossary_ver++`→캐시 키 분기; cross-user 미노출.

### S5. U6 비용 게이트
- **설명**: `get_budget_state` OPEN → `CostDegradedDTO`(LLM 호출 전).

## Setup
```bash
export DOCSURI_SUMMARY_BUCKET=docsuri-... AWS_REGION=ap-northeast-2
export DOCSURI_REDIS_URL=rediss://... DATABASE_URL=postgresql://...
# RDS 마이그레이션 선적용:
psql "$DATABASE_URL" -f backend/modules/summarization/migrations/001_create_user_glossary.sql
```

## Run
```bash
cd backend/modules/summarization
pip install -e . --extra real     # boto3/redis/psycopg
PYTHONPATH="src:../../../shared/python/src" python -m pytest tests/test_integration_real.py -q
```
- 자격증명 부재 시: `1 skipped`(정상 — 게이트 레인 전용).

## Cleanup
- 테스트 S3 객체(`summaries/test-*`)·Redis `sum:test-*`·RDS 테스트 행 정리(테스트 스코프 자격증명).
