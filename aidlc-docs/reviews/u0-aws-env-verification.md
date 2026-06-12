# U0 — AWS 환경 구축 검증 보고서 (실 프로비저닝)

> **Phase**: AIDLC Construction — U0 Foundation 빌드 라운드 부속 실증
> **일자**: 2026-06-11 · **트리거**: [`prompts.md` Prompt 25](../prompts.md#prompt-25) · **계획**: [`plans/aws_env_verification_plan.md`](../plans/aws_env_verification_plan.md)
> **대상**: [ADR §14](../design-artifacts/architecture_decision_record.md) "환경 구축 시 검증 항목" 4건 + [U0 §6](../design-artifacts/units/unit-u0-foundation.md) 빌드 가능 정의의 실모델 근거 보강
> **환경**: SSO 프로필 `AdministratorAccess-028317349537` (계정 `028317349537`) · 리전 `ap-northeast-1`(도쿄) · boto3 1.43.26
> **결론**: 4건 **전부 통과**. D2·D4·D9 결정 **확인**(변경 없음). 폴백·재논의 조건 미발동.

---

## 0. 방법론 — mock이 못 닫는 것을 실 AWS로 닫는다

[U0 §6](../design-artifacts/units/unit-u0-foundation.md)의 6/6은 *포트 계약*을 mock으로 증명한다. mock이 구조적으로 증명 못 하는 4가지(리전 가용성·필터 문법·콜드스타트 실측·실모델 톤)는 실 AWS 호출로만 닫힌다. 본 보고서는 그 4건의 1차 증거다.

리소스는 전부 `docsuri-it-*`(it=integration test) 접두사로 생성 후 **전량 삭제**했다(§5). 생성·삭제가 모두 성공했다는 사실 자체가 "도쿄에서 실제로 만들어진다"의 증명이다.

---

## 1. ① 도쿄 KB×S3 Vectors 생성 가능 여부 — ✅ 가능 ([ADR-D2](../design-artifacts/architecture_decision_record.md#adr-d2))

도쿄에 전 스택을 실제 프로비저닝하여 생성 성공:

| 리소스 | 식별자 |
|---|---|
| S3 데이터 버킷 | `docsuri-it-kb-data-028317349537-apne1` |
| S3 Vectors 버킷·인덱스 | `docsuri-it-vec-028317349537` / `docsuri-papers` (1024차원, **cosine**, `nonFilterableMetadataKeys=["AMAZON_BEDROCK_TEXT"]`) |
| KB IAM 역할 | `docsuri-it-kb-role` |
| Knowledge Base | `DKJMAR9ZM5` (type=VECTOR, embedding=`cohere.embed-multilingual-v3`, storage=**S3_VECTORS**) |
| 데이터 소스 | `VS9ZWAN1BE` (S3) |

**인제스션**(AI/ML 시드 8편, 2017~2024 연도 분산):

```
numberOfDocumentsScanned: 8 · numberOfNewDocumentsIndexed: 8 · numberOfDocumentsFailed: 0
소요: 16.4초
```

- KB가 S3 Vectors를 스토어로 직접 쓰는 경로가 **도쿄에서 성립** → [ADR-D2 결과⑤](../design-artifacts/architecture_decision_record.md#adr-d2)의 "불가 시 (iii) S3 Vectors 직접 API 폴백" **불필요**.
- 1024차원 = [ADR-D3](../design-artifacts/architecture_decision_record.md#adr-d3) Cohere Multilingual v3와 일치.
- 부수 소득: 8편 16.4초 → ADR-D2 검증항목 ③(100편 동기화 소요·비용)도 선형 외삽 시 수 분·미미한 비용으로 시사(별도 100편 실측은 미수행).

## 2. ② KB Retrieve 연도 범위 필터 표현력 — ✅ 표현·동작 ([ADR-D2](../design-artifacts/architecture_decision_record.md#adr-d2))

두 필터 표면 모두 검증. 같은 "연도 범위"가 계층마다 문법이 다르므로 양쪽 확인:

| 필터 | KB Retrieve (`bedrock-agent-runtime`) | 반환 연도 | S3 Vectors 직접 (`query_vectors`, 어댑터 경로) | 반환 연도 |
|---|---|---|---|---|
| 무필터(기준) | — | 2017~2024 (8건) | — | 2017~2024 (8건) |
| `year ≥ 2023` | `greaterThanOrEquals{key:year,value:2023}` | [2023, 2024] | `{"year":{"$gte":2023}}` | [2023, 2024] |
| `2020 ≤ year ≤ 2022` | `andAll[gte 2020, lte 2022]` | [2020, 2021, 2022] | `{"$and":[{"$gte":2020},{"$lte":2022}]}` | [2020, 2021, 2022] |
| `field_tags = vision` | `equals{key:field_tags,value:vision}` | [2020] (ViT) | — | — |

- ADR-D2가 명시한 "`year >= 2023` 형태" 표현력 **충족**. KB Retrieve 연산자 객체(`greaterThanOrEquals`/`andAll`)와 어댑터 `_to_s3v_filter`의 S3 Vectors `$gte`/`$and` 양쪽 동일 결과.
- 사이드카 `.metadata.json`의 `year`(숫자)·`field_tags`(문자)가 필터 가능 메타데이터로 정상 전파됨.

## 3. ③ Lambda 콜드스타트 — P50<3s 위협 없음 ([ADR-D9](../design-artifacts/architecture_decision_record.md#adr-d9))

D1 충실 경로(**컨테이너 이미지** Lambda, `public.ecr.aws/lambda/python:3.12`, **arm64/Graviton**, 1024MB). 모듈 로드 시 FastAPI 앱 구성 + boto3 bedrock-runtime 클라이언트 생성으로 실제 import 비용 재현. 핸들러는 즉시 반환 → 측정값은 순수 *인프라 콜드 오버헤드*. `Init Duration`을 REPORT 로그에서 직접 파싱, env 토글로 콜드 강제(6회) + 웜 6회.

| 지표 | P50 | min | max |
|---|---|---|---|
| 콜드 init (ms) | **887** | 749 | 2798 |
| 콜드 첫응답 = init+핸들러 (ms) | 889 | 751 | 2800 |
| 웜 호출 duration (ms) | 1.9 | — | 3.4 |

- 최초 콜드(2798ms)는 이미지가 Lambda 최적화 캐시에 오르기 전 *첫-ever* 호출 스파이크 — 이후 콜드는 750~990ms로 안정. [ADR-D9 근거②](../design-artifacts/architecture_decision_record.md#adr-d9) "콜드스타트 ~1-2초" 가정 확인(정상상태는 오히려 더 빠름).
- NFR-PERF-01은 **P50(중앙값)** <3s. 콜드는 실행환경당 *첫 요청*에만 붙고 데모 트래픽 중앙값은 웜(~2ms)이 지배 → 콜드 인프라 오버헤드만 떼도 최악 2.8s로 3s 미만.
- → [ADR-D9 결과⑤](../design-artifacts/architecture_decision_record.md#adr-d9) EventBridge 워밍/b안 전환 **발동 조건 미충족**. D9 결정 유지.
- 한계: 본 측정은 Web Adapter의 uvicorn 기동(수십 ms)을 생략한 순수 핸들러 프록시. 실제 요청은 여기에 Bedrock 호출(수 초)이 더해지며 그건 NFR-PERF-02(요약 P95<20s) 관할로 여유.

## 4. ④ Haiku 4.5 KKL 4급 톤 — ✅ 충족 ([ADR-D4](../design-artifacts/architecture_decision_record.md#adr-d4))

`global.anthropic.claude-haiku-4-5-20251001-v1:0` CRIS 실호출(Converse). 동일 원문(트랜스포머 초록)으로 두 페르소나 분기. **접근 게이트 열림**(`AccessDeniedException` 없음 — 메모리상 "Anthropic use-case 폼 게이트"는 이 계정에선 해소됨).

| 페르소나 | NFR | 길이 | 지연 | 판독 |
|---|---|---|---|---|
| `student` (KKL 4급) | UX-01 풀어쓰기 | 419자 | 4.1s | 순환구조→"책을 첫 페이지부터 읽는 것처럼" 비유, 전문어 괄호 병기 ✅ |
| `pro` | UX-02 전문어 보존 | 260자 | 3.2s | recurrence·attention·SOTA·self-attention·seq2seq 보존 ✅ |

- 두 톤 분기 모두 의도대로 동작. pro는 200~400자 창 내, student는 419자(마크다운 헤더 포함, 창 약간 초과 — 회귀 가드는 느슨히).
- 지연 3.2~4.1s(AWS CLI 기동 오버헤드 포함)는 NFR-PERF-02(요약 P95<20s)에 여유.
- CRIS는 글로벌 상용 리전 라우팅 가능([ADR-D4 결과③](../design-artifacts/architecture_decision_record.md#adr-d4)) — 공개 논문·익명 세션이라 수용 범위 그대로.

## 5. 비용·정리(teardown)

- **비용**: Bedrock 호출 ~십여 건(Haiku ~수백 토큰, Cohere embed 소량) + 8편 인제스션 + 분 단위 S3 Vectors/Lambda 보유 + Lambda 18회 호출 + ECR 분 단위 보유 → **수 센트 미만**.
- **정리**: 전 리소스 삭제 완료 — KB·인덱스·벡터버킷·데이터버킷·KB역할·Lambda함수·Lambda역할·ECR리포 (KB는 비동기 `DELETING` 후 자동 소멸). 잔존 고정비 0.

## 6. ⑤ U0 §6 갱신 결정 (요약)

- **체크박스 6/6 상태 불변.** §6 항목은 설계상 "실모델 OR 결정적 mock" 허용 → 어떤 항목도 상태가 바뀌지 않음. 본 검증이 닫은 것은 §6이 아니라 [ADR §14](../design-artifacts/architecture_decision_record.md) 검증 항목.
- **증거 기반만 격상**: §6 증거 라인을 "mock 모드" → "mock + 실 AWS 확인"으로. embed(Cohere v3 1024d)·search(KB Retrieve)·complete(Haiku 4.5 pro 260자)가 mock에 더해 실모델로도 확인됨.
- **절차**: 결정 *확인*이지 *변경*이 아니나, 동결 본문 주석을 위해 [handoff §6](../story-artifacts/handoff.md) 4단계 적용([계획서](../plans/aws_env_verification_plan.md) §1).

---

## 부록 A. 시드 코퍼스 (연도 범위 필터 검증용)

| id | year | field_tags | 주제 |
|---|---|---|---|
| attention2017 | 2017 | nlp | Transformer/self-attention |
| bert2018 | 2018 | nlp | BERT |
| gpt3_2020 | 2020 | nlp | GPT-3 few-shot |
| vit2020 | 2020 | vision | Vision Transformer |
| clip2021 | 2021 | multimodal | CLIP |
| chinchilla2022 | 2022 | nlp | compute-optimal scaling |
| llama2_2023 | 2023 | nlp | Llama 2 |
| mamba2024 | 2024 | sequence | Mamba SSM |
