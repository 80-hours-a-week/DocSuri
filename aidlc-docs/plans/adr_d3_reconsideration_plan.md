# ADR-D3 재검토 — 임베딩 리전/모델 변경 계획 (서울 + Titan 재상정)

> **Phase**: AIDLC Construction — 환경 구축 라운드 / 동결 후 변경 ([`handoff.md §6`](../story-artifacts/handoff.md) 4단계 중 **2단계: 변경 계획서**)
> **상태**: 🟡 **제안 (DRAFT)** — 사용자·팀 승인 전. 본 문서는 *결정을 강제하지 않으며*, 승인 시 [`architecture_decision_record.md`](../design-artifacts/architecture_decision_record.md) ADR-D3·D2·D4·D9를 수정한다.
> **트리거**: 사용자 질문 (2026-06-11) — "임베딩 모델 때문에 도쿄를 쓰는 것보다, Titan을 쓰더라도 한국 리전(서울)을 쓰는 게 낫지 않은가?"
> **입력 근거**: AWS Tier-A 통합 스파이크 실측 (2026-06-11) · [`tech-stack-aws-candidates.md §3·§4`](../design-artifacts/tech-stack-aws-candidates.md) · 기존 [ADR-D2 결과 4](../design-artifacts/architecture_decision_record.md#adr-d2)·[ADR-D3](../design-artifacts/architecture_decision_record.md#adr-d3) · [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01)·[LANG-01](../requirements/nfr.md#nfr-lang-01)·[SEC-01](../requirements/nfr.md#nfr-sec-01)
> **입력 범위 제약** (사용자 지시 2026-06-10): `aidlc-docs/` 밖 문서는 근거로 쓰지 않는다. 단 본 라운드는 *환경 구축*이므로 **실 AWS 실측치**를 1차 근거로 인용한다(재현 절차 §4 명시).

---

## 1. 재검토 대상 결정과 *원래 전제*

| 항목 | 현행 ADR | 채택 당시 핵심 전제 |
|---|---|---|
| [ADR-D3](../design-artifacts/architecture_decision_record.md#adr-d3) 임베딩 모델 | **Cohere Embed Multilingual v3** | ko↔en 교차언어 품질이 [US-DISC-04](../story-artifacts/user_stories.md#us-disc-04)의 핵심 품질 변수이고, **Cohere가 Titan보다 교차언어 우수**하다 |
| [ADR-D3](../design-artifacts/architecture_decision_record.md#adr-d3)·[D9](../design-artifacts/architecture_decision_record.md#adr-d9) 리전 | **도쿄 (ap-northeast-1) 전 스택 통일** | KB 임베딩 모델 리전 제약(서울=Titan V2만, Cohere=도쿄)에서 *교차언어 우위를 지키려고* 도쿄 이동 — [ADR-D2 결과 4](../design-artifacts/architecture_decision_record.md#adr-d2)의 (ii)안 |

즉 **전 스택을 도쿄로 옮긴 유일한 동인은 "Cohere의 교차언어 품질이 리전 이동 비용보다 크다"는 가정**이었다. 본 재검토는 그 가정을 환경 구축 단계에서 실측으로 검증한 결과를 근거로, [ADR-D2 결과 4](../design-artifacts/architecture_decision_record.md#adr-d2)의 **(i)안 — 서울 + Titan V2** 재상정을 제안한다.

---

## 2. 실측 근거 (2026-06-11, AWS Tier-A 스파이크)

> 계정 028317349537 · IAM Identity Center 프로필 `AdministratorAccess-028317349537` · 하네스 `backend/tests/test_aws_integration.py`. 비교 스크립트는 일회성(§4에 승격 제안).

### 2.1 도쿄를 정당화하던 비-품질 축 — 전부 무력 또는 서울 우위

| 축 | 측정/사실 | 판정 |
|---|---|---|
| **지연** ([NFR-PERF-01](../requirements/nfr.md#nfr-perf-01)) | Bedrock 왕복 실측 ~1.6s(embed 163ms + llm 1.4s). 서울↔도쿄 리전 델타는 한국 사용자 ~30ms(~2%). **LLM은 `global.` CRIS라 소스 리전 무관 글로벌 라우팅** → 두 리전 동일 | 서울 우위(미미) |
| **데이터 주권** ([NFR-SEC-01](../requirements/nfr.md#nfr-sec-01)) | [A2](../story-artifacts/handoff.md#a-2): 공개 arXiv·익명 세션 → 제약 아님. 게다가 Haiku가 이미 global CRIS로 한국어를 글로벌로 전송 → **서울이어도 LLM 경로 주권은 못 지킴** | 중립 |
| **비용** ([NFR-COST-01](../requirements/nfr.md#nfr-cost-01)) | Titan V2 ~$0.02 vs Cohere ~$0.10 /1M tok. 코퍼스 100편 기준 둘 다 월 <$1 | 무시(서울 약우위) |
| **모델 가용성** | **Cohere는 서울 불가 확정** — KB뿐 아니라 direct `InvokeModel`도 `ValidationException`. Titan V2는 서울 direct invoke 정상 | 이진 선택 강제 |

→ "Cohere+서울" 탈출구는 없다. 선택지는 **도쿄+Cohere vs 서울+Titan 이진**이며, 품질 축을 제외한 모든 축이 서울로 기울거나 중립이다.

### 2.2 품질 축 — Cohere의 교차언어 우위가 실측에서 사라짐

핵심 질문은 *"Cohere보다 나은가"*가 아니라 ***"Titan이 충분히 좋은가"***이다.

| 실험 | 코퍼스 / 질의 | 결과 |
|---|---|---|
| n=4 합성 프로브 | 합성 영어 초록 7편 / 코드스위칭 한국어 질의 4 | Titan **4/4** vs Cohere **3/4** (Cohere가 순한국어 "연산량 감축"을 놓침). *단 합성·라벨 잡음* |
| 5편 자기검색 파일럿 (키워드형) | **실제 arXiv 제목 100편** / Haiku 생성 한국어 키워드 질의 | **양쪽 5/5, MRR 1.000** |
| 5편 자기검색 파일럿 (순한국어 개념형) | 동일 코퍼스 / 영어 용어 배제한 개념 질의 | **양쪽 5/5, MRR 1.000** |

- 실제 코퍼스 + 자연스러운 한국어 질의에서 **Titan이 Cohere와 동일하게 완벽**. 앞 n=4의 Cohere 열세는 합성·라벨 아티팩트로 해석된다.
- **도메인 특성**: 한국어 ML/AI 용어는 영어 음차가 다수(멀티모달=multimodal, 미세조정=fine-tuning, 에이전트=agent)라, *이 도메인*의 교차언어 간극은 본질적으로 작다 — Titan의 "영어 최적화"가 거의 페널티가 아니다.
- **완화 장치 유지**: [`KoEnQueryMapper`](../design-artifacts/component-model.md) (한→영 매핑 후 검색)가 한 겹 더 덮으므로, 잔여 교차언어 위험은 추가로 흡수된다.

### 2.3 정직한 한계 (과대해석 금지)

- rank-1은 *쉬운* 지표 — 코퍼스 100편이 토픽으로 흩어져 변별 압력이 낮다. **미세한 품질차는 본 실험이 탐지 못 한다.**
- 표본(질의 5)·코퍼스(100편 제목, *초록 텍스트 없음* — 시드가 `abstract_len`만 보유)가 작다. 더 조밀한 질의/코퍼스에서 재현 필요(§4 선택 항목).
- 결론은 *"Titan은 충분히 좋다"*까지이며, *"Cohere보다 절대 안 나쁘다"*는 아니다. 후자가 필요하면 §4-(b) 일관성 테스트.

---

## 3. 제안 결정과 연쇄 (승인 시 동기 갱신 대상)

### 3.1 제안

> **ADR-D2 결과 4의 (i)안 재채택** — 임베딩 모델 `amazon.titan-embed-text-v2:0`(1024차원), **전 스택 서울(ap-northeast-2) 통일.** Cohere를 버리면 도쿄를 붙들 이유가 사라지고, 홈 리전 단일화·운영 단순·비용 절감을 얻는다.

### 3.2 연쇄 영향 (포트 *시그니처* 불변 — [U0 §8](../design-artifacts/units/unit-u0-foundation.md) "단독 변경 가능" 범위)

| 산출물/코드 | 변경 내용 |
|---|---|
| [ADR-D3](../design-artifacts/architecture_decision_record.md#adr-d3) | 모델 Cohere→**Titan V2**, 리전 도쿄→**서울**. 차원 1024 유지(Titan V2 설정값). 근거를 본 실측으로 교체 |
| [ADR-D2](../design-artifacts/architecture_decision_record.md#adr-d2) | 리전 서울. S3 Vectors **서울 GA** 확인됨([조사 §15](../design-artifacts/tech-stack-aws-candidates.md)). 인덱스 1024차원 재생성. "서울 KB=Titan만" 제약이 이제 *순응*(Titan 채택)으로 전환 |
| [ADR-D9](../design-artifacts/architecture_decision_record.md#adr-d9) | 전 스택 리전 도쿄→**서울** (Amplify·Lambda·DynamoDB·Bedrock). "한국 사용자 +30ms" 문구 삭제 |
| [ADR-D4](../design-artifacts/architecture_decision_record.md#adr-d4) | Haiku `global.` CRIS **소스 리전 서울**로. 추가 과금 없음 유지. ⚠️ 서울 소스 가용성 실호출 검증 필요(§4) |
| `backend/src/docsuri/u0/config.py` | `aws_region` 기본값 `ap-northeast-2`, `bedrock_embed_model_id` = `amazon.titan-embed-text-v2:0` |
| `backend/src/docsuri/u0/adapters/aws.py` `BedrockEmbedding.embed` | 요청/응답을 Titan 형태로 — `{"inputText": text}` → `{"embedding": [...]}`. Cohere의 `input_type`·batch·`{"float":[[...]]}` 분기 제거. `search`(S3 Vectors 직접 조회)는 불변 |
| `KoEnQueryMapper` | 변경 없음 — 안전망 역할 유지 |
| 비용 시뮬 [ADR §13](../design-artifacts/architecture_decision_record.md) | 임베딩 비용 추가 하락(무시 수준), 총계 ~$45 이하 유지 |

> **현행 구현 보강 메모**: 실제 `search`는 KB Retrieve가 아니라 **S3 Vectors `query_vectors` 직접 조회**([ADR-D2 결과 3](../design-artifacts/architecture_decision_record.md#adr-d2))이므로, "KB 임베딩 모델 리전 제약"은 이미 부분적으로 우회돼 있다. 그러나 *모델 자체의 리전 가용성*(Cohere=도쿄 전용)은 여전히 바인딩이라, 서울로 가려면 Titan이 강제된다 — 본 제안과 정합.

---

## 4. 승인 전/후 검증 항목 (Definition of Done)

- [ ] **(필수) Haiku `global.` CRIS 서울 소스 실호출** — 서울에서 Converse 1회 성공 확인 (현재 도쿄 소스만 실측됨).
- [ ] **(필수) 서울 S3 Vectors 인덱스 생성·쿼리** — 1024차원, 메타데이터 필터(`$gte`/`$in`) 표현력. 기존 [ADR §14 검증 항목](../design-artifacts/architecture_decision_record.md) 서울 버전.
- [ ] **(선택, 엄밀화) 교차언어 일관성 테스트 N=20** — 같은 질의의 한국어 vs 영어 top-5 이웃 겹침을 모델별 비교. rank-1이 마스킹하는 미세차 탐지용. *"Cohere보다 안 나쁘다"*를 원할 때만.
- [ ] **(선택) Titan V2 차원 선택** — 256/512/1024 중. 인덱스 크기·비용 vs 품질 트레이드오프. 기본 1024 권장(현 인덱스와 정합).
- [ ] 어댑터 변경 후 Tier-A 통합 테스트 재통과(`test_embed_*` 서울/Titan 기준).

> **롤백 안전망**: 미세 품질차가 후에 드러나도 `EmbeddingPort` 추상화 뒤에서 모델·리전 재교체 가능 — 포트 *시그니처*는 불변이라 도메인 unit(U1·U3) 영향 0.

---

## 5. handoff §6 4단계 진행 상태

1. [x] **prompts.md 트리거 등재** — [Prompt 26](../prompts.md#prompt-26) (2026-06-11)로 추가 완료.
2. [x] **변경 계획서** — *본 문서* (DRAFT).
3. [x] **사용자·팀 승인** (2026-06-11) → §3.2 산출물·코드 수정 완료: ADR-D2/D3/D4/D9 + §12 매핑·§13 비용·§14 검증항목 + `config.py`·`aws.py`(embed Titan화)·`.env.example`·통합 테스트 도크스트링.
4. [x] **handoff 동기 갱신** — N/A: [`handoff.md`](../story-artifacts/handoff.md) §4 D3는 *미해결 결정 후보 목록*(OpenAI/Voyage/BGE-M3)일 뿐 리전/모델 표기가 없어 갱신 대상 없음. 해소된 결정의 단일 진실은 ADR.

---

## 6. prompts.md 등재용 트리거 프롬프트 (복사용)

```
[2026-06-11] ADR-D3 재검토 요청 (동결 후 변경 §6-1):
"임베딩 모델 때문에 도쿄 리전을 이용하는 것보다 Titan을 쓰더라도 한국 리전을
쓰는 게 더 낫지 않을까?" → 환경 구축 라운드 AWS Tier-A 스파이크 실측으로 ADR-D3
전제(Cohere 교차언어 우위)를 검증. 결과: 실제 코퍼스에서 Titan=Cohere 동일 성능,
지연·주권·비용 축은 서울 우위/중립, Cohere 서울 불가 확정. → 서울+Titan 재상정 제안.
변경 계획서: aidlc-docs/plans/adr_d3_reconsideration_plan.md
```

---

## 7. 범위 밖 (Out of Scope)

- ADR 본문 *수정* — 승인(§5-3) 전에는 건드리지 않는다. 본 문서는 제안만.
- D2 벡터 스토어(S3 Vectors) 자체 교체 — 리전만 이동, 기술 선택은 불변.
- Tier-B 인프라 프로비저닝(테이블·인덱스·시드) — 별도 환경 구축 작업.
- 임베딩 *차원 축소를 통한 비용 최적화* 등 후속 튜닝 — 출시 후.
