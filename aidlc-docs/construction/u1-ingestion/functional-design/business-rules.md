# business-rules.md — U1 Ingestion 비즈니스 규칙·속성·추적성

**단계**: CONSTRUCTION → Functional Design · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: 계획서 답변(Q1~Q17=A, **Q13=B**) · `requirements.md` · `inception/application-design/`
**원칙**: 기술 무관 결정·검증·제약 규칙. 수치(백오프·동시성·타임아웃)는 정책 형태만, 확정은 NFR/Infra(AS-4).

---

## 1. 비즈니스 규칙 (BR)

| ID | 규칙 | 근거/답 |
|---|---|---|
| **BR-1 (OA 배제)** | 모든 arXiv 논문을 OA로 취급(라이선스 미검사); 본문/메타 취득 실패 항목만 제외. Q2=A에서 비-OA 배제는 사실상 0. | C-1, A-5, **Q5=A** |
| **BR-2 (콘텐츠 범위)** | 데모는 **초록+메타데이터만** 임베딩(전문 본문 청킹 제외). 전문 경로는 계약만 보존. | FR-6, **Q2=A** |
| **BR-3 (논문 식별·버전)** | `PaperId = 버전 없는 arXiv ID`. 최신 vN만 인덱스에 존재(latest-wins upsert). 신규 게재=NEW, vN 증가=CHANGED, 동일 vN=DUPLICATE. | **Q3=A** |
| **BR-4 (디덥 지문)** | `ContentFingerprint = PaperId + PaperVersion` 파생(콘텐츠 해시 아님). 동일 지문 재수신 → DUPLICATE(단락, 재임베딩 0). | NFR-C1, PBT-08, **Q6=A** |
| **BR-5 (청킹 결정성)** | `chunk`·`chunkId`는 결정적·멱등(동일 ParsedPaper→동일 ChunkSet/ChunkId). 빈/비정상 초록 안전 처리. Q2=A: 초록 1청크(ordinal=0). | FR-6, QT-4, PBT-08 |
| **BR-6 (IndexRecord 구성)** | 레코드 = 카드 필드(FR-4) + category + version + 전체 abstract + lexicalTerms(제목+초록 토큰). 해소 가능 arXiv ID/링크 필수(FR-5 근거화 전제). | FR-2/4/5, **Q4=A** |
| **BR-7 (논문 단위 원자성)** | 한 논문의 전 청크 임베딩·기록 성공 시에만 커밋(`markIngested`). 일부 실패 = 미커밋·재시도. **부분/조용한 인덱싱 금지.** | NFR-R1, **Q8=A** |
| **BR-8 (커밋 순서 INV-1)** | 단계 순서 = **index write durable → markIngested → advanceWatermark**. upsert 후 markIngested 전 크래시 → 다음 실행 재분류·**멱등 재upsert**로 정합. | NFR-R1, INV-1 |
| **BR-9 (멱등 upsert)** | upsert는 ChunkId 키 멱등(재실행·재전송이 중복 레코드 생성 안 함). 재처리(CHANGED)는 덮어쓰기. | QT-4, PBT-08, Q3=A |
| **BR-10 (워터마크·RPO)** | 워터마크 기준 시각 = arXiv **updated**(vN 개정 포착). RPO = 마지막 인제스천 시점(RES-2, 별도 백업 없음). | RES-2, **Q7=A** |
| **BR-11 (워터마크 역행)** | `advanceWatermark` **max-clamp**: 전진만, 역행 시도 무시. **예외**: `SEED_REBUILD`만 의도적 리셋 허용(BR-13 상호배제로 보호). | RES-2, **Q17=A** |
| **BR-12 (이벤트 멱등·포이즌)** | 이벤트 at-least-once 소비. **멱등 = DeduplicationGuard DUPLICATE 단일 백스톱**(이벤트-레벨 dedup 없음). 처리 후 `ackEvent`. 포이즌 이벤트 → DLQ. (Q12=A 스텁이어도 계약.) | RES-7, **Q15=A** |
| **BR-13 (재구축↔증분 상호배제)** | 단일 writer 인덱스 보호: `SEED_REBUILD` 활성 중 `INCREMENTAL` 보류/거부(REBUILD_LOCK). 증분이 미재구축 레코드를 지나 워터마크 전진 → RPO 손상 경로 차단. | NFR-R1, RES-2, **Q16=A** |
| **BR-14 (철회·tombstone)** | **Q13=B 활성**: 갱신 중 철회/대체 탐지(arXiv 메타 철회 표시/초록 withdrawal 공지) → `tombstone(paperId)`; tombstone 경로도 INV-1 순서(`markIngested(paperId+vN)`·`advanceWatermark`) 준수. **순서는 `DeduplicationGuard.isNew`로 강제**(별도 메커니즘 아님): 더 새로운 vN=CHANGED→재upsert(부활), 동일/이전 vN=DUPLICATE→무시(stale upsert가 신규 버전·철회를 덮지 않음). 재구축 시에도 동일 탐지 능동 실행. | **Q13=B** |
| **BR-15 (실패 분류)** | RETRIABLE = 네트워크/타임아웃/5xx/429; PERMANENT = 파싱 실패·검증 위반·비-OA·404. | RES-9, **Q9=A** |
| **BR-16 (재시도·쿼터)** | 지수 백오프+지터, arXiv 보수적 쿼터 준수(낮은 동시성·요청 간 최소 지연), 소진 시 DLQ. **수치는 NFR/Infra(AS-4).** | RES-8/9, **Q10=A** |
| **BR-17 (DLQ·경보)** | 소진/영구 항목 DLQ 격리 + 구조화 실패 신호 U6.ObservabilityHub 발행. 잡은 계속 진행(한 논문 실패가 전체를 막지 않음). 잡 실패율 임계 초과 → 갱신 실패 경보. | RES-7, NFR-O1, NFR-R1, **Q11=A** |
| **BR-18 (fail-closed)** | 모든 외부 호출(arXiv/임베딩 게이트웨이/벡터 스토어) 타임아웃·서킷; 실패 시 fail closed(부분/조용한 진행 금지). | SEC-15, RES-9, NFR-R1 |
| **BR-19 (입력 검증)** | 파싱 산출 필수 필드·형식 검증·새니타이즈(질의 아닌 인제스천 데이터). | SEC-5 |
| **BR-20 (공개 스토리지 차단)** | OA 전문 보관 시 오브젝트 스토리지 공개 차단(SEC-9). **Q2=A에서 전문 보관 부재 → SEC-9 정당화된 N/A**(§4 경계표). | SEC-9 |
| **BR-21 (본문 크기 정책)** | 과대/빈/손상 본문 처리(절단 결정적 vs PERMANENT 거부 vs 청크 상한). **Q2=A(초록 전용)에서 사실상 N/A** — 전문 승급(Q2=C) 시 활성화. | FR-6, NFR-C1 |

