# Sprint Backlog — DoD 검증 도구 매핑

각 row의 DoD는 *관측 가능*해야 한다 (AGENTS.md §4.6 부속 규약). 본 문서는 DoD 패턴별 측정 도구를 통일해, sprint review에서 "이 행 끝났나?" 질문이 객관 판정 가능하도록 정의한다.

> Sprint planning checklist: 행마다 (1) DoD의 측정 메트릭/시드 시나리오, (2) 해당 도구가 인프라에 존재, (3) 없다면 도구 셋업이 같은/이전 sprint에 포함되어 있는지 확인. "없음" 응답이 하나라도 있으면 해당 행에 **+2 pt (infrastructure spike)** 추가.

---

## 1. Test pyramid

### 1.1 Unit tests — `pytest`

**커버 범위**: 모든 `domain/*/` 비즈니스 로직.

**DoD 패턴**:
- "N unit 시나리오 통과"
- "단위 테스트", "round-trip 무손실"
- "정확도 N%+ 시드 데이터" (deterministic 룰 기반)

**셋업**:
- `pytest` + `pytest-asyncio` (Temporal/asyncio 코드)
- `factory_boy` for 테스트 데이터
- `pytest-cov` — module 별 80%+ coverage CI gate

**적용 예시**:
- #01a Search Sprint 1 Query Normalizer "동의어/필터 expand 10 unit 시나리오 통과"
- #02 Summarization Sprint 1 length preset "12 (3×4) 프리셋 정의 + 토큰 cap 단위 테스트"

### 1.2 Integration tests — `pytest + testcontainers + VCR`

**커버 범위**: 모든 `infra/*/` 어댑터 + cross-module 흐름.

**DoD 패턴**:
- "통합 테스트 N건 통과"
- "auth/rate limit 검증"
- "API 호출 + 정규화"

**셋업**:
- `testcontainers-python` — GROBID, Qdrant, Postgres, Redis Docker 컨테이너
- `vcr.py` — 외부 LLM API 카세트 (Anthropic / OpenAI 비용 방지)
- `pytest-recording` — 카세트 모드 (record-once, replay-many)

**적용 예시**:
- #01a Sprint 2 4 DB 어댑터 "각각 통합 테스트 통과 + auth/rate limit 검증" → testcontainers + 각 DB stub server
- #01b Sprint 1 GROBID 어댑터 "PDF 1편 → 섹션/문단/문장 JSON 출력" → testcontainers GROBID 컨테이너

### 1.3 Load tests — `Locust` or `k6`

**커버 범위**: 부하 또는 동시성 SLO 검증이 필요한 행.

**DoD 패턴**:
- "N개 동시 실행 부하 통과"
- "p99 < Nms"
- "throughput N rps"

**셋업**:
- `Locust` — Python 친화 (대부분 백엔드가 Python)
- 전용 staging 환경 (production data 격리)
- baseline 메트릭 capture → 회귀 회귀 비교

**적용 예시**:
- #04 Sprint 3 tests "1만 잡 동시 실행 부하 통과" → Locust 1만 user spawn
- #01a Sprint 3 audit "quota 초과 시 429" → Locust burst 시나리오

### 1.4 E2E tests — `Playwright`

**커버 범위**: 모든 frontend 행.

**DoD 패턴**:
- "UI [상호작용] + 빈/에러 상태 처리"
- "hover < Nms"
- "drag-drop 4 컬럼 + 수정 이벤트"

**셋업**:
- `Playwright` + headless chromium
- per-feature smoke + critical user flow
- visual regression — `playwright-test-snapshot`

**적용 예시**:
- #02 Sprint 2 frontend "sentence hover → span 하이라이트 < 100ms" → Playwright + performance API
- #11 Sprint 2 Kanban "DnD 4 컬럼 + 수정 이벤트 → API" → Playwright + API mock

---

## 2. Quality gates

### 2.1 Schema validation — `Pydantic`

**DoD 패턴**:
- "Pydantic 검증 통과"
- "structured JSON 출력"
- "LLM tool-call 1회로 완성"

**셋업**:
- `Pydantic v2` — 모든 LLM tool-call 출력 강제 검증
- 실패 시 1회 재시도 (재시도 로깅), 2회 실패 시 사용자 에러 응답
- 스키마는 `domain/*/schemas.py`에 통일 위치

### 2.2 Architecture — `import-linter`

**DoD 패턴**:
- "import-linter 통과"
- AGENTS.md §5.2 모듈 경계 강제

**셋업**:
- `import-linter` 설정 파일 (`.importlinter`)
- 룰: `domain/A`가 `domain/B`를 import하면 fail
- 룰: `domain/*`이 `infra/llm` 외에 cache key를 생성하면 fail (§4.1)
- CI gate — 위반 시 PR block

### 2.3 LLM eval — `Promptfoo`

**DoD 패턴**:
- "정확도 N%+ 시드 데이터"
- "4-way 라벨 정확도"
- "분류 정확도 80%+"

