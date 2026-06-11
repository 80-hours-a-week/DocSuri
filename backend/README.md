# DocSuri Backend — U0 Foundation · U1 Discover

[`unit-u0-foundation.md`](../aidlc-docs/design-artifacts/units/unit-u0-foundation.md)의 포트 8종 구현(U0) + [`unit-u1-discover.md`](../aidlc-docs/design-artifacts/units/unit-u1-discover.md)의 검색 도메인(U1, 백엔드).
포트 시그니처의 단일 진실은 [`component-model.md §2`](../aidlc-docs/design-artifacts/component-model.md), 구현 매핑은 [`ADR §12`](../aidlc-docs/design-artifacts/architecture_decision_record.md).

## 설치

```bash
cd backend
uv sync --extra dev          # 권장 (uv)
# 또는: python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

## 빌드 가능 정의 — 시연 (자격 증명 불필요, mock 모드)

```bash
uv run python scripts/u0_demo.py     # U0 §6 6항목 체크리스트
uv run python scripts/u1_demo.py     # U1 DISC-01~04 서버측 동작
uv run pytest                        # 전체 테스트 (U0 + U1)
```

## U1 Discover — HTTP API (백엔드 라운드)

```bash
uv run uvicorn docsuri.app:create_app --factory   # FastAPI (mock 모드)
# POST /api/search  body: { query, filters?, sort_key?, selected_terms? }
#   → { result: SearchResult, query_mapping: {en_keywords, explanation} | null }
# GET  /healthz
```

`SearchResult`(= U3·U4와의 유일한 약속, component-model §3.7)는 동결 스키마이고,
DISC-04 한→영 매핑 1줄은 UI 표시 전용이라 응답 엔벨로프(`query_mapping`)에만 싣는다.
프론트엔드(Next.js/shadcn 검색폼·결과 카드·필터 UI)는 [`frontend/`](../frontend/README.md)에 구현돼 있다 —
프론트의 BFF(`/api/search`)가 `BACKEND_URL`로 본 백엔드를 프록시한다(미설정 시 내장 mock).

## 어댑터 모드

| 모드 | 선택 | 내용 |
|---|---|---|
| `mock` (기본) | `DOCSURI_ADAPTER_MODE=mock` | 결정적 mock — 코퍼스 fixture 검색, canned 한국어 LLM, 시간 주입식 TTL 캐시 |
| `aws` | `DOCSURI_ADAPTER_MODE=aws` | ADR §12 실구현 — Bedrock(도쿄)·KB+S3 Vectors·DynamoDB·CloudWatch EMF. 자격 증명 필요 |

환경 변수는 [`.env.example`](.env.example) 참조 (NFR-SEC-03: 평문 키 금지).

## 정적 자산

- `data/corpus_seed.json` — arXiv 실수집 AI/ML 100편 (재수집: `uv run python scripts/build_corpus.py`)
- `data/glossary_seed.json` — 학술 용어 ko-en 50개 **초안 (팀 검토 필요, A6)**

## 모듈 구조 (모듈러 모놀리스 — unit = 모듈)

```
src/docsuri/
├── app.py               # FastAPI 진입점 — create_app() (U0+U1 와이어링)
├── u0/                  # U0 Foundation
│   ├── ports.py         # 포트 Protocol + DTO — component-model §2 시그니처 그대로
│   ├── config.py        # 환경 변수 로딩·검증
│   ├── cost_guard.py    # NFR-COST-01 하드 거부
│   ├── http_policy.py   # NFR-NET-02 재시도 (1·2·4s, 최대 3회)
│   └── adapters/
│       ├── mock.py      # 결정적 mock 어댑터 7종
│       ├── aws.py       # Bedrock·DynamoDB·EMF·Semantic Scholar 어댑터
│       └── __init__.py  # build_u0(settings) 팩토리 + U0Ports
└── u1/                  # U1 Discover (백엔드 — 이 라운드)
    ├── dtos.py          # SearchResult(§3.7 동결) + 엔벨로프
    ├── difficulty.py    # DifficultyEstimator (A7 휴리스틱, LLM 미사용)
    ├── query_mapper.py  # KoEnQueryMapper (DISC-04 한→영)
    ├── keyword_expander.py  # KeywordExpander (DISC-03)
    ├── filter_sort.py   # FilterSortController + 정렬 (DISC-02)
    ├── orchestrator.py  # SearchOrchestrator (DISC-01 흐름 조율)
    ├── service.py       # build_u1(u0) 팩토리 + U1Services
    └── api.py           # FastAPI 라우터 (/api/search, /healthz)
```
