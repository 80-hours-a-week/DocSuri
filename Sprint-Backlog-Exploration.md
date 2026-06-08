## 스프린트 백로그 — 05. 유사 논문 탐색 (Similar Paper Exploration)

> seed(자유서술/논문/프로필/초고) → ANN + MMR + 다축 정렬 → "왜 유사한지" anchor 첨부 설명 + 반례(dissimilar) 모드.
> 모듈 경계: `domain/exploration/` + `crosscutting/{anchor,verifier,audit}/` + `infra/{llm,vectordb,citation_graph}/`.
> 출처: `feature-specs/05-similar-paper-exploration.md`.

---

### Sprint 1 — ANN Search + Diversification

**Sprint 1 DoD:** seed 입력(4 유형 모두) → top-K=100 → MMR 다양화 → 카드 그리드 표시.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | infra/vectordb: SPECTER2 vs text-embedding-3-large 학술 도메인 임베딩 벤치 + 결정 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 임베딩 결정 후속 영향 | 벤치 데이터 + 결정 문서 + 결정된 모델 통합 |
| 2 | domain/exploration: Seed Embedder — 자유서술/paper_id/프로필/초고 4가지 입력 유형 처리 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 유형 dispatch + 임베딩 | 4 입력 유형 unit 테스트 + 임베딩 정규화 |
| 3 | domain/exploration: ANN Search (Qdrant top-K=100) + 메타데이터 필터(연도/분야/인용수) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Qdrant + 필터 | top-K 검색 + 3 필터 조합 + p99 < 200ms |
| 4 | domain/exploration: MMR Diversifier — λ=0.7, 저자/그룹 dedupe 강제 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | MMR + dedupe | MMR λ=0.7 + 동일 저자 ≤ 2건 cap |
| 5 | frontend: 카드 그리드 + 유사/차이 토글 + react-flow 관계 시각화 옵션 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 카드 + 토글 | 카드 그리드 + 유사/차이 토글 + 빈/에러 처리 |

**Sprint 1 합계: 17 포인트**

---

### Sprint 2 — Multi-axis Re-score + Explainer + Anchor/Verifier

**Sprint 2 DoD:** 의미+기여+시기+인용거리 다축 점수 + Sonnet Explainer "왜 유사한가" + anchor 부여 + verifier 환각 검증. #08 OpenAlex BFS 포트 호출 동작.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/exploration: 기여 유사도 별도 임베딩 — contribution sentence extractor + 임베딩 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | sentence 추출 + 별도 임베딩 | contribution sentence 추출 정확도 80%+ + 별도 임베딩 인덱스 |
| 2 | **[depends-on #08]** infra/citation_graph: OpenAlex BFS 포트 호출 (hop distance 계산) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #08 포트 호출 | #08 포트 호출 + hop distance 정규화 [0,1] |
| 3 | domain/exploration: 다축 Re-scorer — 의미 + 기여 + 시기 + 인용거리 가중 합 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4축 가중 + 정규화 | 4축 점수 정규화 + 가중치 직렬화 |
| 4 | domain/exploration: Explainer (Claude Sonnet) — seed × candidate 비교, "왜 유사한가" 2-3문장 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | LLM + 비교 + 2-3문장 | 비교 프롬프트 + 2-3문장 강제 + structured 출력 |
| 5 | **[depends-on #02]** crosscutting/anchor: 설명 문장 anchor 포트 호출 (`§n.m` 형식, §4.4) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 포트 호출 | #02 포트 호출 + 100% anchor 검증 |
| 6 | **[depends-on #02]** crosscutting/verifier: verifier 포트 호출 ("유사 이유" ↔ 양쪽 evidence, §4.3) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 포트 + 양쪽 evidence | #02 호출 + 양쪽 evidence 합성 + verify 라벨 |

**Sprint 2 합계: 17 포인트**

---

### Sprint 3 — Dissimilar Mode + Cost Optimization + Hardening

**Sprint 3 DoD:** Dissimilar Pair 동작 + lazy 설명 모드로 비용 80% 절감 검증 + 저자/그룹 편향 회귀 통과 + cross-domain 어휘 매핑 처리.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/exploration: Dissimilar Pair Finder — 근접하지만 결정적 차이 있는 논문 탐지 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 근접 + 차이 + 임계값 | 임베딩 cos 임계 + 차이 측정 + top-5 반례 출력 |
| 2 | frontend: lazy 설명 모드 — "보고 싶은 카드 클릭 시 Explainer 호출"로 비용 80% 절감 옵션 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | lazy UX + 비용 메트릭 | lazy 로딩 + 비용 80% 절감 측정 |
| 3 | tests: 저자/그룹 편향 회귀 + cross-domain 어휘 매핑 + cold-start 자유서술 시나리오 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 시드 + 편향 측정 | 3 시드 시나리오 회귀 CI + 편향 메트릭 |
| 4 | **[Ops]** crosscutting/ops: SLO(탐색 < 3s, Explainer < 10s) + Qdrant 인덱스 헬스 + Explainer 비용 대시보드 + runbook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 운영 가시성 + 비용 | Grafana 3 패널 + Alertmanager 2 룰 + `/runbooks/explainer-cost-spike.md` |

**Sprint 3 합계: 16 포인트**

**전체 합계: 50 포인트**
