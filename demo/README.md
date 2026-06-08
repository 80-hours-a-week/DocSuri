# Semantic Paper Workbench — Sprint 1 데모

> 5주 프로토타입 walking-skeleton. FastAPI + vanilla JS.
> AGENTS.md §3.1 빌드 순서의 첫 네 기능을 한 컨테이너에서 시연한다.

## Table of contents

- [What this is](#what-this-is)
- [Scope (in / out)](#scope-in--out)
- [Quick start (빠른 실행)](#quick-start-빠른-실행)
- [Demo flow (데모 흐름)](#demo-flow-데모-흐름)
- [Module map](#module-map)
- [Architecture notes](#architecture-notes)
- [Testing](#testing)
- [Known limitations](#known-limitations)

---

## What this is

This is the **Sprint 1 walking-skeleton** for *Semantic Paper Workbench* — a research-consumption tool described in `../AGENTS.md` §1.1. It implements the first four features in the §3.1 build order (`01a → 01b → 02 → 03`): natural-language search, PDF ingest, length-preset summarisation, and span-level Korean translation. Everything runs as a single **modular monolith** (§5.1) so the boundaries between `domain/`, `crosscutting/`, and `infra/` can be exercised end-to-end without distributed-system overhead.

The demo runs in two modes:
- **mock** (default — no env vars): deterministic offline LLM + abstract-only ingest. Works without internet.
- **live** (`ANTHROPIC_API_KEY` set): real Claude calls; optionally real PDF parsing via `GROBID_URL`.

## Scope (in / out)

Sprint 1 only — see `../Sprint-Capacity-Plan.md` §3.1 for the 60-point budget.

| Feature | Sprint 1 deliverable | Status here | Source |
|---|---|---|---|
| #01a Search | arXiv adapter + Query Normalizer + Multi-DB Router shape | **done (mock + live)** | `Sprint-Backlog-Search.md` Sprint 1 |
| #01a Search | Semantic Scholar / OpenAlex / Crossref / PubMed adapters | out (Sprint 2) | `Sprint-Backlog-Search.md` Sprint 2 |
| #01b Ingest | PDF fetch → GROBID parse → in-memory `Paper`, abstract-only fallback | **done (mock-only without GROBID)** | `Sprint-Backlog-Ingest.md` Sprint 1 |
| #01b Ingest | Qdrant chunks collection + embedding insert | out (Sprint 2) | `Sprint-Backlog-Ingest.md` Sprint 2 |
| #02 Summarization | `infra/llm` Owner port + length presets + paragraph summary | **done (mock + live)** | `Sprint-Backlog-Summarization.md` Sprint 1 |
| #02 Summarization | 4-way verify badges + anchor validator + UI hover | mock-only (verifier stub returns SUPPORTED) | `Sprint-Backlog-Summarization.md` Sprint 2 |
| #03 Translation | `crosscutting/glossary` Owner schema + span resolver + Korean output | **done (mock + live)** | `Sprint-Backlog-Translation.md` Sprint 1 |
| #03 Translation | Glossing rule enforcement + LaTeX/citation mask + side-by-side UI | out (Sprint 2) | `Sprint-Backlog-Translation.md` Sprint 2 |
| #04 Monitoring | Temporal cluster + cron + dispatch | out (Sprint 2 onwards) | `Sprint-Backlog-Monitoring.md` |
| #05–#11 | All remaining features | out (Sprint 2+) | other `Sprint-Backlog-*.md` files |
| Ops (§4.6) | Grafana / Alertmanager / runbooks | out (Sprint 3 obligation; intentionally absent here) | AGENTS.md §4.6 |

## Quick start (빠른 실행)

```bash
cd demo
./run.sh
```

`run.sh`는 다음을 자동으로 수행한다:
1. `uv`가 있으면 `uv venv`로, 없으면 `python -m venv`로 `.venv/`를 만든다 (기존 venv는 그대로 재사용 — idempotent).
2. `pyproject.toml`의 런타임 + dev 의존성을 설치한다.
3. 모드(mock / live)를 한 줄 배너로 출력한 뒤 `uvicorn`을 `0.0.0.0:8000`에서 띄운다.

브라우저에서 [http://localhost:8000](http://localhost:8000) 을 열면 데모 SPA가 뜬다 (macOS/Linux는 가능하면 자동으로 열린다).

### 모드 전환

```bash
# mock 모드 (기본) — 인터넷·키 없이 동작
./run.sh

# live 모드 — 실제 Claude 호출
ANTHROPIC_API_KEY=sk-ant-... ./run.sh

# live + 실제 PDF 파싱 — 별도 GROBID 컨테이너가 떠 있어야 한다
ANTHROPIC_API_KEY=sk-ant-... GROBID_URL=http://localhost:8070 ./run.sh
```

`.env.example`을 `.env`로 복사해 두면 `run.sh`가 자동으로 읽는다. `.env`는 `.gitignore`에 포함되어 있으므로 절대 커밋되지 않는다.

## Demo flow (데모 흐름)

FE 수용 시나리오 5단계:

1. **검색 (Search)** — 헤더의 자연어 검색창에 `"attention transformer"` 입력 → arXiv에서 10건 미만의 후보 목록을 받는다. 카드에는 제목·저자·연도·초록 미리보기가 보인다. *(AGENTS.md §3.1 #01a)*
2. **인입 (Ingest)** — 카드의 "PDF 요약" 버튼을 누르면 `/api/ingest`로 `PaperSummary`가 전송된다. 모드가 `live + GROBID_URL`이면 실제 파싱이, 아니면 *abstract-only fallback*이 실행되며 SSE 진행 단계가 표시된다. *(§3.1 #01b)*
3. **결과 확인 (Result)** — 인입이 끝나면 `/api/papers/{id}`가 200을 돌려준다. 섹션 개수·청크 개수가 우측 패널에 표시된다. *(§4.2 — PDF 영속 저장 금지, 모두 메모리)*
4. **요약 (Summary)** — 길이 프리셋 `paragraph` + 관점 `contribution`을 선택한 뒤 "요약" 버튼 → 한국어 단문 요약이 sentence 단위로 출력된다. mock 모드에서는 결정론적 stub, live 모드에서는 Claude Sonnet 호출. 각 sentence 옆에 verifier 라벨(현재는 stub이라 모두 SUPPORTED)이 보인다. *(§3.1 #02, §4.3 verifier port)*
5. **번역 (Translation)** — 요약 패널이나 원문에서 영어 구절을 드래그 → "번역" 버튼 → `한국어(English)` 글로싱이 적용된 `-한다` 체 번역이 나온다. mock 모드는 in-process 사전, live 모드는 Claude 호출. *(§3.1 #03, §6.2 glossing rule, §6.3 학술체)*

전 단계는 인터넷 없이 mock 모드로 검증 가능하다 — `seed/sample-paper.json`을 이용하면 arXiv가 불통이어도 ingest부터 4·5단계까지 그대로 시연된다.

## Module map

`demo/app/` 트리 — AGENTS.md §5.1 디렉터리와 1:1 매핑 (Sprint 1 walking-skeleton에 필요한 노드만 채워져 있고, 나머지는 빈 `__init__.py`로 자리만 잡혀 있다).

```
demo/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI entry; mounts routers + static
│   ├── container.py                     # composition root — wires ports → impls
│   ├── api/                             # thin HTTP surface (allowed to import domain/*)
│   │   ├── routes_search.py             # #01a — POST /api/search
│   │   ├── routes_ingest.py             # #01b — POST /api/ingest, GET /api/papers/{id}
│   │   ├── routes_summary.py            # #02  — POST /api/summary
│   │   └── routes_translation.py        # #03  — POST /api/translate
│   ├── domain/                          # AGENTS.md §5.1 domain modules
│   │   ├── papers/                      # #01a + #01b share this module (§3.2)
│   │   │   ├── models.py                # PaperSummary, Paper, Chunk, Anchor, Sentence
│   │   │   ├── normalizer.py            # rule + LLM query normalizer
│   │   │   ├── search.py                # MultiDBRouter + ArxivAdapter
│   │   │   └── ingest.py                # PDF fetch → GROBID/fallback → chunk + store
│   │   ├── summarization/               # #02 — presets, prompts, retriever, service
│   │   │   ├── presets.py
│   │   │   ├── prompts.py
│   │   │   ├── retriever.py
│   │   │   └── service.py
│   │   └── translation/                 # #03 — span resolver + prompt builder
│   │       ├── prompts.py
│   │       └── span.py
│   ├── crosscutting/                    # cross-cutting concerns (§4)
│   │   ├── verifier/                    # §4.3 — sentence-level entailment port
│   │   │   └── port.py                  # Sprint 1: AlwaysSupportedVerifier stub
│   │   ├── anchor/                      # §4.4 — [§n.m] / [p.X ¶Y] validator
│   │   │   └── validator.py
│   │   ├── glossary/                    # §6.2 — Korean(English) glossing store
│   │   │   ├── protocol.py
│   │   │   └── store.py
│   │   ├── ratelimit/                   # §4.5 — TokenBucket + tenacity retry
│   │   │   └── backoff.py
│   │   ├── events/                      # §5.2 — sole domain-↔-domain channel
│   │   │   └── bus.py
│   │   └── audit/                       # placeholder — Sprint 3 (§4.2 PDF audit)
│   └── infra/                           # adapters to external systems
│       ├── llm/                         # §4.1 — sole owner of prompt-cache keys
│       │   ├── protocol.py              # LLMPort
│       │   ├── cache_keys.py            # derive_cache_key (domain MUST NOT call)
│       │   ├── claude.py                # live ClaudeAdapter
│       │   └── mock.py                  # deterministic offline LLM
│       ├── http/
│       │   └── arxiv.py                 # async arXiv Atom-feed client
│       ├── grobid/
│       │   ├── client.py                # POST /api/processFulltextDocument
│       │   └── tei_parser.py            # TEI XML → list[Section]
│       ├── embedding/                   # placeholder — Sprint 2 Owner port
│       └── storage/
│           └── memory.py                # PaperStore — in-memory only (§4.2)
├── web/
│   └── index.html                       # vanilla-JS SPA, served via /static
├── seed/
│   └── sample-paper.json                # "Attention Is All You Need" PaperSummary
├── scripts/
│   └── smoke.sh                         # 6-step curl smoke test
├── tests/                               # pytest (asyncio_mode = auto)
│   ├── test_search.py
│   └── test_ingest.py
├── pyproject.toml
├── .env.example
├── .gitignore
├── run.sh
└── README.md
```

## Architecture notes

These call out *exactly which AGENTS.md clauses* the walking skeleton already enforces (vs. which are intentionally stubbed for Sprint 1):

- **§4.2 — PDF 영속 저장 금지**: `infra/grobid/client.process_fulltext` streams PDF bytes from `httpx` straight into the GROBID multipart body. No `tempfile`, no `open()`. `infra/storage/memory.PaperStore` keeps the parsed `Paper` in an `asyncio.Lock`-guarded dict only. The `.gitignore` also blocks any `*.pdf` from being staged.
- **§4.3 — Verifier port**: `crosscutting/verifier/port.py` defines `VerifierPort` Protocol and ships an `AlwaysSupportedVerifier` Sprint 1 stub. Domain modules import the port type only — they never instantiate a concrete verifier (the composition root in `container.py` does that). Sprint 2 swaps in Claude Haiku without touching domain code.
- **§4.4 — Anchor**: every search hit, chunk, and (eventually) sentence carries an `Anchor` (`section_id` / `page` / `paragraph`). `crosscutting/anchor/validator.py` parses both `[§n.m]` and `[p.X ¶Y]` forms; Sprint 2 will add "exists-in-paper" enforcement.
- **§5.1 — Modular monolith**: every subtree under `app/` maps to a §5.1 directory. Empty `__init__.py` directories (e.g. `infra/embedding/`, `domain/exploration/`) intentionally reserve the names for Sprint 2+ features.
- **§5.2 — No cross-domain imports**: `domain/papers/` MUST NOT import `domain/summarization/` or `domain/translation/`. `tests/test_search.py::test_arxiv_adapter_boundary_imports_are_safe` greps the source to enforce this until import-linter lands.
- **§6.2 — Glossing rule**: `crosscutting/glossary/store.InMemoryGlossary` pre-seeds the common AI terms (transformer→트랜스포머, attention→주의, …). Both `#02 summarization` and `#03 translation` read from the same store via `GlossaryPort` so first-occurrence decisions stay consistent across features.
- **§4.1 — Cache-key ownership**: `infra/llm/cache_keys.derive_cache_key` is the **only** code that derives prompt-cache keys; domain modules call `LLMPort.complete()` and never see a key. Mock and live adapters both honour the same `cache_hit` semantics.

## Testing

`pytest`는 `pyproject.toml`의 `asyncio_mode = "auto"` + `testpaths = ["tests"]` 설정으로 동작한다.

```bash
cd demo
./run.sh                       # (한 번만) — venv + 의존성 설치
.venv/bin/pytest               # 전체 테스트
.venv/bin/pytest -k search     # 부분 실행
.venv/bin/pytest -m integration  # (선택) 외부 의존성 있는 통합 테스트
```

`uv`가 있다면 `uv run pytest`로 한 줄로도 실행 가능하다.

## Known limitations

Sprint 1 walking-skeleton — 다음은 의도적으로 **빠져 있다**.

- **No Qdrant / embedding** — vector search & rerank는 `#01a` Sprint 2 항목. 현재 `MultiDBRouter`는 arXiv adapter 1개만 호출한다. `infra/embedding/`은 빈 패키지.
- **No Temporal** — `#04 Monitoring`은 AGENTS.md §5.3 W7 도입 시점부터 Temporal을 강제한다. 현재 데모에는 워크플로우 엔진이 전혀 없다.
- **No Redis** — `crosscutting/glossary`와 `infra/storage`는 모두 `dict` 기반 in-memory 구현이다. 프로세스가 죽으면 상태도 사라진다. Sprint 2 (#01a 행 4)에서 Redis 캐시가 들어온다.
- **No real verifier** — `crosscutting/verifier/AlwaysSupportedVerifier`는 evidence가 있으면 `SUPPORTED`, 없으면 `NOT_FOUND`만 돌려준다. 4-way 분류 (§4.3)는 `#02` Sprint 2 Owner port 작업에서 들어온다.
- **Single DB** — arXiv 하나만 붙어 있다. Semantic Scholar / OpenAlex / Crossref / PubMed adapters는 `#01a` Sprint 2 항목 1.
- **No `crosscutting/ops`** — `AGENTS.md` §4.6는 모든 기능 Sprint 3에 Grafana / Alertmanager / runbook 행을 의무화하지만, 5주 프로토타입에는 의도적으로 제외 (`Sprint-Capacity-Plan.md` §3.1 결과 표).
- **Anchor enforcement loose** — `Anchor.exists_in()`은 section_id 일치만 검증한다. GROBID 인덱스 매칭은 `#02` Sprint 2 anchor Owner port에서 추가된다.
- **No glossing-rule enforcement** — `한국어(English)` 첫등장 강제는 `#03` Sprint 2 항목. mock 모드는 사전 치환만, live 모드는 프롬프트에 "글로싱 적용" 지시가 들어가 있지만 검증·재처리는 없다.
- **No audit log** — `crosscutting/audit/`는 빈 디렉터리. PDF 잔존 0건 감사 (§4.2)와 quota 메트릭 (§4.5)은 Sprint 3 항목.
