## 스프린트 백로그 — 11. 읽을만한 논문 분류 추천 (Reading Priority Classifier)

> 후보 N편 × 사용자 프로필 → Must Read / Important / Optional / Skip 4단계 + rationale + exploration injection.
> **단위 비용 최저 + 재사용 빈도 최고 + 사용자 lock-in 강력** → AGENTS.md §3.1 빌드 순서 #3 위치(`01→02→11→09→…`).
> 모듈 경계: `domain/reading_priority/` + `crosscutting/{bandit,anchor,audit}/` + `infra/{llm,vectordb,citation_graph}/`.
> 출처: `feature-specs/11-reading-priority-classifier.md`.

---

### Sprint 1 — Static Classifier (학습 없는 기본 분류)

**Sprint 1 DoD:** 50 후보 + 사용자 프로필 → 4단계 분류 결과 표시. 첫 인상 만족도 측정 가능.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/reading_priority: 4단계 분류 정의 + 균형 cap (Must ≤ 20%, Skip ≤ 30%) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | enum + cap 룰, 의사결정 시간 | enum 정의 + cap 룰 4 단위 테스트 통과 |
| 2 | domain/reading_priority: Feature Extractor — 관련성(cos) + 영향력(citation/venue) + 신선도 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 feature + 정규화 | 3 feature 0-1 정규화 + 단위 테스트 |
| 3 | infra/citation_graph: venue tier 자체 매핑 (CORE/Scimago 기반) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 외부 venue 데이터 수집 | 100 학회 tier 매핑 + 누락 시 default tier |
| 4 | domain/reading_priority: Multi-axis Aggregator — sklearn linear / lightgbm 가중 합 + sigmoid | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 가중 합 + sigmoid | 모델 fit + 가중치 직렬화 + 점수 [0,1] 범위 |
| 5 | domain/reading_priority: Threshold Classifier — 분위수 캘리브레이션 (per-user, 분야별 균형) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 분위수 + 균형 cap | 분위수 캘리브레이션 + cap 강제 검증 |

**Sprint 1 합계: 14 포인트**

---

### Sprint 2 — Personalization (Bandit + Rationale + UI)

**Sprint 2 DoD:** Bandit 가중치 업데이트 동작 + 등급별 rationale 1-2문장 anchor 첨부 + Kanban UI drag-drop으로 분류 수정 가능.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | crosscutting/bandit: Thompson Sampling 가중치 학습 + decay (1년 stale 방지) | 8 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | RL 컴포넌트 — 사후 분포 + 보상 + 재현성 + 모니터링 | Beta 사후 분포 업데이트 + decay 룰 + reward 직렬화 + 재현성 시드 |
| 2 | domain/reading_priority: 고유성(MMR) + 사용자 적합도(이전 읽기/저장/번역 패턴) feature | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | MMR + 행동 로그 집계 | MMR feature 추출 + 행동 로그 24h 집계 |
| 3 | domain/reading_priority: Rationale Generator (Claude Haiku) — 등급당 1-2 문장 + 통일성 룰 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | LLM 배치 + 통일성 룰 | 50 후보 배치 호출 + 등급별 톤 일관 검증 |
| 4 | **[depends-on #02]** crosscutting/anchor: anchor 포트 호출 (rationale "Must인 이유: §3" 형식, §4.4) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 포트 호출 | #02 포트 호출 + rationale 100% anchor 검증 |
| 5 | frontend: 4-column Kanban UI + drag-and-drop 분류 수정 + rationale hover | 8 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | DnD + 4 컬럼 + hover | DnD 4 컬럼 + 수정 이벤트 → API + rationale hover < 100ms |

**Sprint 2 합계: 24 포인트**

---

### Sprint 3 — Exploration + Cold-Start + Hardening

**Sprint 3 DoD:** Skip 자기실현 방지 검증 (wildcard 노출률 5-10%) + 신규 사용자 첫 분류 후 캘리브레이션 UX + niche 분야 인용 편향 회귀 통과.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/reading_priority: Exploration Injector — Skip 자기실현 방지, wildcard Optional 승격 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | exploration 룰 + Bandit 통합 | wildcard 노출률 5-10% 측정 + Bandit 통합 |
| 2 | domain/reading_priority: Feedback Loop — 사용자 분류 수정 → Bandit 가중치 갱신 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 이벤트 + Bandit 업데이트 | 수정 이벤트 → Bandit 가중치 변화 검증 |
| 3 | domain/reading_priority: Cold-start 캘리브레이션 — 첫 결과 후 "이 분류가 맞나요?" UX | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | UX + 초기 가중치 학습 | 신규 사용자 첫 분류 후 캘리브레이션 단계 + 가중치 초기화 |
| 4 | crosscutting/audit: "Skip" 라벨 비공개 정책 (개인 추천만) + 공개 랭킹 보드 금지 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 정책 게시 + 권한 검증 | API 권한 거부 + ToS 게시 |
| 5 | tests: 첫 인상 만족도 + niche 분야 인용 편향 회귀 + exploration off 시 폐쇄 루프 측정 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 텔레메트리 + niche 시드 + 폐쇄 루프 | 3 메트릭 + niche 회귀 통과 + 폐쇄 루프 측정 통과 |
| 6 | **[Ops]** crosscutting/ops: SLO(분류 < 2s) + Bandit 가중치 stale 알림 (1년 미갱신) + Skip 자기실현 메트릭 + cold-start 만족도 추적 + runbook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Bandit 모니터 + 만족도 | Grafana 4 패널 + Alertmanager 3 룰 + `/runbooks/bandit-weight-stale.md` |

**Sprint 3 합계: 21 포인트**

**전체 합계: 59 포인트**
