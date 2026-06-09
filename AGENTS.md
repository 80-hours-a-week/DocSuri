# AGENTS.md — Semantic Paper Workbench 시스템 헌법

> 본 문서는 멀티에이전트 토폴로지, 횡단 관심사, 출력 규약의 **단일 진리 출처(SoT)** 다.
> 모든 `domain/<name>/`, `crosscutting/`, `infra/`, `workflows/` 코드는 본 문서의 §1–§6을 따른다.
> 변경 시: PR에 §번호 명시 + `feature-specs/*` 충돌 여부 점검 필수.

---

## §1. Mission & Non-goals

### §1.1 Mission

AI 연구자·실무자가 **방대한 논문 흐름에서 자기 연구에 필요한 신호만 빠르게 골라내고, 핵심을 이해하고, 자기 위치를 파악할 수 있게** 하는 *소비(consumption) 도구*.

해결 대상은 다음 두 가지:

1. **검색-검증-요약 시간 과다**: 평균 연구 시간의 ~20%가 논문 리서치에 소진. 신입생은 더 큼.
2. **재현·중복·트렌드 불확실성**: 찾은 논문조차 (a) 재현 불가, (b) 자기 아이디어 중복 여부 모호, (c) 분야 트렌드 따라잡기 실패.

### §1.2 Non-goals (명시적 제외)

- **논문 작성(writing) 보조**. outline 생성, 본문 초안, draft 윤문은 본 시스템 책임 범위가 아님.
- **표절 검사 / 학술 부정 탐지**. 외부 도구(iThenticate 등) 위임.
- **공식 동료 검토 대체**. 시뮬레이션은 학습용 보조이며 실제 reviewer를 대체하지 않음.
- **공개 랭킹/리더보드**. 시스템의 모든 점수·분류·평가는 *개인 사용자 결과*로 제한 (§4.2 격리).

### §1.3 Non-goal 충돌 처리

기능 #10 (Research Reading Assistant)은 §1.2와 표면적으로 충돌. 해소책은 `feature-specs/10-research-reading-assistant.md`에서 **"reading 한정 재정의(옵션 C)"** 로 적용. 옵션 A(미션 확장)로의 전환은 §1.1 개정과 PR 리뷰 거쳐야 함.

---

## §2. Target Personas

### §2.1 박지훈 — 28세, AI 대학원 박사과정 3학기

- **사실**: 학위 논문 주제 탐색 중. 주 10시간 이상 문헌 조사.
- **행동**: DB 시스템에 무계획적 키워드 반복 검색. 생성형 AI에 질문.
- **목표**: (a) 자기 주제가 이미 존재하는지 확인, (b) 분야 트렌드 파악, (c) 재현 가능한 선행 논문 식별.
- **골칫거리**: 검색 시간 대비 효용 낮음. 재현 불가능한 논문이 많아 실험·작성 시간 부족.

### §2.2 30대 R&D 연구원

- **사실**: 본업으로 일정 과부하. 논문 투입 시간을 줄이고 싶음.
- **행동**: 검증·요약을 LLM에 위임. 직접 검색 회피.
- **목표**: 관심 분야 트렌드 자동 알림, Seminal Paper 필터링.
- **골칫거리**: 트렌드에 뒤쳐짐. 검증 비용 큼.

### §2.3 대학원생 — 프로젝트 레퍼런스 탐색

- **사실**: 프로젝트 작성을 위해 레퍼런스 논문 필요.
- **행동**: 검색 결과의 무관성·길이 때문에 빠르게 포기.
- **목표**: 프로젝트 연관성 높은 논문 확보, 전체 요약, 기존 논문과의 독립성 확인.
- **골칫거리**: 무관 논문 다수. 본문 길어 파악 어려움.

### §2.4 일반 입문자 (40대 AI 입문 사용자)

