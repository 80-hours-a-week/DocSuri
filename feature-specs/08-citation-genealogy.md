# 08. 인용 계보 트리 (Citation Genealogy Tree)

> 한 논문을 노드로 받아 그 논문이 *인용한* 논문(backward) + *그를 인용한* 논문(forward)을 재귀적으로 수집·분류 → 기술 계보를 시각적 트리/DAG로 출력.

---

## 1. 핵심 요소

- **양방향 탐색**:
  - **Backward** (조상): 해당 논문이 인용한 reference 목록.
  - **Forward** (자손): 해당 논문을 인용한 후속 논문.
- **Depth 제어**: 사용자가 깊이 1-5 지정. 기본 2 (조부모/손자까지).
- **노드 분류**: foundational(이정표) / methodological(방법 도입) / empirical(결과 검증) / survey(요약).
- **간선 의미**: 단순 "인용" 외에 "어떻게 인용됐는지" (이전 SOTA / 베이스라인 / 대조 / 영감) — 인용 문맥(citation sentence)에서 LLM이 분류.
- **시계열 정렬**: 노드를 출판년도 y축에 배치 → 시간 흐름이 시각적으로 보임.
- **영향력 점수**: 노드 크기는 분야 내 인용수 또는 PageRank.
- **사용자 강조**: 사용자가 읽은/저장한 논문을 다른 색으로 표시.

---

## 2. 주요 문제

- **재귀 폭발**: depth 3 = ~10^3 노드, depth 5 = ~10^5. UI에서 의미 있게 보여줄 수 없음. cap + 영향력 prune 필수.
- **인용 데이터 누락**: 비-OA 논문이나 오래된 논문은 reference 목록이 외부 API에 없음. PDF 직접 파싱으로 보충 필요.
- **인용 의도 분류 정확도**: "Smith 2020 also used X"가 "베이스라인 비교"인지 "방법 채택"인지 LLM 판단이 흔들림.
- **노이즈 인용**: 형식적 인용("introduction에서 분야 소개차") vs 실질적 인용("우리 방법은 X에 기반"). 형식적 인용을 빼면 트리가 깔끔해지지만 누락 위험.
- **API rate limit**: depth 3 = 1000+ API 호출 / 사용자. 캐시 강제.
- **시각화 UX**: 노드 1000개를 한 화면에 그리면 무의미. zoom + filter + 클러스터링 필수.

---

## 3. 파이프라인 설계 & 기술 스택

```
seed paper_id + depth + direction
    │
    ▼
┌─────────────────────────┐
│ Reference Resolver      │
│ - OpenAlex/S2 API       │  (1차)
│ - GROBID로 PDF 파싱     │  (2차, fallback)
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Graph Crawler           │  BFS (depth-limited)
│ + dedupe + cache         │  Redis 1주 TTL
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Citation Context Fetch  │  각 인용 위치의 sentence 추출
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Intent Classifier (LLM) │  citation sentence → 4 카테고리
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Influence Scorer        │  PageRank / citation count
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Node Categorizer        │  foundational/methodological/...
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Layout Engine           │  시계열 y축 + 영향력 노드 크기
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Interactive Viz         │  D3.js / Cytoscape.js / react-flow
└─────────────────────────┘
```

### 기술 스택

| 레이어 | 선택 | 비고 |
|---|---|---|
| 인용 데이터 | OpenAlex (1차) + Semantic Scholar | OpenAlex가 무료·완성도 좋음 |
| Graph store | Neo4j (옵션) / Postgres recursive CTE | 작은 그래프엔 Postgres 충분 |
| 인용 컨텍스트 추출 | GROBID `<ref>` 위치 + 주변 문장 | |
| Intent classifier | Claude Haiku (대량 분류) | |
| 시각화 (브라우저) | react-flow + dagre layout | 학술 DAG에 적합 |
| 대용량 옵션 | Cytoscape.js + level-of-detail | 노드 1000+ 시 |

---

## 4. 차별화 포인트

- **양방향 + 의도 분류**: Connected Papers는 forward citation 위주이고 의도 분류 없음. ResearchRabbit도 의도 분류 없음. 본 기능은 "어떻게 인용됐는지"를 노드 간선의 라벨로 보여줌 → 계보의 *의미*가 보임.
- **PDF 직접 파싱 fallback**: OpenAlex/S2에 reference 데이터 없는 옛 논문도 GROBID 파싱으로 채움. 클래식 논문 계보 추적이 가능해짐.
- **시계열 layout**: y축에 출판년도를 강제 → 한 줄기의 진화가 시각적으로 명확.
- **사용자 히트맵**: 자기가 이미 읽은 논문이 트리 어디에 있는지 표시 → 다음에 어디를 읽을지 직관적.

---

## 5. 위험 요소

- **OpenAlex 데이터 신뢰도**: 무료지만 최신 논문/niche 분야에서 인용 누락 종종. 사용자에게 "본 결과에 미포함된 인용이 있을 수 있음" 명시 필요.
- **재귀 비용 폭발**: depth 4+ 사용자가 쉽게 클릭. UI에서 명시적 비용 경고("이 작업은 약 N개 노드를 조회합니다").
- **인용 의도 분류 환각**: 형식적 인용을 "방법 채택"으로 잘못 분류 시 계보 왜곡. 신뢰도 점수 표시 필수.
- **시각화 성능**: 브라우저에서 노드 5000+ 인터랙티브 렌더링은 무거움. WebGL 기반(deck.gl) 옵션 검토.
- **컨텍스트 자기참조**: 학회 시리즈에서 같은 그룹의 자기 인용이 트리를 왜곡. dedupe by author + 자기 인용 별색 강조.

---

## 6. 예상 비용

### 단위 비용 (depth=2, ~150 노드)

| 단계 | 비용 |
|---|---|
| OpenAlex 호출 (150건, 무료) | $0 |
| GROBID fallback (10건) | 컴퓨트 ~$0.05 |
| Citation context 추출 | $0 (이미 파싱된 데이터) |
| Intent classifier (Haiku, 200 edges) | ~$0.2 |
| Influence scoring | $0 |
| **합계/트리** | **~$0.25** |

### 단위 비용 (depth=4, ~5000 노드)

- Intent classifier: ~$10 (대량)
- GROBID fallback: ~$2
- 인프라 부담 큼

### MVP (월 2,000 트리, 평균 depth=2)

- $0.25 × 2,000 = **$500/월**
- 캐시 60% 가정 → **~$200/월**
- 인프라(Neo4j 옵션 시): +$80/월

### 스케일업 (월 5만 트리)

- $0.25 × 50,000 = **$12,500/월**
- 캐시 70% → **~$3,750/월**

> 가장 큰 비용 변동은 **depth 선택**. 기본 depth=2 강제 + depth≥3은 "예상 비용 표시" 옵트인 권장. 이로써 평균 비용이 안정적.
