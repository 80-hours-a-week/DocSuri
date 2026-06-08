## 스프린트 백로그 — 07. 프로젝트 트렌드 & 통합 분석 (Project Trend & Integration Analysis)

> 사용자 프로젝트(Git/문서) 등록 → 트렌드 추종도 + 통합 후보 + 권장 수정점 + 방어 가능성 + 코드/논문 양방향 anchor.
> **Temporal 워크플로우** (AGENTS.md §5.3) — 코드 임베딩 + corpus 수집 + 다단 LLM, 재분석 빈도 높음(3개월 주기).
> 모듈 경계: `domain/analysis/` (06과 공유) + `workflows/project_analysis/` + `crosscutting/{verifier,audit,ops}/` + `infra/{llm,code_embed,vectordb}/`.
> 출처: `feature-specs/07-project-trend-and-integration.md`.

**Sprint 3 split 사유**: 원래 frontend(8p) 단일 행이 코드 diff 뷰어 / 권장+anchor / Mermaid 시계열 세 컴포넌트를 묶고 있었음. 3 행으로 분할해 FE 병렬화 + DoD 명확화. 행 합계는 동일(8p).

---

### Sprint 1 — Project Ingestor + Profiler

**Sprint 1 DoD:** Git URL 등록 → 코드 임베딩 + AST 파싱 + 별도 Qdrant collection 저장 + LLM 프로파일(도메인/기법/의도) 출력.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | infra/code_embed: voyage-code-3 또는 CodeT5+ 어댑터 + tree-sitter AST 파서 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 임베딩 결정 + 다언어 AST | 2 모델 벤치 + 결정 문서 + 5 언어 AST 파싱 |
| 2 | domain/analysis: Project Ingestor — Git URL clone + 로컬 디렉터리 + README/설계문서 파싱 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Git + 다양한 docs | Git clone + README/docs 5 형식 파싱 + 메타 추출 |
| 3 | workflows/project_analysis: Temporal 워크플로우 — ingest → profile → trend → recommend **(depends-on #04 infra/temporal)** | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4단 + retry | 4 activity + retry 정책 + 30분 timeout |
| 4 | infra/vectordb: 코드용 별도 Qdrant collection — 논문과 분리 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | collection + payload | collection 생성 + payload 스키마 + 검색 통합 테스트 |
| 5 | domain/analysis: Project Profiler (Claude Sonnet) — 도메인 분류 + 사용 기법 + 핵심 의도 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | LLM + 프로파일 + 구조화 | 3 필드 추출 + Pydantic 검증 통과 |

**Sprint 1 합계: 18 포인트**

---

### Sprint 2 — Trend Comparison + Integration Recommendation + Verifier

**Sprint 2 DoD:** 시기 정합 corpus 비교 + 통합 후보 + 코드/논문 양방향 anchor 권장 + 방어 가능성 평가 + verifier 통합. 사용자 의도(연구/응용) 따라 톤 분기.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/analysis: Trend Corpus Selector — 시기 정합성 보장 (프로젝트 timestamp ± window) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 시기 매칭 + window | 프로젝트 timestamp ± 24 month window + corpus 200편 선택 |
| 2 | domain/analysis: Trend Analyzer — 기법 분포 / 메트릭 표준화 / SOTA baseline 룰+통계 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 축 분석 + 통계 | 기법 분포 비교 + 메트릭 표준 확인 + SOTA baseline 추출 |
| 3 | domain/analysis: Integration Finder (Claude Opus) — 프로젝트 모듈 × 후보 적합도/난이도 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 매칭 + 적합도/난이도 | 모듈 × 후보 매트릭스 + 적합도/난이도 점수 [0,1] |
| 4 | domain/analysis: Recommendation Composer (Opus) — 파일/줄/라이브러리/논문 anchor 4중 첨부 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4중 anchor (어려운 요구) | 권장 1건당 4 anchor 모두 포함 + structured 출력 |
| 5 | domain/analysis: Defensibility Checker (Sonnet) — 사용자 의도(연구/응용)별 톤 분기 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 차별점 + 톤 분기 | 차별점 평가 + 연구/응용 톤 분기 단위 테스트 |
| 6 | **[depends-on #02]** crosscutting/verifier: verifier 포트 호출 + effort 추정/위험도 라벨링 (§4.3) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 호출 + 라벨링 | #02 호출 + effort/위험도 라벨 부착 |

**Sprint 2 합계: 24 포인트**

---

### Sprint 3 — Re-analysis Diff + Incremental + Frontend Split + Ops

**Sprint 3 DoD:** 3개월 전 vs 현재 권장 변화 시각화 + 변경 파일만 재임베딩으로 50% 비용 절감 + 3 frontend 컴포넌트 병렬 완성 + ZDR 적용 + SLO 출시.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/analysis: Incremental 재분석 — 변경된 파일만 임베딩 갱신, 50% 비용 절감 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 변경 추적 + 최적화 | 변경 파일만 재임베딩 + 비용 50% 절감 측정 |
| 2 | domain/analysis: 이전 분석 diff — 3개월 전 vs 현재 권장 변화 시각화 (백엔드 diff 알고리즘) | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | diff + 저장/조회 | 권장 diff 알고리즘 + 변화 라벨링(추가/제거/유지) |
| 3 | frontend: 코드 diff 뷰어 — Monaco editor + 권장 변경점 highlight | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 단일 컴포넌트 (분할 행 1/3) | Monaco + 변경점 highlight + 줄 단위 권장 hover |
| 4 | frontend: 권장 카드 + 논문/코드 anchor hover (양방향 8 anchor) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 단일 컴포넌트 (분할 행 2/3) | 권장 카드 + 8 anchor 양방향 hover + 카드 정렬 |
| 5 | frontend: Mermaid 트렌드 시계열 차트 — 기법/메트릭/SOTA 시기 추이 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 단일 컴포넌트 (분할 행 3/3) | Mermaid 시계열 3 차트 + 사용자 의도 필터 |
| 6 | crosscutting/audit: IP 보호 — Anthropic ZDR 옵션 + 사용자 동의 + 코드 로컬 처리 옵션 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 정책 + 옵트인 + 로컬 분기 | ZDR 활성화 + 동의 UI + 로컬 처리 분기 검증 |
| 7 | tests: 시기 정합성 회귀 + niche 도메인 코드 임베딩 품질 + 응용 vs 연구 톤 분기 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 시드 + 회귀 측정 | 3 시드 시나리오 회귀 CI + 톤 분기 단위 테스트 |
| 8 | **[Ops]** crosscutting/ops: SLO(분석 < 30min) + Opus 비용 + ZDR off 감지 alert (IP 누출 방지) + Temporal 재시도 + 비용 50% 절감 baseline + runbook | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 비용 + 보안 + 운영 다축 | Grafana 5 패널 + Alertmanager 4 룰 + `/runbooks/zdr-off-detected.md` |

**Sprint 3 합계: 31 포인트** ⚠️ — Sprint 3가 무거움. 2팀 병렬화 필수 (백엔드: 1, 6, 7; 프론트엔드: 3, 4, 5; SRE: 8). 단일 팀이면 Sprint 4로 1, 2 미루는 옵션 검토.

**전체 합계: 73 포인트**
