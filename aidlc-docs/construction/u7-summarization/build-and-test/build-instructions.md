# U7 Summarization — Build Instructions

**단계**: CONSTRUCTION → Build & Test · **유닛**: U7 Summarization · **일자**: 2026-06-19
**범위**: U7 증분(시스템 전역 빌드는 `construction/build-and-test/` 참조). 모노레포 모듈 `backend/modules/summarization/`.

## Prerequisites
- **빌드 도구**: Python ≥3.11 · `uv`(워크스페이스) / 또는 venv. 패키지 `docsuri-summarization`(hatchling).
- **의존성**: `docsuri-shared`(경로 의존, `shared/python`) · `pydantic>=2.7`. optional `api=[fastapi]` · `real=[boto3,redis,psycopg]`. dev `pytest·hypothesis·ruff`.
- **환경 변수**(real 경로): `DOCSURI_SUMMARY_BUCKET`(S3, 마운트 게이트) · `DOCSURI_REDIS_URL` · `DATABASE_URL`(RDS) · `DOCSURI_SUMMARY_MODEL_ID`/`DOCSURI_TRANSLATE_MODEL_ID`(기본 Sonnet/Haiku) · `AWS_REGION`. **미설정 시 모듈은 graceful-skip**(real-first, mock 폴백 없음).

## Build Steps

### 1. 의존성 설치 (모듈 단독)
```bash
cd backend/modules/summarization
uv sync                      # 또는: pip install -e . --extra real
```

### 2. 빌드/임포트 검증 (코드 생성물은 인터프리티드 — 컴파일 단계 없음)
```bash
PYTHONPATH="src:../../../shared/python/src" python -c \
  "import summarization.real_wiring, summarization.api.router; print('import OK')"
```

### 3. 빌드 산출물
- 휠: `uv build`(선택) → `dist/docsuri_summarization-*.whl`.
- 마이그레이션: `migrations/001_create_user_glossary.sql`(RDS 적용은 배포 last-mile).

## Troubleshooting
- **`ModuleNotFoundError: docsuri_shared`**: `PYTHONPATH`에 `shared/python/src` 추가 또는 `uv sync`.
- **`ModuleNotFoundError: boto3/redis/psycopg`**: `real` extra 미설치 — 단위 테스트엔 불필요(통합만 필요).
- **마운트 안 됨**: `DOCSURI_SUMMARY_BUCKET` 미설정 → 의도된 graceful-skip. app-shell 마운트는 조율 존(@ELSAPHABA 사인오프; `code/README.md` 스니펫).
