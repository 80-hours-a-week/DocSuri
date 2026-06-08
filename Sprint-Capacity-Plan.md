# Sprint Capacity Plan

> 12개 backlog 파일의 sprint capacity와 5주 프로토타입 / MVP / Full launch 시나리오 매핑.
> 총 **650 pt** (#01 split + Ops 행 추가 반영).
> 출처: 11개 Sprint-Backlog-*.md + AGENTS.md §3.1 빌드 순서 + §4.6 Ops 규약.

---

## 1. Total scope: 650 포인트

| # | 기능 | Sprint 1 | Sprint 2 | Sprint 3 | 합계 | Owner 포트 |
|---|---|---:|---:|---:|---:|---|
| 01a | Search | 21 | 16 | 11 | **48** | infra/embedding (Sprint 2) |
| 01b | Ingest | 13 | 13 | 14 | **40** | — |
| 02 | Summarization | 13 | 19 | 13 | **45** | infra/llm cache (S1), verifier+anchor (S2) |
| 03 | Translation | 10 | 18 | 13 | **41** | glossary (S1 schema, S2 글로싱) |
| 04 | Monitoring | 21 | 21 | 21 | **63** | infra/temporal (S1) |
| 05 | Exploration | 17 | 17 | 16 | **50** | — |
| 06 | Research-Gap | 19 | 21 | 24 | **64** | — |
| 07 | Project-Trend | 18 | 24 | 31 ⚠️ | **73** | — |
| 08 | Citation Genealogy | 20 | 13 | 23 | **56** | infra/citation_graph (S1) |
| 09 | Reproducibility | 18 | 18 | 26 ⚠️ | **62** | — |
| 10 | Reading-Assistant | 13 | 19 | 17 | **49** | — |
| 11 | Priority Classifier | 14 | 24 ⚠️ | 21 | **59** | — |
| | **합계** | **197** | **223** | **230** | **650** | |

**Sprint 분포 관찰**:
- Sprint 1 (197 pt) — 신규 구현 + Owner 포트 셋업
- Sprint 2 (223 pt) — 가장 무거움. 횡단 통합(verifier/anchor/glossary) + frontend 동시 진행
- Sprint 3 (230 pt) — hardening + 운영(Ops) + tests + audit. Ops 행 12개 추가 영향

---

## 2. Team capacity 가정

**표준 2주 sprint (10 working day)**:
- BE 1명: 8 pt/week × 2 = 16 pt/sprint (순수 코딩 시간 6h/day 가정)
- FE 1명: 6 pt/week × 2 = 12 pt/sprint (UI 작업이 BE보다 환경 의존성 큼)
- SRE/Ops 0.5명: 6 pt/sprint (Ops 행 전담)

**1 BE + 1 FE team capacity**: 약 **24 pt/sprint** (mixed work + 코드 리뷰 + 회의 오버헤드 포함).
**1 BE + 1 FE + 0.5 SRE team capacity**: 약 **30 pt/sprint**.

multi-team 시나리오에서 cross-team 동조화 overhead는 추가 cost (-5%/팀 추가):
- 1 team: 24 pt
- 2 teams: 48 × 0.95 = ~46 pt
- 3 teams: 72 × 0.90 = ~65 pt

---

## 3. 5주 프로토타입 시나리오

5주 = **2.5 sprint** (1주 = sprint 0.5). Sprint 1 + half of Sprint 2.

### 3.1 1-team 시나리오 (24 pt × 2.5 = 60 pt budget)

**현실적 scope**:

| 우선순위 | 항목 | pt |
|---|---|---|
| 1 | #01a Search Sprint 1 (single-DB 검색 walking skeleton) | 21 |
| 2 | #02 Summarization Sprint 1 (infra/llm Owner + 한 문단 요약) | 13 |
| 3 | #03 Translation Sprint 1 (span 번역 walking skeleton) | 10 |
| 4 | #01b Ingest Sprint 1 (PDF→GROBID skeleton — #02 요약이 의존) | 13 |
| | Buffer (3 pt) | 3 |
| | **합계** | **60** |

**결과**: 검색·요약·번역·인입 walking skeleton 4종. UI 데모 가능. 환각 가드(verifier/anchor) 미적용 (Sprint 2 영역).

**미실현 기능**: #04, #05, #06, #07, #08, #09, #10, #11 — 모두 0%.

### 3.2 2-team 시나리오 (46 pt × 2.5 = 115 pt budget)

**현실적 scope**:

| 우선순위 | 항목 | pt | 팀 |
|---|---|---|---|
| 1 | #01a Search Sprint 1 + Sprint 2 | 37 | A |
| 2 | #01b Ingest Sprint 1 + Sprint 2 | 26 | B |
| 3 | #02 Summarization Sprint 1 + Sprint 2 일부 | 25 | A |
| 4 | #03 Translation Sprint 1 | 10 | B |
| | Buffer | 17 | |
| | **합계** | **115** | |

**결과**: 검색·인입 → Sprint 2 완성(다중 DB + 청크 벡터 저장). 요약 Sprint 2 일부(verifier/anchor Owner 포트). 번역 walking skeleton.

**미실현**: #04-#11.

### 3.3 시나리오 비교

| 항목 | 1-team | 2-team |
|---|---|---|
| 5주 ship 기능 수 | 4 (walking skeleton) | 4 (S1+S2 부분) |
| 데모 가능성 | 단순 흐름 | 환각 가드 포함 흐름 |
| 운영 가능성 | 없음 (Ops 행 미실현) | 없음 |
| Owner 포트 ship | infra/llm + glossary skeleton | + verifier + anchor + infra/embedding + temporal 없음 |
| 비용 견적 (월간) | ~$100 (MVP infra) | ~$500 (production-grade) |

**관찰**: 5주 안에는 어느 시나리오든 **운영 가능 production launch 불가**. 가장 빠른 production 경로는 2-team으로 Sprint 3까지 완성 (≈ 7주).

---

## 4. MVP scope (Sprint 3까지 5개 기능)

**목표**: 5개 핵심 기능(`#01a → #01b → #02 → #03 → #11`)을 Sprint 3까지 ship — 운영 가능 + 환각 가드 + Ops 출시.

**Budget**: 48 + 40 + 45 + 41 + 59 = **233 pt**

**팀 시나리오**:
- 1-team: 233 / 24 = 10 sprint = ~5개월
- 2-team: 233 / 46 = 5 sprint = ~2.5개월
- 3-team: 233 / 65 = 4 sprint = ~2개월

**권장**: **2-team으로 2.5개월** — 가장 cost-effective production launch.

---

## 5. Full launch scope (12개 기능 모두 Sprint 3까지)

**Budget**: 650 pt

**팀 시나리오**:
- 1-team: 27 sprint = ~12개월
- 2-team: 14 sprint = ~7개월
- 3-team: 10 sprint = ~5개월
- 4-team: 8 sprint = ~4개월 (조정 overhead 큼)

**권장**: **3-team으로 5개월** — 4-team 이상은 조정 overhead가 발생 (palpable diminishing returns).

---

## 6. Critical path — Owner 포트 의존성 그래프

각 Owner 포트의 Sprint 완료가 다른 기능의 Sprint 시작 시점을 차단:

```
Week 1-2  | #01a S1 (Router + arXiv)                     #04 S1 (Temporal 클러스터)
Week 3-4  | #01a S2 (Multi-DB + infra/embedding Owner)   #04 S2 (다채널 + Importance)
          | #01b S1 (PDF→GROBID skeleton, depends-on #01a)
Week 5-6  | #02 S1 (infra/llm Owner, depends-on #01b S2 for chunks)
          | #01b S2 (Chunker + Vector insert, depends-on #01a S2 infra/embedding)
          | #08 S1 (infra/citation_graph Owner)
Week 7-8  | #02 S2 (verifier + anchor Owner, depends-on #03 S1 glossary Owner)
          | #03 S1 (glossary Owner, depends-on #02 S1 infra/llm)
          | #11 S1 (Static classifier — independent)
Week 9+   | #03 S2, #05 S2, #06 S2, #07 S2, #09 S3, #10 S2 (all depends-on #02 S2)
```

**병목**: #02 S2 (verifier + anchor)가 7개 기능의 Sprint 2를 차단. **#02 S2 완료 시점이 critical path의 핵심.**

---

## 7. Heavy sprint 경고 (24 pt 초과)

다음 sprint는 capacity 초과 — 추가 분할 또는 멀티 팀 병렬화 필수:

| sprint | pt | 경고 |
|---|---:|---|
| #04 S1 (Temporal 셋업) | 21 | Temporal 8 pt 단일 행 — 인프라 작업 분할 검토 (HA 설정, RBAC, worker, sample workflow) |
| #04 S2 | 21 | 4 채널 dispatcher (5 pt) + State Differ (5 pt) 동시 — 가능 |
| #04 S3 | 21 | Ops row 5 pt + 부하 테스트 — Ops 전담 SRE 권장 |
| #06 S3 | 24 | Claim conflict (5) + Scope sensitivity (5) + Ops (3) — Sprint 4 분할 옵션 |
| #07 S2 | 24 | 다단 LLM 호출 5+5+5+3 — Opus 비용 사전 검토 |
| #07 S3 | 31 ⚠️ | **3 FE 행 + audit + tests + Ops** — 백엔드/프론트엔드/SRE 3분할 병렬화 필수. 1팀 시 Sprint 4 분할 |
| #09 S3 | 26 ⚠️ | verifier 100% sampling + prereview 모드 + 점수표 UI + Ops — Sprint 4 분할 옵션 |
| #11 S2 | 24 | Bandit (8) + Kanban UI (8) — 두 행 모두 전담 가능 인원 필요 |

**총 8개 sprint가 24 pt 초과.** Planning poker에서 split 결정 필수.

---

## 8. 권장 사항

1. **5주 프로토타입**: 1-team으로 검색·인입·요약·번역 walking skeleton 4개 — 데모 가능, 운영 불가. (Stage gate: 비즈니스 가치 검증)
2. **MVP 출시 (2.5개월)**: 2-team으로 #01a/#01b/#02/#03/#11 Sprint 3까지 — 운영 가능, 환각 가드 + Ops 포함. (Stage gate: 첫 유료 사용자)
3. **확장 출시 (5개월)**: 3-team으로 12개 기능 모두 Sprint 3 — 풀 production. (Stage gate: 학술 기관 통합)
4. **Heavy sprint 8개**: planning poker 시 분할 결정. 특히 #07 S3 (31 pt)는 단일 팀 capacity 초과 — Sprint 4 도입 또는 frontend split sub-team.
5. **#02 S2 critical path**: 모든 다운스트림 기능이 의존 — Sprint 2 종료 즉시 export 가능 상태로 강제. delay 시 cascading 영향.
6. **운영 가시성**: 5주 프로토타입은 의도적으로 Ops 행 0개. 그러나 MVP 출시 전 모든 Sprint 3 Ops 행 100% 완성 — 운영 없는 production launch 금지 (AGENTS.md §4.6).

---

## 9. 기능별 비용 vs 사용 빈도 매트릭스

ROI 기반 우선순위 재검토:

| 기능 | 단위 비용 | 예상 사용 빈도 | Lock-in | ROI 순위 |
|---|---|---|---|---|
| #11 Priority | $0.06 | 매우 높음 (주 2회) | 강 (Bandit 학습) | 1 |
| #02 Summary | $0.05-0.28 | 높음 | 중 (glossary 누적) | 2 |
| #03 Translation | $0.04 | 중 | 중 (glossary 공유) | 3 |
| #09 Reproducibility | $0.09 | 중 | 약 | 4 |
| #01a Search | <$0.01 | 매우 높음 (모든 사용) | 매우 약 | 5 (토대지만 단독 가치 약) |
| #04 Monitoring | $0.005 | 자동 | 강 (구독 누적) | 6 |
| #08 Citation | $0.25 | 중 | 약 | 7 |
| #05 Exploration | $0.07 | 중 | 약 | 8 |
| #07 Project-Trend | $7 | 낮음 (3개월 재분석) | 중 | 9 |
| #06 Research-Gap | $12 | 매우 낮음 (분기 1회) | 약 | 10 |
| #10 Reading | $0.15-3 | 중 | 약 | 11 |
| #01b Ingest | $0.01 (parsing) | 매우 높음 (수동) | 매우 약 | (토대) |

**관찰**: AGENTS.md §3.1 빌드 순서 `01a→01b→02→11→09→03→04→...`는 ROI 순서와 거의 일치. #11이 빠른 단계에 진입하는 게 정당화됨.
