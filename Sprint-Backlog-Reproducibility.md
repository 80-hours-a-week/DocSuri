## 스프린트 백로그 — 09. 재현 가능성 자동 평가 (Reproducibility Evaluation)

> rubric(NeurIPS+Pineau+PRISMA) 기반 0-100점 + 분야별 rubric 분기 + URL 자동 검증 + anchor 첨부.
> **Temporal 워크플로우** (AGENTS.md §5.3 W7 이후) — 다단 추출/검증/스코어링, URL HEAD/GitHub API 외부 호출 retry.
> 모듈 경계: `domain/reproducibility/` + `workflows/repro_evaluation/` + `crosscutting/{verifier,audit}/` + `infra/{llm,http,github}/`.
> 출처: `feature-specs/09-reproducibility-evaluation.md`.

---

### Sprint 1 — Rubric-based Static Evaluation

**Sprint 1 DoD:** 논문 1편 입력 → rubric YAML 로드 + 분야 분류 + checklist 항목별 evidence 추출 + per-item 0/1/2 점수 산출.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/reproducibility: 분야별 rubric YAML 정의 (ML/PRISMA/CONSORT/COBE) + 편집 가능 형식 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 분야 rubric 학술 지식 의존 | 4 분야 rubric YAML 작성 + 학술 출처 1차 인용 |
| 2 | workflows/repro_evaluation: Temporal 워크플로우 — extract → verify URLs → score → report **(depends-on #04 infra/temporal)** | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4단 activity + retry | 워크플로우 정의 + 4 activity + retry 정책 적용 |
| 3 | domain/reproducibility: 분야 분류기 (Claude Haiku 단일 호출) — rubric 선택 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 단일 LLM + 4-class | 4-class 분류 정확도 85%+ 시드 데이터 |
| 4 | domain/reproducibility: Checklist Extractor (Claude Sonnet, structured output) — 항목별 evidence | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | structured output + 항목별 | 8 rubric 항목 × evidence 추출 + Pydantic 검증 통과 |
| 5 | domain/reproducibility: Per-item Scorer — rubric 정의대로 0/1/2 점수 (룰 우선) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 룰 엔진 + LLM 보조 | 0/1/2 점수 산출 + 룰 우선 분기 + LLM fallback 검증 |

**Sprint 1 합계: 18 포인트**

---

### Sprint 2 — External Verification + Aggregation

**Sprint 2 DoD:** URL/GitHub/HuggingFace 외부 검증 + GROBID 표 감사 + 카테고리·총점 집계 + 자연어 권장 리포트 생성.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | infra/http: URL Verifier — httpx HEAD + 타임아웃/재시도 + 24h 후 재검증 옵션 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | httpx + retry + 스케줄 | HEAD 응답 코드 + 24h 재검증 잡 등록 검증 |
| 2 | infra/github: GitHub API 어댑터 — repo 존재/README/스타/최근 커밋 확인 (clone 금지) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | GitHub REST + auth | repo 메타데이터 4 필드 추출 + auth 검증 |
| 3 | infra/http: HuggingFace API 어댑터 — 데이터셋/모델 weight 접근성 확인 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | HF API + endpoint 확인 | 데이터셋/모델 존재 확인 + 단위 테스트 |
| 4 | domain/reproducibility: Table Auditor — GROBID 표 JSON + 하이퍼파라미터 정규식 매칭 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | GROBID 표 파싱 + 다양한 패턴 | 하이퍼파라미터 표 인식률 80%+ 시드 데이터 |
| 5 | domain/reproducibility: Aggregator — 카테고리/총점 가중 평균 + sub-score | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 가중 평균 + 분해 | 카테고리/총점 산출 + sub-score 분해 단위 테스트 |
| 6 | domain/reproducibility: Report Composer (Sonnet) — 미흡 항목 자연어 설명 + 권장 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | LLM + 권장 톤 | 미흡 항목 × 권장 출력 + structured JSON |

**Sprint 2 합계: 18 포인트**

---

### Sprint 3 — Verifier (100% sampling) + Author Mode + Hardening

**Sprint 3 DoD:** 100% verifier sub-score별 의무 통과 + appendix 컨텍스트 누락 0건 + 저자용 prereview 모드 동작 + rubric 게이밍 회귀 통과.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | **[depends-on #02]** crosscutting/verifier: verifier 포트 호출 (100% sampling 의무, sub-score별, §4.3) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 호출 + 100% sampling + 비용 모니터링 | sub-score별 100% verify + 비용 메트릭 노출 |
| 2 | domain/reproducibility: 부록(appendix) 컨텍스트 누락 방지 — full-paper 컨텍스트 보장 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | GROBID appendix + 합성 | appendix 식별 + full-paper 컨텍스트 통합 검증 |
| 3 | domain/reproducibility: 저자용 prereview 모드 — 출판 전 자가 점검 UX | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | UX + 자가 점검 가이드 | 자가 점검 단계 + 미흡 항목 액션 권장 UI |
| 4 | frontend: 점수표 + 카테고리별 sub-score + anchor + 미흡 항목 권장 카드 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 점수표 + 분해 + 권장 + hover | 점수표 + sub-score 차트 + anchor hover + 권장 카드 |
| 5 | crosscutting/audit: 점수 공개 금지 정책 (개인 결과만) + 명예훼손 우려 ToS 게시 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 정책 + 권한 검증 | API 권한 거부 + ToS 게시 검증 |
| 6 | tests: rubric 게이밍 회귀 + GitHub 일시 비공개 false negative + 분야 오분류 영향 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 시드 + 회귀 측정 | 3 시드 시나리오 CI + 점수 안정성 측정 |
| 7 | **[Ops]** crosscutting/ops: SLO(평가 < 5min) + GitHub API rate alert + URL 검증 실패율 + verify 100% sampling 비용 모니터링 + runbook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 외부 API 다축 모니터링 | Grafana 4 패널 + Alertmanager 3 룰 + `/runbooks/github-api-throttle.md` |

**Sprint 3 합계: 26 포인트**

**전체 합계: 62 포인트**