---

## 2. RejectedRecord 사유 분류

| RejectReason | 의미 | FailureClass |
|---|---|---|
| `NON_OA` | 비-OA(Q5=A에서 사실상 0) | PERMANENT |
| `PARSE_FAILURE` | 메타데이터 파싱 불가 | PERMANENT |
| `VALIDATION_VIOLATION` | 필수 필드/형식 위반(SEC-5) | PERMANENT |
| `FETCH_FAILURE` | 원천 취득 실패(타임아웃/네트워크) | RETRIABLE→소진 시 DLQ |

> 거부**율**(특히 PARSE/VALIDATION 급증)은 BR-17 잡 실패율 경보의 보조 신호(RES-7).

---

## 3. PBT 속성 (QT-4 / PBT-08 blocking) — 테스트 가능 속성 명문화

| 속성 | 진술 | 트레이스 |
|---|---|---|
| **P1 디덥 멱등성** | `isNew` 결정은 입력에만 의존·결정적; **동일 이벤트/논문 재전송이 추가 인덱싱·중복 생성 안 함**(Q15=A 재전송 포함). | PBT-08, BR-4/9/12 |
| **P2 청크 결정성** | 동일 ParsedPaper → 동일 ChunkSet·동일 ChunkId(순서·내용 안정). | PBT-08, BR-5 |
| **P3 upsert 멱등성** | 동일 IndexRecord 집합 재upsert가 인덱스 상태 불변(중복 레코드 0); CHANGED는 덮어쓰기. | PBT-08, BR-8/9 |
| **P4 무손실·무중복** | 주어진 ParsedPaper에 대해 `|upserted IndexRecords| == |ChunkSet|`(청크 조용한 누락/중복 0). | NFR-R1, BR-7 |
| **P5 임베딩 정렬 보존** | `EmbeddingBatch.vectors[i] ↔ chunks[i].chunkId`(embedBatch→upsert 사이 재정렬/누락 0). | NFR-R1, BR-7 |
| **P6 워터마크 단조성** | `advanceWatermark`는 **BR-11 max-clamp 규칙에 따라** 전진만(역행 무시); SEED_REBUILD 리셋만 예외. | RES-2, BR-11 |

