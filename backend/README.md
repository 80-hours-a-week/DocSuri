# DocSuri Backend — U0 Foundation

[`unit-u0-foundation.md`](../aidlc-docs/design-artifacts/units/unit-u0-foundation.md)의 포트 8종 구현.
포트 시그니처의 단일 진실은 [`component-model.md §2`](../aidlc-docs/design-artifacts/component-model.md), 구현 매핑은 [`ADR §12`](../aidlc-docs/design-artifacts/architecture_decision_record.md).

## 설치

```bash
cd backend
uv sync --extra dev          # 권장 (uv)
# 또는: python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

## U0 §6 빌드 가능 정의 — 시연 (자격 증명 불필요, mock 모드)

```bash
uv run python scripts/u0_demo.py     # 6항목 체크리스트 순서대로 실행·출력
uv run pytest                        # 전체 테스트
```

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
└── u0/                  # U0 Foundation (이 라운드)
    ├── ports.py         # 포트 Protocol + DTO — component-model §2 시그니처 그대로
    ├── config.py        # 환경 변수 로딩·검증
    ├── cost_guard.py    # NFR-COST-01 하드 거부
    ├── http_policy.py   # NFR-NET-02 재시도 (1·2·4s, 최대 3회)
    └── adapters/
        ├── mock.py      # 결정적 mock 어댑터 7종
        ├── aws.py       # Bedrock·DynamoDB·EMF·Semantic Scholar 어댑터
        └── __init__.py  # build_u0(mode) 팩토리
```
