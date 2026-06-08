## 스프린트 백로그 — 08. 인용 계보 트리 (Citation Genealogy Tree)

> seed 논문 → backward/forward 양방향 재귀 수집 → 노드 분류(foundational/methodological/empirical/survey) + 인용 의도 분류 → 시계열 layout.
> **infra/citation_graph Owner 기능** (OpenAlex BFS 어댑터) — #05/#11이 공통 의존.
> 모듈 경계: `domain/citation/` + `crosscutting/{cache,audit}/` + `infra/{llm,citation_graph,graphdb}/`.
> 출처: `feature-specs/08-citation-genealogy.md`.

---

### Sprint 1 — Reference Resolver Owner + Basic Tree (depth=2)

**Sprint 1 DoD:** seed 논문 → depth=2 backward/forward 트리 표시. **infra/citation_graph (OpenAlex/S2 어댑터)가 #05/#11에 export 가능 상태.**

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | **[Owner: infra/citation_graph]** domain/citation + infra/citation_graph: Reference Resolver — OpenAlex/S2 (1차) + GROBID PDF fallback (2차) — #05/#11이 공통 의존 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Owner — 2 API + GROBID fallback | OpenAlex/S2 통합 + PDF fallback 시나리오 + 포트 export 문서 |
| 2 | infra/graphdb: Postgres recursive CTE (소형) vs Neo4j (대형) — 임계 결정 + 어댑터 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 옵션 검증 + 임계 결정 | 양쪽 어댑터 통합 테스트 + 노드 수 임계값 결정 문서 |
| 3 | domain/citation: Graph Crawler — BFS depth-limited + dedupe | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | BFS + dedupe | depth=2 BFS + dedupe + depth cap 강제 |
| 4 | crosscutting/cache: Redis 1주 TTL 인용 그래프 캐시 + depth≥3 비용 경고 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 캐시 + 경고 UX | 1주 TTL + depth≥3 비용 경고 UI 표시 |
| 5 | frontend: react-flow + dagre (depth=2 기본 layout) | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 그래프 통합 + 기본 layout | depth=2 트리 렌더링 + zoom/pan + 노드 클릭 |

**Sprint 1 합계: 20 포인트**

---

### Sprint 2 — Intent Classification + Influence Scoring

**Sprint 2 DoD:** 4 카테고리 인용 의도 분류 + confidence 노출 + PageRank/citation 영향력 점수 + foundational/methodological/empirical/survey 노드 분류.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/citation: Citation Context Fetch — GROBID `<ref>` 위치 주변 sentence 추출 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | GROBID 파싱 + 주변 sentence | citation 위치 → 주변 sentence ±1 정확도 90%+ |
| 2 | domain/citation: Intent Classifier (Claude Haiku) — citation sentence → 4 카테고리 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | LLM 배치 호출 | 4-class 분류 정확도 80%+ 시드 데이터 |
| 3 | domain/citation: 신뢰도 점수 — Intent 분류 confidence 노출 (환각 경고) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | confidence + 경고 UI | confidence 노출 + 임계값 미만 경고 표시 |
| 4 | domain/citation: Influence Scorer — PageRank / citation count + venue tier | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | PageRank + venue | PageRank 계산 + venue tier 통합 점수 |
| 5 | domain/citation: Node Categorizer — foundational/methodological/empirical/survey 분류 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 분류 룰 + LLM 보조 | 4-category 분류 룰 + LLM fallback |

**Sprint 2 합계: 13 포인트**

---

### Sprint 3 — Temporal Layout + LOD + Hardening

**Sprint 3 DoD:** 시계열 y축 layout + Cytoscape LOD로 5000+ 노드 인터랙티브 + depth 폭발 cap + 자기 인용 dedupe + 형식적 인용 분류 회귀 통과.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/citation: Layout Engine — 시계열 y축 + 영향력 노드 크기 + dagre | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | dagre + 시계열 정렬 | 출판년도 y축 정렬 + 영향력 노드 크기 비례 |
| 2 | frontend: Cytoscape.js + LOD (depth≥3, 5000+ 노드) + 사용자 강조 히트맵 + zoom/filter | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 다른 라이브러리 + LOD + 인터랙션 | 5000 노드 인터랙티브 60fps + 사용자 강조 히트맵 |
| 3 | domain/citation: 자기 인용 dedupe + 별색 강조 (그룹 자기참조 왜곡 방지) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 저자 매칭 + 별색 | 동일 저자 인용 별색 + dedupe 옵션 |
| 4 | crosscutting/audit: OpenAlex 누락 경고 명시 + depth 비용 경고 옵트인 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 경고 + 옵트인 | 누락 경고 UI + 옵트인 단계 |
| 5 | tests: depth 폭발 cap + 자기 인용 dedupe + 형식적 vs 실질적 인용 분류 회귀 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 시나리오 + 회귀 | 3 시드 시나리오 회귀 CI |
| 6 | **[Ops]** crosscutting/ops: SLO(depth=2 < 10s) + OpenAlex API 가용성 + GROBID fallback rate + Cytoscape 렌더링 fps + runbook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 운영 가시성 + 렌더링 성능 | Grafana 4 패널 + Alertmanager 2 룰 + `/runbooks/openalex-outage.md` |

**Sprint 3 합계: 23 포인트**

**전체 합계: 56 포인트**
