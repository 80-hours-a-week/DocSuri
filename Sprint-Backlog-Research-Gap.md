## 스프린트 백로그 — 06. 연구 공백 분석 & 아이디어 제안 (Research Gap & Idea Generation)

> scope 정의 → corpus 1000편 수집 → 토픽 모델링 → 다축 공백 신호 → Gap Synthesizer → Idea Generator → Feasibility.
> **Temporal 워크플로우** (AGENTS.md §5.3) — 30분 단위 장시간 잡, retry/timeout 강력 필요.
> 모듈 경계: `domain/analysis/` + `workflows/gap_analysis/` + `crosscutting/{verifier,audit,ops}/` + `infra/{llm,vectordb}/`.
> 출처: `feature-specs/06-research-gap-and-ideas.md`.

**Sprint 2 rebalance 사유**: 원래 Sprint 2가 26 pt로 과중. Claim conflict(5p, fine-tune 옵션 포함하는 ML 컴포넌트)를 Sprint 3으로 이동. Sprint 2는 Gap+Idea 핵심 흐름에 집중, Sprint 3에서 신호 품질 보강. 트레이드오프: Sprint 2 ship 시점에 공백 신호는 4종 중 3종(method/benchmark/temporal)만 활용 — claim conflict는 후속 sprint 신호 enrichment.

---

### Sprint 1 — Scope + Corpus + Signal Extraction (3종)

**Sprint 1 DoD:** 사용자 scope 정의 → corpus 1000편 수집 → BERTopic 클러스터 출력 → method/benchmark/temporal 3종 signal 추출. claim conflict는 Sprint 3.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | workflows/gap_analysis: Temporal 워크플로우 — corpus 수집 → 토픽 → signal → synth retry/timeout **(depends-on #04 infra/temporal)** | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4단 + retry/timeout | 4 activity + retry 정책 + 30분 timeout |
| 2 | domain/analysis: Scope 정의 입력 (키워드/시기/출판처/제외 키워드) + scope 캐시 키 설계 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 입력 폼 + 캐시 키 | scope 입력 + 동일 scope 캐시 적중 검증 |
| 3 | domain/analysis: Corpus Collector — #01a 검색 + #01b 인입 bulk 모드 호출 (N=1000편) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #01a/#01b 호출 + 페이지네이션 | 1000편 수집 < 30분 + 페이지네이션 안정성 |
| 4 | domain/analysis: BERTopic (UMAP + HDBSCAN) 토픽 모델러 + LLM 라벨링 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 토픽 모델 + LLM 라벨 + 후처리 | 토픽 10-30개 클러스터 + LLM 라벨 + 잡음 클러스터 분리 |
| 5 | domain/analysis: Signal Extractors (3종) — method gap / benchmark gap / temporal gap | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 신호 + 다른 휴리스틱 | 3 signal 추출기 + 시드 코퍼스 단위 테스트 |

**Sprint 1 합계: 19 포인트**

---

### Sprint 2 — Gap Synthesis + Idea Generation + Verifier

**Sprint 2 DoD:** Gap Synthesizer가 anchor 첨부 공백 진술 생성 + Idea Generator n=10 dedupe 후보 + Feasibility 추정 + verifier negative claim 재검색 + 공백 맵 UI.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/analysis: Gap Synthesizer (Claude Opus) — signals → 자연어 공백 진술 + anchor | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Opus + 진술 + anchor 의무 | 공백 진술 100% anchor + structured 출력 |
| 2 | domain/analysis: Idea Generator (Opus, n=10 sampling) — gap × 사용자 제약 → 아이디어 후보 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | sampling + dedupe + ranking | n=10 → dedupe → top-5 ranked 아이디어 |
| 3 | domain/analysis: Feasibility Scorer — 자원/시기/난이도 추정 룰 + LLM 보조 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 룰 + LLM 보조 | 자원/시기/난이도 3축 추정 + 라벨링 |
| 4 | **[depends-on #02]** crosscutting/verifier: verifier 포트 호출 + Sonnet 승격 (negative claim 적극 재검색, §4.3) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 + 승격 + 재검색 | #02 호출 + Sonnet 승격 분기 + negative claim 재검색 |
| 5 | frontend: 공백 맵 시각화 (UMAP 2D projection) + 아이디어 카드 + feasibility 배지 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | UMAP + 카드 + 배지 | UMAP 2D + 카드 클릭 → 상세 + feasibility 배지 |

**Sprint 2 합계: 21 포인트**

---

### Sprint 3 — Claim Conflict Signal + Sensitivity + Compliance + Ops

**Sprint 3 DoD:** claim conflict 신호 추가로 공백 신호 4종 완성 + scope sensitivity 시각화 + incremental 분석으로 캐시 적중률 30%+ + ToS + niche 환각 회귀 + SLO 출시.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/analysis: Claim conflict — embedding stance detection (자체 분류기 fine-tune 옵션) — Sprint 2에서 이전 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | stance + fine-tune 결정 | stance 정확도 75%+ + fine-tune 옵션 결정 문서 |
| 2 | domain/analysis: Scope sensitivity 노출 — 정의 변형 시 공백 차이 시각화 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 정의 변형 + 차이 시각화 | scope 변형 3종 자동 생성 + 차이 diff UI |
| 3 | domain/analysis: Incremental 분석 — 이전 corpus + 신규 N편만 추가 처리 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 이전 재사용 + 추가만 | 같은 scope 캐시 적중률 30%+ 측정 |
| 4 | crosscutting/audit: 사용자 입력 격리 — 세션·테넌트 격리 + LLM 메모리 사용 금지 ToS 게시 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 격리 + LLM memory off + ToS | tenant 격리 + LLM memory off 검증 + ToS 게시 |
| 5 | tests: scope sensitivity 회귀 + niche 분야 환각 + 같은 분야 캐시 적중률 + claim conflict 회귀 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 시드 + 회귀 + 캐시 메트릭 | 4 시드 시나리오 CI + 캐시 적중률 측정 |
| 6 | **[Ops]** crosscutting/ops: SLO(분석 < 1h, 재시도 < 3회) + Opus $12/분석 임계 alert + scope 캐시 적중률 + Temporal 워크플로우 실패 알림 + runbook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 비용 임계 + 운영 가시성 | Grafana 4 패널 + Alertmanager 3 룰 + `/runbooks/llm-cost-spike.md` |

**Sprint 3 합계: 24 포인트**

**전체 합계: 64 포인트**
