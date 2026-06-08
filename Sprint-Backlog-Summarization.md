## 스프린트 백로그 — 02. 논문 요약 (Summarization)

> 길이(1줄/문단/페이지) × 관점(기여/방법/결과/비판) 프리셋 한국어 요약. 모든 문장에 `[§n.m]` anchor 의무.
> **여러 횡단 포트의 Owner 기능** — verifier(§4.3), anchor(§4.4), infra/llm cache(§4.1).
> 모듈 경계: `domain/summarization/` + `crosscutting/{anchor,verifier,glossary,audit}/` + `infra/llm/`.
> 출처: `feature-specs/02-summarization.md`, AGENTS.md §4.3/§4.4/§6.1.

---

### Sprint 1 — Summary MVP + Cache Owner

**Sprint 1 DoD:** 논문 1편 입력 → 한 문단 요약 출력. **infra/llm Sonnet 어댑터가 #03/#06/#07/#10에 export 가능 상태.**

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | **[Owner]** infra/llm: Claude Sonnet/Opus 어댑터 + `cache_control` 5분 TTL (extended-cache flag) — AGENTS.md §4.1 단독 cache key 책임 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 5 기능 의존, interface + cache key 결정 | Sonnet 호출 + cache hit 로깅 + 키 충돌 0건 + retry 3회 + import-linter 통과 |
| 2 | domain/summarization: 길이 프리셋(TL;DR/문단/페이지) + 관점 프리셋(기여/방법/결과/비판) 정의 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | YAML/enum + 토큰 cap 룰 | 12 (3×4) 프리셋 정의 + 토큰 cap 단위 테스트 |
| 3 | domain/summarization: Retriever — paper_id → 구조화 md 전문 + 관련 청크 fetch | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #01 결과 조회 + 청크 합성 | paper_id 조회 → md + 청크 반환 + p99 < 200ms |
| 4 | domain/summarization: Prompt Builder — §6 cached / 전문 cached(ephemeral) / fresh 요청 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 캐시 블록 4단 + structured prompt | 프리셋 × 청크 → 프롬프트 + 캐시 hit 검증 |

**Sprint 1 합계: 13 포인트**

---

### Sprint 2 — Anchor + Verifier Owner Ports + UI Integration

**Sprint 2 DoD:** §n.m anchor + 4-way verify + glossary 통합. sentence hover UI 동작. **crosscutting/anchor·crosscutting/verifier 포트가 #03/#05/#06/#07/#09/#10/#11에 export 가능 상태.**

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | **[Owner]** crosscutting/verifier: sentence × evidence → 4-way label (SUPPORTED/PARTIAL/UNSUPPORTED/NOT_FOUND) — AGENTS.md §4.3 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 7 기능 의존, 4-way 분류 + sampling 정책 | 4-way 라벨 정확도 90%+ + sampling 정책 설정 + 포트 export 문서 |
| 2 | **[Owner]** crosscutting/anchor: `§n.m` / `p.X ¶Y` 형식 파서 + 실제 span 존재 검증 (Anchor Validator) — AGENTS.md §4.4 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 기능 의존, 파서 + GROBID 인덱스 매칭 | 형식 파서 + 위조 anchor 거부 + 5 시드 시나리오 통과 |
| 3 | domain/summarization: 출력 structured JSON (sentences[], anchors[], verify_label[]) 스키마 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Pydantic + LLM tool-call | Pydantic 검증 통과 + LLM tool-call 1회 호출로 완성 |
| 4 | **[depends-on #03]** crosscutting/glossary: 세션 사전 lookup으로 요약 출력 한국어 용어 일관 표기 (AGENTS.md §6.2) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #03 포트 호출 + 매핑만 | #03 포트 호출 + 동일 용어 100% 일관 표기 검증 |
| 5 | frontend: 요약 sentence hover → 원문 span 하이라이트 + verify 라벨 배지 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | hover + span + 배지 + 상태 | sentence hover → span 하이라이트 < 100ms + 4 verify 라벨 색 |

**Sprint 2 합계: 19 포인트**

---

### Sprint 3 — Consistency + Hardening

**Sprint 3 DoD:** 100자 직역 금지 회귀 통과 + 캐시 히트율 70%+ 메트릭 + 재요약 일관성(동일 입력 cos > 0.95) 검증.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/summarization: 재요약 일관성 — temperature 0.2 / top_p 0.9 / seed 고정 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 설정 + 회귀 측정 | 동일 입력 재요약 cos > 0.95 측정 통과 |
| 2 | crosscutting/audit: 캐시 히트율 + verify 4-way 분포 + 비판적-검토 모드 신뢰성 메트릭 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Prometheus + Grafana 패턴 | 3 메트릭 Grafana 대시보드 + 임계 알림 |
| 3 | tests: 100자 이상 연속 직역 금지 + anchor 위조(존재하지 않는 §) 회귀 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 회귀 + 표절 경계 임계값 | 2 시드 시나리오 회귀 CI + 임계값 문서화 |
| 4 | **[Ops]** crosscutting/ops: SLO(요약 < 30s, verify p95 < 5s) + LLM 비용 대시보드(Sonnet/Opus 일간) + verify 4-way 분포 anomaly + 캐시 히트율 < 50% alert + runbook | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 비용 + 운영 + verify 신호 다축 | Grafana 4 패널 + Alertmanager 3 룰 + `/runbooks/llm-cost-spike.md` |

**Sprint 3 합계: 13 포인트**

**전체 합계: 45 포인트**
