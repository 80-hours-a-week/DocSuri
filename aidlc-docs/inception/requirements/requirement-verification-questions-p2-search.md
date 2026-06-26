# 페이즈 2 검색(U2 Discovery) — 요구사항 명확화 질문 (Requirement Verification — Search)

**단계**: INCEPTION → Requirements Analysis 재진입 (재인셉션 페이즈 2) · **일자**: 2026-06-26
**담당**: 본인
**대상 기능**: 자연어 질의 검색 — Normalize → **Hybrid Search(Lexical+Semantic)** → Ranking → **Grounding(페이즈 4)** → 결과. **D6 인덱스 소스 전환**(full-text 청크 → DocModel Block) 반영.
**영향 유닛**: U2(`backend/modules/discovery/`) · `shared/vector-spec`(인덱스 계약) · U1(인덱스 writer, D6) · 페이즈 4(grounding).
**근거 SSOT**: 차터 `inception/plans/reinception-2026-06-charter.md`(**D6**) · 베이스라인 `inception/reverse-engineering/code-baseline-2026-06.md`.
**답변 상태**: ⏳ **답변 대기**. 각 질문에 차터 기반 **권장(차터)** 을 별도 줄로 적어두었다. `[Answer]:` 는 비워 두었으니 **letter(A/B/X)** 로 채워 주세요.

> **성격**: 페이즈 2는 그린필드가 아니다 — discovery 모듈(HybridRetriever·ranker·assembler·validator·expander·grounding_adapter)이 이미 존재한다. 이번 작업의 실체는 **D6 인덱스 전환 반영 + 페이즈 4 grounding 통합 정합**이다.
> **실질 갈림길**: **Q1(인덱스 소스 전환)·Q3(청크/dedup 의미)**.

---

## Q1. 인덱스 소스 전환 — full-text → DocModel Block — **실질 갈림길 (D6)**

검색 인덱스의 청크 소스를 무엇으로 하는가? (U1 질문지 Q6과 한 쌍.)
(현재 코드: `HybridRetriever` = k-NN ∥ BM25 → RRF → PaperId dedup, **full-body multi-chunk** 인덱스; `RETRIEVAL_TOP_K=150`.)

- **A) DocModel(Block) 기반 청크로 전환** (차터 D6): U1이 DocModel Block 경계로 청킹·임베딩 → U2는 동일 인덱스 reader. 표/수식이 검색 후보에 가시.
- **B) full-text 청크 유지** — 현행.
- **X) 기타**(본문 DocModel + 표/수식 별도 필드 병행)

[Answer]:
**권장(차터·D6)**: A — U1 Q6과 동일. specVersion/model/dimensions 불변(임베딩 모델 변경 아님; U1 Q8), 소스만 전환.

---

## Q2. Hybrid 검색·융합 전략 유지

검색 융합·dedup 전략을 무엇으로 하는가?

- **A) k-NN ∥ BM25 → RRF(Reciprocal Rank Fusion) → PaperId dedup 유지** (현행):
  scale-invariant. lexical-only degrade(비용/임베딩 폴백) 경로 유지. 개선(reranker 등)은 페이즈 8.
- **B) 전략 변경(가중합 등)**.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q3. 청크 단위 변경에 따른 dedup·결과 단위 — **실질 갈림길**

DocModel Block 청크(Q1=A) 전환 시 "paper당 1 레코드" dedup과 결과 노출 단위를 어떻게 하는가?
(현행: 한 논문이 여러 청크 → PaperId로 dedup, paper당 best chunk rank.)

- **A) PaperId dedup 유지 + best Block 청크 rank**(현행 의미 보존):
  결과는 paper 단위 카드, 매칭 근거는 Block 청크. `RETRIEVAL_TOP_K` 재튜닝(Block 청크 수 변화 반영).
- **B) Block/Section 단위 결과 노출**(논문 내 위치까지 결과로) — UX·랭킹 변경 큼.
- **X) 기타**

[Answer]:
**권장(차터)**: A — paper 단위 유지, Block은 근거/스니펫. `RETRIEVAL_TOP_K`는 NFR/Infra 재튜닝.

---

## Q4. 검색 Grounding — 페이즈 4 통합과 정합

검색 grounding을 어떻게 두는가?
(현행: `GroundingAdapter`(thin) → `GroundingEnforcementHook.enforce`(U6 단일권위, candidate ↔ retrieved record SET) → pass/abstain.)

- **A) 현행 U6 enforce(검색 grounding) 유지 + 페이즈 4 통합 인터페이스의 "Search Validator"로 편입** (차터 D3):
  enforce 시그니처(FROZEN) 불변. U2는 어댑팅만. 통합은 인터페이스/관측 일원화이지 검색 enforce 권위 이전 아님.
- **B) U2가 자체 grounding 보유** — 단일권위 원칙 위반(기각).
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q5. 저하·실패 모드 유지

비용/의존 실패 처리를 무엇으로 하는가?

- **A) 현행 유지**: 임베딩 실패 → lexical-only 저하(`EmbeddingUnavailable`), 인덱스 실패 → fail-closed(`IndexUnavailable`→`SearchUnavailable`), 비용 degrade → `CostGuard.getBudgetState` 분기.
- **B) 변경**.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q6. 검색 품질 개선 항목의 분리

reranker·LTR·query expansion 고도화·click log 기반 랭킹·personalization을 페이즈 2에 넣는가?

- **A) 페이즈 8로 분리**(차터): 페이즈 2는 **안정화 + D6 전환 + grounding 통합**까지. 품질 고도화는 페이즈 8.
- **B) 페이즈 2에 일부 포함**.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q7. 관측·이벤트 유지

검색 관측을 무엇으로 하는가?

- **A) `SearchExecuted` 이벤트 + `ObservabilityHub`(emitMetric/emitLog/startSpan) 유지** (현행/`shared/ports`):
  검색 지연·에러·grounding 헬스 측정. 핵심 경로 관측(차터 Part 2-A 관측성).
- **B) 변경**.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## 다음 단계

답변(특히 **Q1·Q3**) 확정 후 → `requirements.md`에 페이즈 2 FR/NFR/C 등재. Q1은 U1 Q6과 **한 쌍으로** 확정(인덱스 writer↔reader 동일 공간 불변식, `shared/vector-spec`).