**셋업**:
- `Promptfoo` + golden set per LLM 호출 종류 (verifier / classifier / synthesizer)
- 행별 threshold는 DoD에서 명시 (e.g. #04 분야 분류기 "85%+")
- regression CI — 임계 미만 시 fail

**적용 예시**:
- #02 Sprint 2 verifier "4-way 라벨 정확도 90%+" → Promptfoo + 시드 (sentence, evidence, expected_label) 100건
- #09 Sprint 1 분야 분류기 "85%+ 시드 데이터" → Promptfoo + 4-class 시드

### 2.4 CI gate — `GitHub Actions`

모든 위의 gate는 CI workflow에 통합:
1. pytest (unit + integration) + coverage
2. import-linter
3. Pydantic 스키마 검증 (테스트 내포)
4. Promptfoo eval (LLM 평가)
5. Playwright E2E (head full job, scheduled + on PR)
6. Locust (scheduled, weekly)

PR block 조건: 1+2+3+4 실패 시. Playwright/Locust는 reporting only (별도 alert).

---

## 3. Metrics & observability

### 3.1 Prometheus + Grafana

**DoD 패턴**:
- "Grafana N 패널 + 임계 알림"
- "Prometheus 메트릭 노출"
- "임계 알림"

**셋업**:
- 각 service에 `prometheus_client` 익스포터
- Grafana 인스턴스 → service-discovery
- 대시보드 1개 per feature (Ops row의 패널 개수만큼)
- Alertmanager 룰 — Ops row에서 명시한 임계값

**필수 대시보드**:
- search, ingest, summarization, translation, monitoring, exploration, research-gap, project-trend, citation, reproducibility, reading, priority — 각 1개

### 3.2 Anthropic usage API

**DoD 패턴**:
- "LLM 비용 대시보드"
- "$N/호출 측정"
- "캐시 히트율 N%+"

**셋업**:
- Anthropic usage API → 자체 Prometheus exporter (분 단위 sync)
- Grafana cost panel per feature
- Per-feature 일간 비용 budget alert (e.g. #06 $12/분석 임계)

**중요**: 캐시 히트율은 Anthropic의 cache_read_input_tokens / (cache_read + cache_creation) 비율로 측정. AGENTS.md §4.1에 따라 `infra/llm`이 단독 측정 책임.

### 3.3 Redis MONITOR + counters

**DoD 패턴**:
- "캐시 히트율 N%+"
- "24h 자동 만료"

**셋업**:
- Redis MONITOR sampling (운영 환경에서는 5% sampling — 풀 MONITOR는 부하 큼)
- Prometheus counters for hit/miss per cache namespace
- 명확한 namespace: `search:`, `glossary:`, `intent:`, `repro:`, etc.

---

## 4. Runbooks (필수 산출물)

각 Ops 행에서 참조하는 runbook은 `/runbooks/` 디렉터리에 배치:

| Runbook | 작성 책임 | 트리거 | 핵심 액션 |
|---|---|---|---|
| `search-db-failure.md` | #01a | arXiv/S2 outage | DB priority fallback, 사용자 알림 정책 |
| `grobid-down.md` | #01b | GROBID worker unresponsive | worker restart, in-flight job recovery |
| `temporal-worker-down.md` | #04 | Temporal worker crash | worker restart, schedule 재가동 |
| `llm-cost-spike.md` | #02 / #06 / #07 | 일간 Anthropic 비용 임계 | 호출 throttle, 비용 알림, 비용 분포 분석 |
| `ses-reputation-drop.md` | #04 | SES 평판 < 90 | warm-up restart, channel failover to FCM/Slack |
| `zdr-off-detected.md` | #07 | ZDR header 누락 호출 발생 | 즉시 호출 차단, 사용자 알림, 후처리 audit |
| `glossary-violation.md` | #03 | 동일 세션 내 용어 비일관 | glossary 재처리 + 사용자 알림 |
| `explainer-cost-spike.md` | #05 | Explainer 호출 비용 임계 | lazy 모드 강제, top-K 축소 |
| `openalex-outage.md` | #08 | OpenAlex API 다운 | S2 fallback 활성화, 캐시 TTL 연장 |
| `github-api-throttle.md` | #09 | GitHub API rate limit hit | 인증 토큰 rotate, 재검증 지연 |
| `safety-guard-violation.md` | #10 | system prompt 가드 위반 출력 감지 | 출력 거부 로그, 가드 룰 강화 |
| `bandit-weight-stale.md` | #11 | 가중치 1년 미갱신 사용자 발생 | 가중치 초기화 트리거, 사용자 캘리브레이션 UX |

**총 12개 runbook**. Sprint 3 Ops 행 종료 조건의 일부.

---

## 5. Sprint planning checklist

각 행 sprint planning 시 확인:

| 확인 항목 | 통과 기준 |
|---|---|
| DoD에 측정 가능 메트릭/시드 명시? | 정량 임계 또는 시드 시나리오 수 명시 |
| 측정 도구 인프라 존재? | 표 1-3 도구 중 하나에 매핑 가능 |
| 도구가 인프라에 없으면 셋업 sprint 포함? | 셋업 행 추가 또는 이전 sprint에서 완료 |
| DoD가 다른 행에 의존? | depends-on 태그 명시 |
| 비용 측정 필요한 행에 budget alert? | Ops 행이 해당 비용 대시보드 포함 |

전체 미통과 항목 1개당 **+2 pt (infrastructure spike)** 추가. spike가 누적되면 sprint 분할 신호.

---

## 6. 도구 도입 우선순위 (5주 프로토타입 기준)

1주차 (week 1):
- pytest + pytest-asyncio + factory_boy
- testcontainers (GROBID, Qdrant, Redis, Postgres 컨테이너 정의)
- import-linter (AGENTS.md §5.2 룰 적용)
- Pydantic v2

2주차 (week 2):
- Prometheus + Grafana (#01a 첫 대시보드)
- VCR.py (LLM 호출 카세트)
- GitHub Actions CI (1+2+3 통합)

3주차 (week 3):
- Anthropic usage API exporter
- Playwright (#01a frontend)
- Promptfoo (#02 verifier 시작 시)

4주차 (week 4):
- Locust staging 환경
- Alertmanager
- Sentry (safety 가드 위반 로깅 등)

5주차 (week 5):
- 첫 runbook 3-4개 (#01a / #01b / #02)
- DoD 측정 회고

이후 sprint마다 사용 패턴 따라 추가 도입.