- **사실**: 기술 배경 없이 AI 본질이 궁금해 논문 검색.
- **목표**: "AI가 뭐길래" — 본질을 쉽게 알려주는 입구.
- **골칫거리**: 답변이 어렵거나 부정확.
- **시스템 대응**: §6.2 glossing rule + #02 요약의 1줄 프리셋이 이 페르소나의 진입점.

### §2.5 페르소나-기능 매핑

| 페르소나 | 핵심 기능 (우선순위) |
|---|---|
| §2.1 박지훈 | #06 공백/아이디어, #09 재현성, #08 인용 계보 |
| §2.2 R&D 연구원 | #04 모니터링, #11 우선순위 분류, #02 요약 |
| §2.3 프로젝트 대학원생 | #01 검색, #05 유사 논문, #07 프로젝트 통합 |
| §2.4 입문자 | #02 요약(1줄), #03 번역 |

---

## §3. Feature Topology

총 11개 기능. 단계적 도입 (`priorities.html` 26주 타임라인).

### §3.1 빌드 우선순위

```
01a → 01b → 02 → 11 → 09 → 03 → 04 → 08 → 05 → 07 → 06 → 10
```

근거: (a) #01a 검색·#01b 인입은 모든 기능의 토대 — sprint planning 편의를 위해 분리됐으나 단일 `domain/papers/` 모듈, (b) #02·#11은 단위 비용 최저·재사용 빈도 최고, (c) #04는 SNS+SQS 도메인 fan-out 도입 진입(§5.3), (d) #10은 §1 충돌로 마지막.

**#01 분리 사유 (2026-06-08)**: 원본 spec(`feature-specs/01-paper-search-and-ingest.md`)이 검색과 인입을 한 묶음으로 다루나, sprint planning 단위가 너무 커져 ship 가능 시점이 흐려짐. #01a Search는 단일 DB로 5주 안에 walking skeleton 가능 (48 pt), #01b Ingest는 GROBID + Qdrant + 청크 anchor 무거운 인프라(40 pt)로 별도 sprint cadence 필요. 모듈은 분리하지 않음 — `domain/papers/search.py` + `domain/papers/ingest.py` 동일 모듈 내 분할.

### §3.2 기능 그룹

| 그룹 | 기능 | 도메인 모듈 |
|---|---|---|
| 기반 | #01a 검색 / #01b 인입 | `domain/papers/` (sprint planning 분리, 모듈 단일) |
| 이해 보조 | #02 요약 / #03 번역 | `domain/summarization/`, `domain/translation/` |
| 탐색 | #05 유사 논문 / #08 인용 계보 | `domain/exploration/`, `domain/citation/` |
| 분석 | #06 공백·아이디어 / #07 프로젝트 통합 | `domain/analysis/` |
| 평가·우선순위 | #09 재현성 / #11 우선순위 분류 | `domain/reproducibility/`, `domain/reading_priority/` |
| 자동화 | #04 모니터링·알림 | `domain/monitoring/` |
| 읽기 보조 | #10 Research Reading Assistant | `domain/reading/` |

---

## §4. Cross-cutting Policies

### §4.1 Cache Policy

- **외부 API 응답 캐시**: Redis, 24h TTL 기본. 동일 쿼리·동일 매개변수 재호출 시 캐시 우선.
- **임베딩 캐시**: 텍스트 hash → 임베딩. 영속 보관. 재계산 금지.
- **LLM prompt cache**: Anthropic SDK `cache_control: ephemeral`. 5분 TTL 기본, extended cache(1h beta)는 비용 분석 후 옵트인.
- **캐시 키 책임**: `infra/llm/`만 prompt cache key 생성/관리. 도메인 모듈은 cache key를 *읽지 않음*.
- **캐시 미스 로깅**: 미스율 5% 초과 시 알림 (재호출 비용 폭증 지표).

### §4.2 Storage / IP / License Policy

