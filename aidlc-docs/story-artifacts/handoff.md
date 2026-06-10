# DocSuri MVP — Inception › User Stories 인계 노트 (Handoff)

- **단계 전환**: AI-DLC › Inception › User Stories **→** Construction › Architecture/Design
- **Inception 1차 동결**: 2026-06-10 ([Prompt 12](../prompts.md#prompt-12) 옵션 1)
- **Unit 분해 동결**: 2026-06-10 ([Prompt 21](../prompts.md#prompt-21))
- **Inception 단계 종료**: ✅ 2026-06-10 — 본 노트 + Unit 분해까지 모든 Inception 산출물 동결. 다음 단계는 *Architecture Decision Records*.
- **상태**: 페르소나 · Epic · NFR · 사용자 스토리 · 커버리지 매트릭스 · Unit 분해 6종 동결. 모바일 검토 반영 완료.

본 파일은 다음 단계(아키텍처/설계)가 *Inception 산출물*만으로 작업을 시작할 수 있도록 인계용 요약 + 위험 + 가정 + 결정 필요 사항을 한곳에 모은다.

---

## 1. 동결된 산출물

| 분류 | 파일 | 동결 내용 |
|---|---|---|
| 페르소나 | [`personas.md`](personas.md) | P1 박지훈 · P2 김민서 (디바이스 비중·모바일 시나리오 포함) |
| Epic | [`../requirements/epics.md`](../requirements/epics.md) | E1·E2·E3 + E4 일부 · MVP 디바이스 정책 명시 |
| NFR | [`../requirements/nfr.md`](../requirements/nfr.md) | PERF·UX·LANG·DATA·SEC·COST·A11Y·**MOBILE**·**NET**·OBS 10개 카테고리 / **NFR 키 33개** |
| 사용자 스토리 | [`user_stories.md`](user_stories.md) | 14 스토리 / 70 SP / MoSCoW 분류 |
| 색인 | [`story_index.md`](story_index.md) | ID·제목·우선순위 한 페이지 색인 |
| 커버리지 | [`coverage_matrix.md`](coverage_matrix.md) | 페르소나×Epic, 디바이스×페르소나, 디바이스×Epic, INVEST+M축, NFR 인용 분포 |
| 결정 로그 | [`../plans/user_stories_plan.md`](../plans/user_stories_plan.md), [`../plans/mobile_review_plan.md`](../plans/mobile_review_plan.md), [`../plans/units_plan.md`](../plans/units_plan.md) | 부록 A 결정 10건 + 모바일 결정 5건 + Unit 결정 7건 |
| **Unit 분해** | [`../design-artifacts/units/`](../design-artifacts/units/) | U0 Foundation + U1 Discover + U2 Comprehend + U3 Differentiate + U4 Trace + [overview](../design-artifacts/units/units-overview.md). 14 스토리 → 5 unit (누락·중복 0), cross-unit 포트 8개 + DTO 2개. |
| 출처 로그 | [`../prompts.md`](../prompts.md) | Prompt 1~21 (스토리 출처는 모두 [Prompt 2](../prompts.md#prompt-2)) |

### MoSCoW 분포 (동결)

| 분류 | 수 | SP |
|---|---|---|
| Must | 6 | 29 |
| Should | 5 | 28 |
| Could | 3 | 13 |
| **합계** | **14** | **70** |
| **MVP(Must+Should)** | **11** | **57** |

---

## 2. Open Risks (다음 단계가 닫아야 할 위험)

위험은 **확률 × 영향**으로 등급을 매기고, 닫는 책임이 아키텍처/설계 단계에 있다.

> Unit 분해(2026-06-10) 이후, 각 위험을 *어느 unit이* 닫는지는 마지막 컬럼 참조. 자세한 매핑은 [`units-overview.md §5.1`](../design-artifacts/units/units-overview.md).

| ID | 위험 | 확률 | 영향 | 닫는 방법 | 닫는 Unit |
|---|---|---|---|---|---|
| <a id="r-1"></a>R1 | **Mobile UX 미확정 5건** — [DISC-02](user_stories.md#us-disc-02) 모바일 필터 UI, [DISC-03](user_stories.md#us-disc-03) 확장 키워드 칩, [COMP-01](user_stories.md#us-comp-01) 모바일 요약 레이아웃, [DIFF-01](user_stories.md#us-diff-01)/[02](user_stories.md#us-diff-02) 모바일 입력 폼 (현재 *읽기 전용 결과 확인*만 가정) | 高 | 中 | 디자인 단계에서 모바일 와이어프레임 작성 + AC 보강 | [U1](../design-artifacts/units/unit-u1-discover.md) · [U2](../design-artifacts/units/unit-u2-comprehend.md) · [U3](../design-artifacts/units/unit-u3-differentiate.md) |
| <a id="r-2"></a>R2 | **SP 8 스토리 3건** — [US-DIFF-01](user_stories.md#us-diff-01), [DIFF-02](user_stories.md#us-diff-02), [TRACE-01](user_stories.md#us-trace-01). INVEST의 *Small*에 ⚠️ 표시됨 | 中 | 中 | 아키텍처 단계에서 컴포넌트 분해 후 스토리 분할 가능성 재평가 | [U3](../design-artifacts/units/unit-u3-differentiate.md) · [U4](../design-artifacts/units/unit-u4-trace.md) |
| <a id="r-3"></a>R3 | **LLM 비용 변동성** — [NFR-COST-01](../requirements/nfr.md#nfr-cost-01) 월 USD 50 상한이 요약·차별성 분석·모바일 추가 호출까지 흡수 가능한지 미검증 | 中 | 高 | 프롬프트 길이 시뮬레이션 + 모델 선택 결정 시 정산 | [U0](../design-artifacts/units/unit-u0-foundation.md) (게이트웨이 상한) · [U2](../design-artifacts/units/unit-u2-comprehend.md) · [U3](../design-artifacts/units/unit-u3-differentiate.md) (호출 측 압축) |
| <a id="r-4"></a>R4 | **인용 그래프 API 의존** — Semantic Scholar API 변동·할당량·지연이 [NFR-PERF-03](../requirements/nfr.md#nfr-perf-03)/[NFR-MOBILE-03](../requirements/nfr.md#nfr-mobile-03) 목표를 깨뜨릴 수 있음 | 中 | 中 | 아키텍처 단계에서 *캐시 + 폴백 전략* 결정 | [U0](../design-artifacts/units/unit-u0-foundation.md) (캐시·폴백) · [U4](../design-artifacts/units/unit-u4-trace.md) (사용·실증) |
| <a id="r-5"></a>R5 | **학술 용어 사전 수기 50개** — [NFR-LANG-03](../requirements/nfr.md#nfr-lang-03)이 일관 번역을 요구하나 50개로는 분야별 변형 부족 가능 | 中 | 低 | MVP 코퍼스 범위 좁히기 또는 사전 자동 시드 도구 도입 | [U0](../design-artifacts/units/unit-u0-foundation.md) (`Glossary`) · [U2](../design-artifacts/units/unit-u2-comprehend.md) (적중률 보고) |
| <a id="r-6"></a>R6 | **오프라인 24h 캐시** — [NFR-NET-04](../requirements/nfr.md#nfr-net-04). PWA·Service Worker·LocalStorage 중 어느 메커니즘인지 미정 | 中 | 中 | 프론트엔드 프레임워크 선택과 함께 결정 | [U0](../design-artifacts/units/unit-u0-foundation.md) (`CachePort` 클라이언트 구현) |
| <a id="r-7"></a>R7 | **재현 가능성·알림·개인화 Won't 항목** — 사용자가 데모 후 즉시 요구할 가능성 | 中 | 低 | 후속 사이클 백로그로 *명시적* 등록 | (제품 관리 — unit 분해 밖) |

---

## 3. Assumptions (다음 단계가 그대로 신뢰해도 되는 전제)

본 사이클이 가정한 사항. 가정이 깨지면 스토리 재작성이 필요하다.

- <a id="a-1"></a>**A1.** arXiv 메타데이터 + Semantic Scholar 인용 그래프가 **공개 API**로 데모 트래픽 범위에서 조회 가능하다.
- <a id="a-2"></a>**A2.** MVP는 **비로그인 익명 세션**으로 충분하다 ([NFR-SEC-01](../requirements/nfr.md#nfr-sec-01)).
- <a id="a-3"></a>**A3.** [박지훈](personas.md#p1)의 모바일 사용 시나리오는 *트리아지/큐레이션* 한정이며, **차별성 분석·노트 작성은 데스크톱**에서 수행한다.
- <a id="a-4"></a>**A4.** [김민서](personas.md#p2)는 *학부 1~2학년 수준 한국어*(능력시험 4급) 가독성으로 충분히 이해 가능한 학습자이다.
- <a id="a-5"></a>**A5.** MVP의 코퍼스는 **AI/ML 분야**로 한정한다 (전 분야 일반화는 후속 사이클).
- <a id="a-6"></a>**A6.** 학술 용어 사전은 **수기 50개로 시드**하고, 부족분은 *[NFR-LANG-03](../requirements/nfr.md#nfr-lang-03) 위반*이 아닌 *알려진 한계*로 표기한다.
- <a id="a-7"></a>**A7.** 검색 결과의 *난이도 추정 점수*는 휴리스틱(분야 태그 + 인용수 + 길이 + 어휘 빈도)으로 산출하며 정식 분류 모델이 아니다.
- <a id="a-8"></a>**A8.** [US-COMP-04](user_stories.md#us-comp-04) 모바일 분기에서 **바텀시트 패턴**을 가정 (확정 디자인은 아님).

---

## 4. 다음 단계가 내려야 할 결정 (Open Decisions)

아키텍처/설계 단계가 진입 직후 결정해야 한다. 각 항목에 *권장 후보*만 적고 최종 선택은 다음 단계의 권한.

> Unit 분해(2026-06-10) 이후, 각 결정의 *진입 unit*은 마지막 컬럼 참조. 자세한 매핑은 [`units-overview.md §5.2`](../design-artifacts/units/units-overview.md). [U0 Foundation](../design-artifacts/units/unit-u0-foundation.md)에 **7개 결정(D1·D2·D3·D4·D8·D9·D10)이 집중**되므로 이 unit의 진입 라운드에 한꺼번에 닫는 것이 권장.

| ID | 결정 항목 | 후보 | 진입 Unit |
|---|---|---|---|
| <a id="d-1"></a>D1 | **백엔드 언어/프레임워크** | 기존 데모(`demo/app`)는 Python/FastAPI 추정. 동일 유지 vs Node.js/Bun 신규 | [U0](../design-artifacts/units/unit-u0-foundation.md) |
| <a id="d-2"></a>D2 | **임베딩 인덱스** | FAISS (자체 호스팅) / pgvector / Chroma / Pinecone — 비용·운영 부담 vs 성능 | [U0](../design-artifacts/units/unit-u0-foundation.md) |
| <a id="d-3"></a>D3 | **임베딩 모델** | OpenAI text-embedding-3-small / Voyage / 한국어 특화(BGE-M3) | [U0](../design-artifacts/units/unit-u0-foundation.md) |
| <a id="d-4"></a>D4 | **LLM 모델** | Claude Sonnet/Haiku / GPT-4o-mini / Bedrock 경유 — [NFR-COST-01](../requirements/nfr.md#nfr-cost-01)과 직결 | [U0](../design-artifacts/units/unit-u0-foundation.md) |
| <a id="d-5"></a>D5 | **프론트엔드 프레임워크** | 기존 `web/` Next.js 추정. 그대로 유지 vs SvelteKit/Astro 등 | [U1](../design-artifacts/units/unit-u1-discover.md) (UI 최초 진입) |
| <a id="d-6"></a>D6 | **컴포넌트 라이브러리·디자인 시스템** | shadcn/ui · Mantine · Chakra · 자체 — 모바일 친화 점수 비교 | [U1](../design-artifacts/units/unit-u1-discover.md) |
| <a id="d-7"></a>D7 | **그래프 시각화 라이브러리** ([TRACE-01](user_stories.md#us-trace-01) 데스크톱) | react-flow / Sigma.js / Cytoscape — 모바일 분기는 그래프 불필요 | [U4](../design-artifacts/units/unit-u4-trace.md) |
| <a id="d-8"></a>D8 | **오프라인 캐시 메커니즘** ([NFR-NET-04](../requirements/nfr.md#nfr-net-04)) | Service Worker(PWA) / IndexedDB 직접 / localStorage | [U0](../design-artifacts/units/unit-u0-foundation.md) |
| <a id="d-9"></a>D9 | **호스팅 환경** | Vercel + 서버리스 / 자체 VPS / AWS Bedrock 묶음 | [U0](../design-artifacts/units/unit-u0-foundation.md) |
| <a id="d-10"></a>D10 | **관찰가능성 스택** (NFR-OBS) | Sentry / OpenTelemetry / 자체 로그 | [U0](../design-artifacts/units/unit-u0-foundation.md) |

> 본 표는 결정을 강제하지 않는다. 다음 단계 첫 산출물(예: `aidlc-docs/design-artifacts/architecture_decision_record.md`)에서 각 항목을 *기록·승인*하면 된다.

---

## 5. 다음 단계 권장 입력 순서

Unit 분해(2026-06-10)가 완료되어, *unit 단위로* 다음 단계를 진입한다.

1. **본 인계 노트 + [`units-overview.md`](../design-artifacts/units/units-overview.md)**를 1차 읽기. (다른 산출물은 결정이 필요할 때만 펼쳐 본다)
2. **[U0 Foundation](../design-artifacts/units/unit-u0-foundation.md) 진입 라운드**에서 [D1·D2·D3·D4·D8·D9·D10](#4-다음-단계가-내려야-할-결정-open-decisions) **7개 결정**을 한꺼번에 닫는다 — 다른 4 unit이 모두 U0 포트 시그니처에 묶여 있다.
3. U0 포트 시그니처 동결 직후 [U1](../design-artifacts/units/unit-u1-discover.md) · [U2](../design-artifacts/units/unit-u2-comprehend.md)를 **병렬** 진입 (둘은 서로 의존하지 않는다).
4. U1 `SearchResult` + U2 `SummaryResult` 안정화 후 [U3](../design-artifacts/units/unit-u3-differentiate.md) · [U4](../design-artifacts/units/unit-u4-trace.md)를 **병렬** 진입.
5. 각 unit의 §6 *Definition of Buildable*이 통과될 때마다 본 노트 §2의 해당 위험을 닫는다.
6. unit 간 합의 지점 ([`units-overview.md §4`](../design-artifacts/units/units-overview.md))이 깨지면 *조용한 수정 금지* — §6 변경 정책 따른다.

---

## 6. 동결 후 변경 정책

본 인계 노트 이후 스토리·NFR을 *변경*하려면:

1. `prompts.md`에 변경 요청 프롬프트를 새로 기록.
2. `aidlc-docs/plans/`에 변경 계획서 신설.
3. 사용자 승인 후 산출물 수정.
4. 본 인계 노트의 §1 표와 §2 위험 항목을 갱신.

> *조용한 수정 금지* — 동결 이후의 모든 변경은 위 4단계를 거친다.