> PBT 프레임워크·언어·도메인 제너레이터·shrinking·시드 재현성은 **NFR Requirements**에서 확정. P1/P3/P4/P5는 PBT-08(디덥 멱등·결과셋 보존) 차단성, P2는 청크 결정성, P6은 RES-2 정합.

---

## 4. 데모 범위 vs 프로덕션 타깃 경계

| 축 | 데모(답) | 프로덕션 타깃 | 후속 단계 |
|---|---|---|---|
| 코퍼스 슬라이스(FR-6) | cs.LG, 최근 ~1년(수천)(Q1=A) | 5개 카테고리·5년·수십만 | Infra Design |
| 본문 깊이(Q2) | 초록+메타만(A) | OA 전문 청킹(C) | NFR/Infra |
| 트리거 표면(Q12) | 수동 rebuild + 스케줄 증분(A); 이벤트 스텁 | + new-arXiv 이벤트 경로 | Infra(이벤트 버스) |
| 철회/tombstone(Q13) | **탐지·tombstone 활성(B)** | 동일 + 대체 정합 강화 | — |
| 평가셋 코퍼스(Q14) | QT-1/QT-2 대상 논문 포함 보장(A) | 동일 | U2/U6 FD가 평가셋 구축 |
| OA 전문 보관/SEC-9 | **부재 → SEC-9 정당화된 N/A**; 재구축은 arXiv 재취득(Q2=A 귀결) | 보관 + SEC-9 적용 + 재구축 재사용 | Infra |
| 재시도 수치(Q10) | 정책 형태만 | 확정 수치 | NFR/Infra(AS-4) |
| 임베딩 모델/차원(VectorSpec) | 미확정(계약만) | 확정 | NFR Requirements |

---

## 5. 추적성 매트릭스 (요구사항 → 규칙/속성/엔티티)

| 요구사항 | 랜딩 |
|---|---|
| **FR-6**(인제스천·인덱싱·갱신) | BR-2/5/6, IngestionPipelineService, RefreshOrchestrationService |
| **C-1**(OA 전용) | BR-1(OA 배제), RejectReason(NON_OA) |
| **C-6**(AI/ML 전용) | CategoryFilter / resolveSliceCategories(cs.LG 슬라이스, Q1=A) |
| **RES-2**(재구축 자산·RPO·런북) | BR-10/11/13, IndexStats(§bus-logic 5), AS-5 |
| **RES-7**(갱신 실패 경보) | BR-17, RejectReason 거부율 |
| **RES-8**(쿼터 인지) | BR-16, ArxivSourceClient |
| **RES-9**(타임아웃·서킷·저하) | BR-15/16/18, IngestionResilienceService |
| **NFR-C1**(비용·디덥) | BR-4(DUPLICATE 단락), EmbeddingGatewayAdapter 텔레메트리 |
| **NFR-R1**(부분/조용한 인덱싱 금지) | BR-7/8/13/17/18, P4/P5 |
| **NFR-O1**(관측성) | BR-17, IndexStats |
| **SEC-5 / SEC-9 / SEC-15** | BR-19 / BR-20 / BR-18 |
| **QT-4 / PBT-08** | P1~P6 |
| **US-I1**(시드 빌드) | triggerFullRebuild, BR-13 |
| **US-I2**(스케줄 갱신) | onScheduleTick, BR-10/17 |
| **US-I3**(복원력) | BR-15/16/17/18, IngestionResilienceService |
| **Q13=B**(철회) | BR-14, Tombstone, WithdrawalMarker |
| **미커버 검증** | 위 표로 U1 트레이스 0 미커버 — backing US-H1/US-D2는 공유 인덱스 존재로 충족 |

---

## 6. 공유 계약 정합 주석 (VectorSpec)

- U1.EmbeddingGatewayAdapter(writer)와 U2.QueryUnderstandingExpander(reader)는 **동일 `VectorSpec`(차원·모델·거리 메트릭)** 을 소비해야 인덱스 검색 정합(동일 임베딩 공간 불변식).
- 본 Functional Design은 **불변식·계약만** 규정. 구체 모델/차원/메트릭 값은 **NFR Requirements**에서 확정하며, 확정 후 U1 writer와 U2 reader가 동시에 동일 값을 채택해야 한다(스키마 드리프트 = 인덱스 비정합).
- 단일 writer(U1)/단일 reader(U2) 경계 — U1은 쓰기 측 진실 원천.