- **PDF 영속 저장 금지**. 세션 범위 in-memory 처리. 사용자가 명시적으로 "내 라이브러리에 저장"을 선택해도 본인 격리 저장소만 사용.
- **사용자 데이터 격리**: user_id별 namespace. LLM 컨텍스트 메모리 비활성. 한 사용자 입력이 다른 사용자 prompt에 절대 등장 금지.
- **비공개 프로젝트(#07)·미공개 아이디어(#06, #10)**: Anthropic Zero Data Retention(ZDR) 옵션 강제. 사용자 동의 UI 게시.
- **라이선스 검증**: paywall PDF는 Unpaywall로 OA 사본 우선. paywall 직접 다운로드는 ToS 위반 가능 — 사용자 본인 인증된 접근에 한해 처리.
- **공개 금지 산출물**: 점수·분류·평가(특히 #09 재현성, #11 분류)는 *개인 결과*. 공개 랭킹/리더보드 금지.
- **GDPR/개인정보**: 구독 패턴(#04)·연구 일지(#10)는 민감 정보. 익명화·삭제 권리 보장.

### §4.3 Verifier — Sentence-level Entailment

**모든 LLM 산출물 sentence는 횡단 verify를 거친다.**

- **포트 경계**: `crosscutting/verifier/` 단일 인터페이스. 도메인 모듈은 verifier 구현 세부를 모름.
- **계약**:
  - 입력: `(generated_sentence, evidence_spans)`
  - 출력: `Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "NOT_FOUND"]` + confidence
- **LLM**: 기본 Claude Haiku (저비용 entailment). 비판적 검토 모드(#02)·negative claim(#06)은 Sonnet 승격.
- **Sampling**: 단순 번역(#03)·계보 분류(#08)는 10% 무작위 verify 옵트인 가능. 단, 4-way label 강제 기능(#02, #09)은 100% verify 의무.
- **실패 처리**: `UNSUPPORTED` / `NOT_FOUND` 발생 시 (a) 사용자 UI에 라벨 배지 표시, (b) regenerate 옵션 제공.
- **금지**: 도메인 모듈이 자체 verifier 호출 우회 금지. PR 리뷰 시 import-linter로 강제.

### §4.4 Anchor Format

- **형식**: `[§n.m]` (섹션) 또는 `[p.X ¶Y]` (페이지·문단).
- **부착 대상**: §6.1에 명시된 모든 산출물.
- **검증**: `crosscutting/anchor/` Anchor Validator가 anchor가 실제 span을 가리키는지 확인. 위조(존재하지 않는 §) 발견 시 거부 + 재생성.

### §4.5 Rate Limit & 외부 API 정책

- **per-DB quota**: arXiv OAI-PMH 권장 경로 사용. S2 100rpm 무인증, PubMed 3rps. tenacity backoff 의무.
- **사용자별 quota**: "검색 컨텍스트 다양화"가 50개 DB 호출로 증폭 방지. 사용자당 분당 호출 cap.
- **per-feature quota**: 비싼 기능(#06 ~$12/회, #07 ~$7/회)은 일간 호출 cap + 비용 경고 UI.

### §4.6 Operational SLO Conventions

**모든 기능 Sprint 3에는 `crosscutting/ops/` 행이 의무.** 운영 가시성 없는 기능은 배포 금지.

각 Ops 행이 제공해야 할 산출물:
- **SLO**: 기능별 latency p95/p99 + error rate 임계값
- **Grafana 대시보드**: 최소 3 패널 (latency, error rate, 비용 또는 외부 의존성 상태)
- **Alertmanager 룰**: 최소 2 룰 (SLO 위반, 외부 의존성 다운)
- **Runbook**: `/runbooks/<feature>-<scenario>.md` — 사고 대응 절차

기능별 Ops 행 책임 범위:

| 기능 | 핵심 SLO | 핵심 Alert |
|---|---|---|
| #01a Search | p95 검색 < 500ms, DB error < 1% | DB API 장애, S2 rate limit 초과 |
| #01b Ingest | 인입 < 5min, GROBID 실패 < 5% | GROBID worker 다운, Qdrant 디스크 90%+ |
| #02 Summarization | 요약 < 30s, verify p95 < 5s | LLM 비용 임계, 캐시 히트율 < 50% |
| #03 Translation | 번역 < 10s | glossary 일관성 위반 |
| #04 Monitoring | 잡 99% 성공, 발송 < 5min | Resend/SES 평판, SQS DLQ depth > 0, Celery worker 다운 |
| #05 Exploration | 탐색 < 3s, Explainer < 10s | Qdrant 인덱스 헬스 |
| #06 Research-Gap | 분석 < 1h, 재시도 < 3회 | Opus $12/분석 임계 |
| #07 Project-Trend | 분석 < 30min | ZDR off 감지 (IP 누출 방지) |
| #08 Citation | depth=2 < 10s | OpenAlex API 가용성 |
| #09 Reproducibility | 평가 < 5min | GitHub API rate limit |
| #10 Reading | 서브기능 < 10s | safety 가드 위반 |
| #11 Priority | 분류 < 2s | Bandit 가중치 stale |

Ops 행 없는 기능은 Sprint 3 종료 거부 — `crosscutting/ops`는 모든 기능에 의무 횡단 관심사.

**검증 도구 매핑**: 각 DoD의 측정 도구는 `Sprint-Backlog-Verification-Tools.md`에 통합 정의 (pytest / testcontainers / Promptfoo / Locust / import-linter / Prometheus 등).

---

## §5. Architecture

### §5.1 모듈러 모놀리스

단일 FastAPI 앱. 디렉터리 경계:

```
domain/
  ├ papers/          (#01)
  ├ summarization/   (#02)
  ├ translation/     (#03)
  ├ monitoring/      (#04)
  ├ exploration/     (#05)
  ├ analysis/        (#06, #07 공유)
  ├ citation/        (#08)
  ├ reproducibility/ (#09)
  ├ reading/         (#10)
  └ reading_priority/(#11)
crosscutting/
  ├ verifier/        (§4.3)
  ├ anchor/          (§4.4)
  ├ glossary/        (§6.2)
  ├ ratelimit/       (§4.5)
  ├ audit/           (감사 로그)
  ├ safety/          (§1.3 가드)
  ├ bandit/          (#11 학습)
  └ events/          (도메인 간 통신 단일 경로)
infra/
  ├ llm/             (§4.1 cache key 단독 책임)
  ├ vectordb/
  ├ grobid/
  ├ citation_graph/  (OpenAlex)
  ├ code_embed/      (#07)
  ├ graphdb/         (#08)
  ├ http/
  ├ github/
  ├ notification/    (#04 dispatch)
  ├ storage/         (Postgres, Redis)
  └ messaging/       (§5.3 SNS+SQS)
workflows/
  ├ monitoring_cron/     (#04)
  ├ gap_analysis/        (#06)
  ├ project_analysis/    (#07)
  └ repro_evaluation/    (#09)
```

### §5.2 모듈 간 통신

- **도메인 간 직접 import 금지**. `domain/A`가 `domain/B`를 import하면 안 됨.
- **유일한 통로**: `crosscutting/events/` (event bus). 결합도 차단.
- **검증**: import-linter 또는 ruff TID 규칙으로 자동 검증. CI에서 위반 시 PR 거부.

### §5.3 도메인 간 통신 (Celery + SNS/SQS 단일 채택)

- **결정 (2026-06-09)**: Temporal 도입 룰 폐기. AWS native `SNS + SQS` 팬아웃과 `Celery + Redis broker` 워커 실행으로 통일. 사유는 §9 changelog 참조.
- **계층 분리**:
  - **`infra/messaging/`** — 도메인 간 단일 통로. `crosscutting/events/`가 발행하는 도메인 이벤트는 SNS Topic 1개에 게시되고, 관심 도메인은 자기 SQS Queue를 subscribe한다.
  - **`infra/celery/`** — 워커 실행 엔진. SQS 메시지 핸들러가 Celery task로 dispatch되거나, 단발 ingest·임베딩(#01b)처럼 fan-out 불필요한 경우 Celery group을 직접 사용한다.
- **의무화 대상**: #04, #06, #07, #09. 이 4개는 SNS Topic 발행 + 전용 SQS Queue 소비로 stateful pipeline을 구성한다.
- **DLQ / Retry**: 모든 SQS Queue는 DLQ 필수. Celery task의 `autoretry_for` + `retry_backoff`는 `infra/celery/policies.py`에 단일 정의 후 도메인이 import.
- **Karpenter 연동(미래)**: SQS `ApproximateNumberOfMessagesVisible` 메트릭이 노드 프로비저닝 트리거 (단, EKS 도입 sprint에서만 활성화).
- **금지**: 동일 이벤트를 두 경로(SNS+SQS / Celery group)로 동시 발행. 한 도메인 이벤트는 정확히 하나의 통로로만.

### §5.4 신규 기능 추가 규칙

- 새 기능은 **새 `domain/<name>/` 모듈**로만 추가.
- `infra/`·`crosscutting/`에 신규 코드 0줄이 목표. 건드려야 하면 **추상화가 새고 있다는 신호** — 설계 리뷰 트리거.

---

## §6. Output Conventions

### §6.1 Anchor 강제

- 산출물의 **모든 sentence**에 `[§n.m]` 또는 `[p.X ¶Y]` 인용 필수.
- 적용 기능: #02 요약, #03 번역, #05 유사 설명, #06 공백 진술, #07 권장, #08 의도 분류, #09 평가 항목, #10 모든 서브기능, #11 rationale.
- 미부착 sentence는 UI에 회색 처리 + 경고 배지.

### §6.2 Glossing Rule

- **도메인 용어 첫 등장 시**: `한국어(English)` 병기. 예: `주의(attention)`.
- **두 번째 등장 이후**: 한국어만 (사용자 옵션으로 항상 병기 가능).
- **세션 누적**: `crosscutting/glossary/`에 세션별 사전 누적. TTL 24h.
- **일관성**: 한 번 결정된 한국어 표기는 동일 세션 내 모든 산출물에 동일 적용 (#02 요약 ↔ #03 번역 공유).
- **사용자 수정**: glossary 수정 시 과거 산출물 재처리 옵션 제공.

### §6.3 종결형 (학술체)

- 한국어 산출물 종결형: `-한다` 체 통일.
- 능동/수동: 원문 보존 우선. 한국어 자연성 vs 학술 정확성 trade-off 시 **literal-first, idiomatic-second**.
- LaTeX 수식·인용 번호(`[12]`)·표 구조: 통과(pass-through), 번역 금지.

### §6.4 길이 제약

- #02 요약 프리셋: TL;DR(1줄) / 문단(150-200자) / 페이지(800-1200자).
- 사용자 요청 길이 초과 시 post-trimmer로 컷.
- 100자 이상 연속 직역 금지 (§1.2 표절 경계).

### §6.5 구조화 출력

- LLM JSON 출력 스키마: `{sentences: [{text, anchor, verify_label, confidence}], glossary_additions: []}`.
- UI 렌더링·verify·glossary 갱신이 한 응답에서 일괄 처리됨.

---

## §7. Team Ownership

### §7.1 결정 배경

모듈러 모놀리스(§5.1)는 **팀 병렬 개발을 위한 디렉터리 경계와 import-linter 강제를 이미 제공**한다. MSA 전환은 (a) §4.1/§4.3 cross-cutting verifier RPC 비용, (b) §4.6 Ops 행 비선형 증가, (c) 인프라 셋업 3–4주 매몰비용을 발생시키므로 **본 단계에서 채택하지 않는다.** 대신 본 §7에서 *누가 무엇을 책임지는지*를 명문화해 모놀리스 안에서 명확한 ownership을 보장한다.

재검토 시점: §5.3 SNS+SQS fan-out 도입 이후 워커 노드가 자연스럽게 분리되거나, 팀이 5팀 이상으로 확장될 때.

### §7.2 Feature Owner 매트릭스

| # | 기능 | 도메인 모듈 | Owner | Backup |
|---|---|---|---|---|
| 01a | Search | `domain/papers/search.py` + `normalizer.py` | `@team-search` | `@team-ingest` |
| 01b | Ingest | `domain/papers/ingest.py` + `infra/grobid/` + `infra/pdf/` | `@team-ingest` | `@team-search` |
| 02 | Summarization | `domain/summarization/` | `@team-summary` | `@team-translation` |
| 03 | Translation | `domain/translation/` | `@team-translation` | `@team-summary` |
| 04 | Monitoring | `domain/monitoring/` + `workflows/monitoring_cron/` | `@team-monitoring` | `@team-platform` |
| 05 | Exploration | `domain/exploration/` | `@team-exploration` | `@team-citation` |
| 06 | Research-Gap | `domain/analysis/` (gap-side) + `workflows/gap_analysis/` | `@team-analysis` | `@team-summary` |
| 07 | Project-Trend | `domain/analysis/` (project-side) + `workflows/project_analysis/` | `@team-analysis` | `@team-monitoring` |
| 08 | Citation Genealogy | `domain/citation/` + `infra/citation_graph/` + `infra/graphdb/` | `@team-citation` | `@team-exploration` |
| 09 | Reproducibility | `domain/reproducibility/` + `workflows/repro_evaluation/` + `infra/github/` | `@team-repro` | `@team-analysis` |
| 10 | Reading-Assistant | `domain/reading/` | `@team-reading` | `@team-summary` |
| 11 | Priority Classifier | `domain/reading_priority/` + `crosscutting/bandit/` | `@team-priority` | `@team-monitoring` |

**규칙**: 한 PR에서 다른 도메인을 건드리려면 양쪽 Owner가 모두 승인해야 한다. import-linter가 PR을 차단할 가능성이 높지만, 차단을 우회하려는 변경(예: `crosscutting/events/`에 새 이벤트 토픽 추가)은 양쪽 합의 필수.

### §7.3 Owner Port 매트릭스 (횡단)

Owner port는 여러 도메인이 의존하는 단일 인터페이스. Owner는 인터페이스 변경 PR을 단독 결정할 수 없고 **모든 consumer feature owner의 승인을 받아야 한다.**

| Port | 위치 | Owner | Sprint 도입 | 주요 consumer |
|---|---|---|---|---|
| LLM 어댑터 + cache key | `infra/llm/` | `@team-llm-port` | #02 S1 (`infra/llm` Owner row) | #02, #03, #06, #07, #10, #11 |
| Glossary | `crosscutting/glossary/` | `@team-glossary-port` | #03 S1 schema, #02/#03 S2 글로싱 | #02, #03 |
| Anchor Validator | `crosscutting/anchor/` | `@team-anchor-port` | #02 S2 | #02, #03, #05, #06, #07, #09, #10, #11 |
| Verifier | `crosscutting/verifier/` | `@team-verifier-port` | #02 S2 | 모든 LLM 산출 기능 |
| Event Bus | `crosscutting/events/` | `@team-platform` | S1 (필수 기반) | 모든 도메인 |
| Embedding | `infra/embedding/` | `@team-search` (Owner row #01a S2) | #01a S2 | #01b S2+, #05 S2+ |
| Messaging (SNS+SQS) | `infra/messaging/` | `@team-platform` | #04 S1 (W7) | #04, #06, #07, #09 |
| Celery 워커 엔진 | `infra/celery/` | `@team-platform` | #01b S1 | #01b, #02, #04, #06, #07, #09 |
| Citation Graph | `infra/citation_graph/` | `@team-citation` (Owner row #08 S1) | #08 S1 | #08, #05 |

### §7.4 Cross-cutting Role

도메인 외 책임:

- **`@team-platform`** — `main.py`, `container.py`, `api/`, `crosscutting/events/`, `crosscutting/ratelimit/`, `crosscutting/observability/`, `crosscutting/audit/`, `pyproject.toml`, Docker, CI/CD, `infra/messaging/`, `infra/celery/`, `infra/storage/`. SRE/Ops 행 (§4.6)의 default owner.
- **`@team-frontend`** — `web/` 전체. 백엔드 API 계약 변경 시 해당 도메인 owner와 cross-review.
- **`@team-architect`** — `AGENTS.md`, `feature-specs/*`, `architecture.html`, `priorities.html`, `Sprint-Capacity-Plan.md` 의 변경 review. §5/§6 규약 변경은 architect 승인 필수.

### §7.5 PR Review 의례

1. **자동 reviewer 지정**: `.github/CODEOWNERS`가 파일 경로 기준으로 자동 매핑.
2. **단일 도메인 PR**: 해당 owner 1명 + automated checks (import-linter, pytest, ruff) 통과 시 self-merge 가능.
3. **다중 도메인 PR**: 모든 touched-owner 승인 필수. 24h 내 반응 없으면 `@team-architect` 에스컬레이션.
4. **Owner port 변경**: §7.3 consumer 표의 모든 feature owner approval. AGENTS.md §번호로 변경 근거 명시.
5. **AGENTS.md / feature-specs / Sprint-Backlog 변경**: `@team-architect` 승인 필수. 본 §7.1처럼 결정 배경 함께 명시.

### §7.6 Onboarding

신규 팀 합류 시 다음 순서로 권한 부여:

1. AGENTS.md 통독 → §7 ownership 표에서 자기 영역 확인.
2. 자기 owner인 `domain/<feature>/` 디렉터리만 처음 1주 작업.
3. `crosscutting/`·`infra/` 수정이 필요하면 PR 전에 해당 Owner port 담당자에게 사전 협의.
4. Sprint-Backlog의 `[이름]` placeholder를 본인으로 갱신.

---

## §8. References

- `feature-specs/00-overview.md` — 11개 기능 매핑·병합·분할 근거
- `feature-specs/01..11-*.md` — 기능별 파이프라인·기술 스택·비용
- `architecture.html` v1.0 — 5주 프로토타입 시스템도
- `priorities.html` — 26주 빌드 타임라인
- Sprint backlogs — `Sprint-Backlog-{Feature}.md` 11개 파일 (본 문서 §번호 참조)
- `.github/CODEOWNERS` — §7 매트릭스의 GitHub 실행 가능 표현

---

## §9. Change Log

| 날짜 | 변경 | 사유 |
|---|---|---|
| 2026-06-08 | 초안 작성 | sprint backlog 11개에서 §1/§4.1/§4.2/§4.3/§6.2 인용 사용 중이나 본 문서 부재 — 1차 출처 보장 필요 |
| 2026-06-08 | §4.6 Operational SLO Conventions 추가 + §3.1 빌드 순서 #01 → #01a/#01b 분리 + §3.2 그룹 표 갱신 | P2 작업: (a) `crosscutting/ops` 행 의무화로 운영 가시성 없는 배포 차단, (b) #01 sprint 단위가 과대해 walking skeleton ship 시점 흐려짐 → 검색/인입 분리 |
| 2026-06-08 | §7 Team Ownership 추가 + `.github/CODEOWNERS` 생성 | MSA 전환 검토 결과 모놀리스 유지가 더 적합 — 팀 병렬 개발은 ownership 명문화로 충족. §7.1에 결정 배경 명시 |
| 2026-06-09 | §5.3 Temporal → SNS+SQS+Celery 단일 채택 / §5.1 트리 `infra/temporal` → `infra/messaging` / §4.6 #04 alert 라벨 갱신 | Phase 0 기술 스택 합리성 검토: Temporal과 SNS+SQS 병행은 인프라 표면적·운영 부담을 2배로. 사용자 결정으로 AWS native(SNS+SQS) 단일화. Karpenter가 SQS depth 기반으로 노드 확장하는 미래 EKS 토폴로지와도 정합 |
