# DocSuri MVP — Architecture Decision Records (ADR)

> **Phase**: AIDLC Construction — Architecture/Design
> **위상**: [`handoff.md §4`](../story-artifacts/handoff.md)가 권고한 "다음 단계 첫 산출물". Open Decisions D1~D10의 *기록·승인* 장부.
> **입력**: [`tech-stack-aws-candidates.md`](tech-stack-aws-candidates.md) (후보 조사) · [`component-model.md`](component-model.md) (확정 컴포넌트 모델) · [`nfr.md`](../requirements/nfr.md)
> **운영 방식**: 결정이 내려질 때마다 ADR 절을 추가하고 §1 현황판을 갱신한다. 결정 변경은 [`handoff.md §6`](../story-artifacts/handoff.md) 4단계(프롬프트→계획→승인→동기 갱신)를 따른다.

---

## 1. 결정 현황판 (2026-06-10 기준)

**10/10 확정** (2026-06-10, 사용자·팀 협의). 기준 리전: **ap-northeast-2 (서울)** — 당초 D3 연쇄로 도쿄 확정했으나 **2026-06-11 ADR-D3 재검토**([Prompt 26](../prompts.md#prompt-26), [`adr_d3_reconsideration_plan.md`](../plans/adr_d3_reconsideration_plan.md))로 서울+Titan 환원 ([ADR-D3](#adr-d3)).

| ID | 항목 | 상태 | 결정 |
|---|---|---|---|
| [D1](../story-artifacts/handoff.md#d-1) | 백엔드 언어/프레임워크 | ✅ 승인 | **Python 3.12 + FastAPI** (Lambda Web Adapter) → [ADR-D1](#adr-d1) |
| [D2](../story-artifacts/handoff.md#d-2) | 임베딩 인덱스 | ✅ 승인 | **Bedrock Knowledge Bases + S3 Vectors** → [ADR-D2](#adr-d2) |
| [D3](../story-artifacts/handoff.md#d-3) | 임베딩 모델 | ✅ 승인 (2026-06-11 재검토) | **Titan Text Embeddings V2** (서울) → [ADR-D3](#adr-d3) |
| [D4](../story-artifacts/handoff.md#d-4) | LLM 모델 | ✅ 승인 | **Claude Haiku 4.5** (`global.` CRIS) → [ADR-D4](#adr-d4) |
| [D5](../story-artifacts/handoff.md#d-5) | 프론트엔드 프레임워크 | ✅ 승인 | **Next.js App Router + Amplify Hosting** → [ADR-D5](#adr-d5) |
| [D6](../story-artifacts/handoff.md#d-6) | 컴포넌트 라이브러리 | ✅ 승인 | **shadcn/ui + Tailwind CSS** → [ADR-D6](#adr-d6) |
| [D7](../story-artifacts/handoff.md#d-7) | 그래프 시각화 | ✅ 승인 | **React Flow** → [ADR-D7](#adr-d7) |
| [D8](../story-artifacts/handoff.md#d-8) | 오프라인 캐시 | ✅ 승인 | **Service Worker(Serwist) + IndexedDB** → [ADR-D8](#adr-d8) |
| [D9](../story-artifacts/handoff.md#d-9) | 호스팅 환경 | ✅ 승인 (2026-06-11 리전 갱신) | **풀 서버리스 (AWS, 서울)** → [ADR-D9](#adr-d9) |
| [D10](../story-artifacts/handoff.md#d-10) | 관찰가능성 스택 | ✅ 승인 | **CloudWatch(EMF) + Bedrock 호출 로깅 + X-Ray** → [ADR-D10](#adr-d10) |

**결정 외 동결 기록**

| 산출물 | 상태 |
|---|---|
| [`component-model.md`](component-model.md) (도메인/컴포넌트 모델) | ✅ **확정** (2026-06-10 사용자 승인, [`component_model_plan.md`](../plans/component_model_plan.md) C-V4 종료). 이후 변경은 handoff §6 4단계. |

---

<a id="adr-d9"></a>
## 2. ADR-D9 — 호스팅: 풀 서버리스 (AWS)

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의)
- **컨텍스트**: 데모 서비스는 트래픽이 간헐적이고 LLM 비용 상한이 월 $50([NFR-COST-01](../requirements/nfr.md#nfr-cost-01))로 묶여 있어 *유휴 고정비*가 예산의 적이다. 운영 인력이 없는 소규모 팀이라 관리형 우선. 후보 3안 비교는 [조사 §10](tech-stack-aws-candidates.md).
- **결정**: **(a) 풀 서버리스** — Amplify Hosting(프론트) + Lambda(백엔드, Web Adapter) + DynamoDB(TTL 캐시·텔레메트리·용어집) + Bedrock(LLM·임베딩). 기준 리전 **ap-northeast-2(서울)** — 당초 [ADR-D3](#adr-d3) 연쇄로 도쿄 통일(2026-06-10)했으나, **2026-06-11 ADR-D3 재검토**([Prompt 26](../prompts.md#prompt-26))로 서울 환원: Cohere 교차언어 우위가 실측에서 미검증 + LLM은 `global.` CRIS라 리전 무관이라, 홈 리전 서울이 지연·운영 면에서 우위. 한국 사용자 지연 페널티 제거됨.
- **근거**:
  1. 유휴 비용 ~$0 — Lambda·DynamoDB·Amplify 무료 티어로 데모 트래픽 흡수 ([조사 §12](tech-stack-aws-candidates.md): LLM 제외 월 $0~3).
  2. 콜드스타트 ~1-2초는 *첫 호출*에 국한 — P50(중앙값) 기준 [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01)(<3s)은 warm 경로가 지배. 필요 시 EventBridge 핑으로 완화.
  3. TLS·배포·스케일이 전부 관리형 — (c) VPS 안의 수동 운영 부담 제거.
- **기각된 대안**: (b) App Runner 상시 컨테이너 — 콜드스타트는 없으나 유휴에도 $3~13/월 고정비 + 컨테이너 관리. (c) 자체 VPS — 최저가지만 TLS·배포·보안 패치 수동.
- **결과 (Consequences)**:
  1. **D2 연쇄**: Lambda는 영속 로컬 디스크가 없어 임베디드 벡터 라이브러리(Chroma/FAISS 파일)가 불가 → 관리형 벡터 스토어 필수 ([ADR-D2](#adr-d2)로 이어짐).
  2. **D1 제약**: 백엔드는 Lambda 탑재 가능해야 함 (Python/FastAPI는 Web Adapter, Node도 가능 — 후보 모두 충족).
  3. `CachePort`([component-model §2.3](component-model.md))의 서버측 구현은 **DynamoDB TTL**로 사실상 확정 (24h/7d 자동 만료가 [NFR-DATA-03](../requirements/nfr.md#nfr-data-03)과 1:1).
  4. `CostGuard` 누적치·`Telemetry` 질의 저장소도 DynamoDB로 수렴 (Lambda 무상태). D10의 대시보드·로그 스택 선택은 별도 미결.
  5. 콜드스타트가 [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01) 위반으로 관측되면 EventBridge 워밍 또는 (b)안 전환을 재논의 — 전환 비용은 코드 레벨에서 낮게 유지 (FastAPI는 양쪽 동일 코드).
- **NFR 추적**: COST-01(유휴 $0) · PERF-01(콜드스타트 완화 전략 명시) · NET-02(재시도는 코드 레벨 `HttpClientPolicy`) · SEC-03(키는 Lambda 환경 변수/SSM).
- **검증 항목 (환경 구축 시)**: 콜드스타트 실측이 P50<3s에 미치는 영향 측정 ([U0 §6](units/unit-u0-foundation.md) 빌드 가능 정의에 포함). → ✅ **실측 완료 (2026-06-11)**: 컨테이너 이미지 Lambda(arm64) 콜드 init P50 887ms(정상상태 750~990ms, 최초 2.8s)·웜 ~2ms → P50<3s 위협 없음, **EventBridge 워밍 발동 조건 미충족 · D9 결정 유지** ([검증 보고서 §3](../reviews/u0-aws-env-verification.md)).

---

<a id="adr-d2"></a>
## 3. ADR-D2 — 임베딩 인덱스: Bedrock Knowledge Bases + S3 Vectors

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의) · **전제**: [ADR-D9](#adr-d9) 풀 서버리스
- **컨텍스트**: `EmbeddingPort.search`는 연도·분야 메타데이터 필터([US-DISC-02](../story-artifacts/user_stories.md#us-disc-02))를 지원해야 하고, 코퍼스는 AI/ML 100편 시드([A5](../story-artifacts/handoff.md#a-5))로 작다. D9 확정으로 임베디드 라이브러리가 탈락한 상태. 후보 비교는 [조사 §3](tech-stack-aws-candidates.md).
- **결정**: **Amazon Bedrock Knowledge Bases + S3 Vectors** (벡터 스토어). S3 Vectors는 서울·도쿄 모두 GA 확인(2026-06-10, [조사 §15 출처](tech-stack-aws-candidates.md)) — 최종 리전은 **서울** ([ADR-D3](#adr-d3) 재검토 연쇄, 2026-06-11). 인덱스 1024차원(Titan V2).
- **근거** (소거 구조 — [조사 §3](tech-stack-aws-candidates.md)):
  1. OpenSearch Serverless: 유휴 최소 ~$175/월 → [NFR-COST-01](../requirements/nfr.md#nfr-cost-01) 위반으로 탈락.
  2. Aurora Serverless v2 pgvector: 0 ACU auto-pause 재개 ~15초가 첫 검색의 [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01)(P50<3s) 위협 → 탈락.
  3. 임베디드(Chroma/FAISS): D9(Lambda 비영속 디스크)로 물리적 불가 → 탈락.
  4. 남은 S3 Vectors: 월 <$1 + 콜드스타트 없음 + **메타데이터 필터 내장**(DISC-02 직결) + KB 결합 시 청킹·임베딩·동기화 관리형(CorpusIndex 1회 빌드 = S3 업로드 + KB 동기화, [A1](../story-artifacts/handoff.md#a-1)).
- **기각된 대안**: 상기 1~3 + Pinecone(비-AWS 의존, AWS 중심 방침과 불일치).
- **결과 (Consequences)**:
  1. `EmbeddingPort.search` 구현 = KB `Retrieve` API(+ metadata filter). `EmbeddingPort.embed` 단독 호출이 필요한 경로(예: [U3 SimilarPaperFinder](component-model.md)의 주제 초안 임베딩)는 Bedrock `InvokeModel` 직접 호출.
  2. 시그니처 영향 0 — [component-model §2.1](component-model.md)의 포트 계약 그대로, 구현체만 결정됨 ([U0 §8](units/unit-u0-foundation.md) 변경 정책의 "단독 변경 가능" 범위).
  3. **S3 Vectors 신생 리스크** (GA 2025-12): 장애·기능 공백 시 `EmbeddingPort` 추상화 뒤에서 교체 — 1차 폴백은 S3 Vectors **직접 API**(PutVectors/QueryVectors, KB 우회), 2차는 Aurora pgvector.
  4. ⚠️ **D3 연쇄 제약 (2026-06-10 웹 확인)**: KB 임베딩 모델의 리전 지원에서 **서울은 Titan Text Embeddings V2만 가능**. Cohere Embed Multilingual v3(조사 시 D3 1순위 후보)는 KB 기준 **도쿄(ap-northeast-1)에만** 있음. 검토된 3안:
     - (i) 서울 유지 + Titan V2 — `KoEnQueryMapper`의 한→영 매핑이 교차언어 약점 우회. 운영 최단순.
     - (ii) 도쿄로 리전 이동 + Cohere Multilingual — 교차언어 품질 우선. S3 Vectors 도쿄 GA 확인됨.
     - (iii) KB 우회, S3 Vectors 직접 API — 모델 제약 해제, 청킹·동기화 자체 구현.
     → **팀 결정 (2026-06-10): (ii) 채택** — [ADR-D3](#adr-d3)에 기록. **⟳ 2026-06-11 재검토로 (i)안(서울+Titan)으로 환원** — [Prompt 26](../prompts.md#prompt-26)·[재검토 계획](../plans/adr_d3_reconsideration_plan.md). 실측에서 Titan=Cohere 동률이라 (ii)의 교차언어 우위 전제가 무너짐.
  5. KB×S3 Vectors 결합의 **서울** 리전 가용성은 콘솔에서 최종 확인 (불가 시 결과 4의 (iii) 폴백). *(2026-06-11 재검토로 도쿄→서울.)*
- **NFR 추적**: COST-01(<$1) · PERF-01(관리형 API, 콜드 없음) · DATA-01(arXiv 메타 S3 적재) · MOBILE-03(검색 경로 동일).
- **검증 항목 (환경 구축 시)**: ① **서울** KB×S3 Vectors 생성 가능 여부(Titan V2 1024d) ② KB Retrieve의 연도 범위 필터(`year >= 2023` 형태) 표현력 ③ 100편 코퍼스 동기화 소요·비용 실측. → ✅ **선검증 완료 (2026-06-11, 도쿄+Cohere)**: ① KB(S3_VECTORS)+Cohere v3 1024d 생성·8편 색인 0실패 16.4s → **폴백(iii) 불요**. ② `greaterThanOrEquals`/`andAll`(KB Retrieve)·`$gte`/`$and`(S3 Vectors) 양쪽 정확 동작. ③ 8편 16.4s 선검증(100편 미수행) ([검증 보고서 §1·§2](../reviews/u0-aws-env-verification.md)). ⚠️ **이 선검증은 ADR-D3 재검토 *이전*의 도쿄+Cohere 조합** — *접근법 타당성*은 입증됐으나 확정 스택은 서울+Titan이므로 **서울+Titan 재검증이 잔여**([재검토 계획 §4](../plans/adr_d3_reconsideration_plan.md)).

---

<a id="adr-d1"></a>
## 4. ADR-D1 — 백엔드: Python 3.12 + FastAPI

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의)
- **컨텍스트**: U0 포트 7종 + 도메인 unit 로직의 호스트. [ADR-D9](#adr-d9) 확정으로 Lambda 탑재 가능 조건. 후보 비교는 [조사 §2](tech-stack-aws-candidates.md).
- **결정**: **Python 3.12 + FastAPI**, [AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter)로 컨테이너 이미지 탑재.
- **근거**: boto3·PDF 추출([U2 §5](units/unit-u2-comprehend.md) 후보 PyMuPDF/pdfplumber)·텍스트 처리 생태계가 모두 Python 우선. 동일 코드로 App Runner(b안) 전환 가능 — D9 재논의 시 이식 비용 최소.
- **기각된 대안**: Node.js(PDF·과학 텍스트 생태계 약함) · Bun(관리형 런타임 아님).
- **결과**: `HttpClientPolicy` = httpx 재시도 정책(지수 백오프 1·2·4초, [NFR-NET-02](../requirements/nfr.md#nfr-net-02)와 1:1). 콜드스타트 완화를 위해 슬림 이미지 유지. U2의 PDF 추출 라이브러리 선택(라이선스 검토 포함)은 U2 진입 시 결정.
- **NFR 추적**: PERF-02(async) · NET-02 · SEC-03(환경 변수/SSM).

---

<a id="adr-d3"></a>
## 5. ADR-D3 — 임베딩 모델: Titan Text Embeddings V2 (리전: 서울)

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **재검토·갱신**: 2026-06-11 ([Prompt 26](../prompts.md#prompt-26), [`adr_d3_reconsideration_plan.md`](../plans/adr_d3_reconsideration_plan.md)) · **결정자**: 사용자(팀 협의) · **전제**: [ADR-D2](#adr-d2) 결과 4
- **컨텍스트**: ko↔en 교차언어 검색([US-DISC-04](../story-artifacts/user_stories.md#us-disc-04))이 핵심 품질 변수. 임베딩 모델은 리전 제약 — 서울=Titan V2, Cohere Multilingual=도쿄 전용(서울 direct InvokeModel도 `ValidationException`).
- **결정**: **`amazon.titan-embed-text-v2:0`** (1024차원) + **전 스택 서울(ap-northeast-2) 통일** — [ADR-D2](#adr-d2) 결과 4의 **(i)안**. *(2026-06-10 당초 (ii)안 Cohere+도쿄 채택 → 2026-06-11 환경 구축 라운드 실측으로 재검토·환원.)*
- **근거 (2026-06-11 재검토, [계획서](../plans/adr_d3_reconsideration_plan.md))**: AWS Tier-A 스파이크에서 **Titan V2가 실제 arXiv 코퍼스·한국어 질의 자기검색에서 Cohere와 동률**(파일럿 5/5, MRR 1.000) — "Cohere 교차언어 우위"라는 (ii) 전제가 실측에서 미검증(한국어 ML 용어는 영어 음차 다수라 도메인 교차언어 간극이 본질적으로 작음). 결정 기준은 *"Titan이 충분히 좋은가"*이고 답은 예. 반면 도쿄 고집 비용은 분명: 지연 델타 ~30ms(LLM은 `global.` CRIS라 리전 무관), 주권 비제약([A2](../story-artifacts/handoff.md#a-2)), Titan 비용 1/5. `KoEnQueryMapper`([component-model §3.2](component-model.md))가 잔여 교차언어 위험을 한 겹 더 흡수.
- **기각된 대안**: ~~Cohere+도쿄((ii)안)~~ — 교차언어 우위 실측 미검증 + 전 스택 도쿄 비용 · S3 Vectors 직접 API(청킹·동기화 자체 구현 부담).
- **결과**: S3 Vectors 인덱스 1024차원(서울) 생성. `EmbeddingPort.embed` 구현은 Titan 형태(`inputText`→`embedding`, input_type 없음) — 포트 *시그니처* 불변([U0 §8](units/unit-u0-foundation.md)). [ADR-D9](#adr-d9)·[ADR-D2](#adr-d2)·[ADR-D4](#adr-d4) 리전 표기 서울로 갱신. `KoEnQueryMapper`는 DISC-04 표시 목적 유지. ⚠️ Haiku `global.` CRIS **서울 소스** 가용성은 환경 구축 시 실호출 검증([재검토 계획 §4](../plans/adr_d3_reconsideration_plan.md)).
- **NFR 추적**: LANG-01·02 · PERF-01 · COST-01(Titan 더 저렴).

---

<a id="adr-d4"></a>
## 6. ADR-D4 — LLM: Claude Haiku 4.5 (Bedrock `global.` CRIS)

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의)
- **컨텍스트**: 예산의 지배 변수([NFR-COST-01](../requirements/nfr.md#nfr-cost-01) 월 $50). 페르소나 톤 분기 — 학부 KKL 4급 풀어쓰기([NFR-UX-01](../requirements/nfr.md#nfr-ux-01)) / 전문 어휘 보존([NFR-UX-02](../requirements/nfr.md#nfr-ux-02)). 요약 P95<20s([NFR-PERF-02](../requirements/nfr.md#nfr-perf-02)).
- **결정**: **Claude Haiku 4.5** — `global.anthropic.claude-haiku-4-5` CRIS, **서울 소스** (서울도 global CRIS 소스 리전 — [조사 §1·§15](tech-stack-aws-candidates.md); [ADR-D3](#adr-d3) 재검토로 도쿄→서울, 2026-06-11). CRIS 추가 과금 없음. ⚠️ 서울 소스 실호출은 환경 구축 시 검증(§14).
- **근거**: 한국어 격조·톤 제어 우수 + $1/$5 per 1M tok 기준 시뮬레이션 **월 ~$42 ≤ $50** ([조사 §12](tech-stack-aws-candidates.md)). `CostGuard`([component-model §2.2](component-model.md))가 상한을 하드 스톱.
- **기각된 대안**: Sonnet 4.6 단독(~$126 — 예산 초과) · Nova Lite(~$2 — 비용 폴백으로 보존, KKL 4급 톤 검증 부담) · GPT-4o-mini(비-Bedrock).
- **결과**: ① Bedrock **모델 호출 로깅** 활성화 — 토큰 수 자동 기록([NFR-OBS-02](../requirements/nfr.md#nfr-obs-02), [ADR-D10](#adr-d10) 정합). ② 혼합 라우팅(DIFF-01·02만 Sonnet 4.6, 시뮬 ~$43)은 `LlmPort` 게이트웨이 정책으로 *후속 허용* — [R2](../story-artifacts/handoff.md#r-2)·[R3](../story-artifacts/handoff.md#r-3) 대응 여지. ③ CRIS는 요청이 글로벌 상용 리전으로 라우팅될 수 있음 — 공개 논문·익명 세션([A2](../story-artifacts/handoff.md#a-2))이라 수용, ADR에 명시.
- **위험 정리**: [R3 LLM 비용 변동성](../story-artifacts/handoff.md#r-3) — CostGuard 상한 + 본 시뮬로 **1차 닫힘** (실측 정산은 U0 §6 빌드 단계).
- **검증 항목 (환경 구축 시)**: KKL 4급 톤 분기 실모델 검증. → ✅ **실측 완료 (2026-06-11)**: `global.` CRIS 실호출 — `pro` 260자(recurrence·attention·SOTA 전문어 보존, UX-02)·`student` 419자(비유 풀어쓰기+괄호 병기, UX-01) 두 톤 분기 동작, **접근 게이트 열림** ([검증 보고서 §4](../reviews/u0-aws-env-verification.md)).
- **NFR 추적**: COST-01·02 · UX-01·02 · LANG-01 · PERF-02.

---

<a id="adr-d5"></a>
## 7. ADR-D5 — 프론트엔드: Next.js (App Router) + Amplify Hosting

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의)
- **컨텍스트**: 반응형 3 브레이크포인트([NFR-MOBILE-01](../requirements/nfr.md#nfr-mobile-01)), 필터 URL 직렬화([US-DISC-02](../story-artifacts/user_stories.md#us-disc-02)·`SessionPort`), 4G 초기 로드([NFR-MOBILE-03](../requirements/nfr.md#nfr-mobile-03)).
- **결정**: **Next.js App Router + TypeScript**, 배포는 **Amplify Hosting** (SSR 지원, 무료 티어: SSR 50만 req/월·빌드 1,000분).
- **근거**: URL searchParams 직렬화 자연스러움 + RSC 스트리밍으로 모바일 체감 개선 + D7(React Flow)·D8(Serwist) 결합 성립. 데모 트래픽 무료 티어 내 ~$0.
- **기각된 대안**: SvelteKit(React Flow 불성립 → D7 연쇄 붕괴) · 정적 export+S3/CloudFront(초기 로드 손해) · Vercel(AWS 일원화 이탈).
- **결과**: Amplify 빌드 파이프라인이 배포 채널로 확정. D7·D8의 전제 성립.
- **NFR 추적**: MOBILE-01·03 · UX-03 · A11Y-01.

---

<a id="adr-d6"></a>
## 8. ADR-D6 — 컴포넌트 라이브러리: shadcn/ui + Tailwind CSS

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의)
- **컨텍스트**: WCAG 2.1 AA([NFR-A11Y-01](../requirements/nfr.md#nfr-a11y-01))·키보드 내비([A11Y-02](../requirements/nfr.md#nfr-a11y-02))·터치 타깃 44px([A11Y-03](../requirements/nfr.md#nfr-a11y-03)·[MOBILE-02](../requirements/nfr.md#nfr-mobile-02))·바텀시트 패턴([A8](../story-artifacts/handoff.md#a-8)).
- **결정**: **shadcn/ui + Tailwind CSS** (+ vaul 바텀시트).
- **근거**: Radix 프리미티브 기반 a11y + 코드 소유 방식이라 44px 터치 타깃·콘트라스트를 직접 강제 가능.
- **기각된 대안**: Mantine(별도 스타일 시스템) · Chakra(런타임 CSS-in-JS — 4G 불리) · AWS Cloudscape(관리 콘솔용 — 모바일 소비자 앱 부적합, [조사 §7](tech-stack-aws-candidates.md)) · 자체 제작(일정 과대).
- **결과**: U1 `ResultListView`·U2 바텀시트·U4 카드 재사용의 구현 어휘 확정 — [R1](../story-artifacts/handoff.md#r-1) 모바일 와이어프레임 작업의 기반.
- **NFR 추적**: A11Y-01·02·03 · MOBILE-01·02.

---

<a id="adr-d7"></a>
## 9. ADR-D7 — 그래프 시각화: React Flow

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의) · **전제**: [ADR-D5](#adr-d5) React 확정
- **컨텍스트**: [US-TRACE-01](../story-artifacts/user_stories.md#us-trace-01) 데스크톱 1-hop 그래프(≤30 노드), 노드 선택 → 논문 카드, 키보드 내비([NFR-A11Y-02](../requirements/nfr.md#nfr-a11y-02)). 모바일은 그래프 미사용([NFR-MOBILE-05](../requirements/nfr.md#nfr-mobile-05)).
- **결정**: **React Flow** (@xyflow/react).
- **근거**: 노드=React 컴포넌트라 "노드 → 논문 카드 사이드 패널" AC가 구현 직결. ≤30 노드 규모에 최적. 키보드 내비 내장.
- **기각된 대안**: Cytoscape.js(캔버스 — 노드 내 카드 UI 불가) · Sigma.js(수천 노드 WebGL — 과설계).
- **결과**: 데스크톱 전용 번들 — `FormFactorRouter`([component-model §6.2](component-model.md)) 분기에서 코드 스플리팅으로 모바일 번들 제외.
- **NFR 추적**: PERF-03 · A11Y-02·03 · MOBILE-05.

---

<a id="adr-d8"></a>
## 10. ADR-D8 — 오프라인 캐시: Service Worker(Serwist) + IndexedDB

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의)
- **컨텍스트**: [NFR-NET-04](../requirements/nfr.md#nfr-net-04) — 최근 검색·요약 24h 오프라인 읽기 전용. SW 없이는 오프라인 *재방문* 자체가 불가(앱 셸이 네트워크 의존).
- **결정**: **Service Worker(PWA, Serwist) + IndexedDB**(데이터, 타임스탬프 TTL 24h).
- **근거**: 후보 3안 중 유일하게 NET-04를 완전 충족 ([조사 §9](tech-stack-aws-candidates.md)).
- **기각된 대안**: IndexedDB 단독·localStorage 단독(오프라인 재로드 불가 — 부분 충족).
- **결과**: `CachePort` 클라이언트측 구현 확정 — **[R6 오프라인 24h 캐시](../story-artifacts/handoff.md#r-6) 위험 닫힘** ([U0 §7](units/unit-u0-foundation.md)). 오프라인 감지 시 빈 상태 행동 제안([NFR-NET-03](../requirements/nfr.md#nfr-net-03))과 결합.
- **NFR 추적**: NET-03·04 · DATA-03.

---

<a id="adr-d10"></a>
## 11. ADR-D10 — 관찰가능성: CloudWatch(EMF) + Bedrock 모델 호출 로깅 + X-Ray

- **상태**: ✅ 승인 · **결정일**: 2026-06-10 · **결정자**: 사용자(팀 협의)
- **컨텍스트**: [NFR-OBS-01](../requirements/nfr.md#nfr-obs-01) 요청별 latency·토큰·캐시 적중 / [OBS-02](../requirements/nfr.md#nfr-obs-02) 토큰·비용 누적 노출. D9 서버리스 파생으로 CloudWatch 계열이 자연 정합.
- **결정**: **CloudWatch Logs(EMF 커스텀 메트릭) + Bedrock 모델 호출 로깅 + X-Ray 트레이스**. 비용 누적치는 DynamoDB(`CostGuard`와 동일 저장소).
- **근거**: Bedrock 호출 로깅이 토큰 수를 자동 기록 — OBS-02의 절반이 설정 1회로 충족. EMF는 `Telemetry.record()` 1회 = 로그 1행 + 메트릭 동시 산출. 데모 비용 $0~2 (프리 티어 내).
- **기각된 대안**: Sentry(토큰·비용 비네이티브) · OpenTelemetry+Grafana(데모 대비 설정 과대).
- **결과**: 월 비용 대시보드 1장으로 [NFR-COST-01](../requirements/nfr.md#nfr-cost-01) 가시화. `Telemetry`([component-model §2.5](component-model.md)) 구현 = EMF + DynamoDB 1행.
- **NFR 추적**: OBS-01·02 · COST-01.

---

## 12. 확정 포트 ↔ 구현 매핑 ([component-model §2](component-model.md) 연결 — 전 항목 확정)

| 포트/정책 | 확정 구현 |
|---|---|
| `EmbeddingPort.embed` | Bedrock InvokeModel — `amazon.titan-embed-text-v2:0` (1024d, 서울) — 2026-06-11 재검토 |
| `EmbeddingPort.search` | Bedrock KB Retrieve + metadata filter (S3 Vectors 스토어) |
| `LlmPort.complete` | Bedrock Converse — `global.anthropic.claude-haiku-4-5` CRIS |
| `CostGuard` | DynamoDB 월 누적 + 호출 전 검사 (상한 $50) |
| `CachePort` (서버) | DynamoDB TTL (검색 24h / 요약 7d) |
| `CachePort` (클라이언트) | Service Worker(Serwist) + IndexedDB (24h 읽기 전용) |
| `SessionPort` | 클라이언트 쿠키/URL 직렬화 (서버 무상태) |
| `Telemetry` | CloudWatch EMF + DynamoDB 1행/호출 + Bedrock 호출 로깅 |
| `Glossary` | DynamoDB 50행 (GlossarySeed 1회 적재) |
| `CitationApi` | Lambda(httpx) → Semantic Scholar + DynamoDB 24h 캐시 + 폴백 |
| `HttpClientPolicy` | httpx 재시도 (지수 백오프 1·2·4s, 최대 3회) |

---

## 13. 비용 시뮬레이션 확정판 ([NFR-COST-01](../requirements/nfr.md#nfr-cost-01) — [U0 §6](units/unit-u0-foundation.md) 시뮬레이션 보고 충족)

확정 스택(풀 서버리스 + Haiku 4.5) 기준, [조사 §12](tech-stack-aws-candidates.md) 트래픽 가정(캐시 미스 보수 추정):

| 항목 | 월 |
|---|---|
| LLM (Haiku 4.5 — 요약·번역·DIFF·확장·캡션) | ~$42 |
| 임베딩 (Titan V2, 쿼리+코퍼스 1회 — 2026-06-11 재검토, Cohere 대비 ~1/5) | < $1 |
| S3 Vectors + DynamoDB + Lambda + Amplify + CloudWatch | $0~3 |
| **총계** | **~$45 ≤ $50 ✅** |

초과 방어: `CostGuard` 하드 스톱 + 캐시(24h/7d) 적중 시 실비용은 추정치 미만.

---

## 14. 종결 및 다음 단계

- **D1~D10 전 항목 확정** (2026-06-10) — handoff §4 Open Decisions 종결. 변경은 [handoff §6](../story-artifacts/handoff.md) 4단계.
- **위험 정리**: [R3](../story-artifacts/handoff.md#r-3) 1차 닫힘(ADR-D4) · [R6](../story-artifacts/handoff.md#r-6) 닫힘(ADR-D8) · [R4](../story-artifacts/handoff.md#r-4)는 `CitationApi` 구현 시 실증(U0) · [R1](../story-artifacts/handoff.md#r-1)·[R2](../story-artifacts/handoff.md#r-2)는 unit 진입 시.
- **다음**: [handoff §5](../story-artifacts/handoff.md) 권장 순서대로 **U0 Foundation 빌드 라운드** 진입 — 포트 시그니처는 [component-model.md](component-model.md)(확정)이 단일 진실, 구현은 본 ADR §12 매핑. U0 §6 "빌드 가능 정의" 6항목이 통과 기준.
- **환경 구축 시 검증 항목 모음**: **서울** KB×S3 Vectors 생성(ADR-D2, Titan V2 1024d) · KB 연도 범위 필터 표현력(ADR-D2) · Lambda 콜드스타트 실측(ADR-D9) · Haiku 4.5 KKL 4급 톤 검증(ADR-D4) · **Haiku `global.` CRIS 서울 소스 실호출**(ADR-D3·D4 재검토 신규). → ✅ **4건 선검증 통과 (2026-06-11, 계정 028317349537·도쿄+Cohere)** — D2·D4·D9 확인, 폴백·재논의 미발동 ([검증 보고서](../reviews/u0-aws-env-verification.md) · [절차](../plans/aws_env_verification_plan.md)). ⚠️ ADR-D3 재검토(2026-06-11)로 **서울+Titan 환원** — 도쿄 선검증은 접근법 타당성 입증, **서울+Titan 재검증이 잔여**([재검토 계획 §4](../plans/adr_d3_reconsideration_plan.md)).
