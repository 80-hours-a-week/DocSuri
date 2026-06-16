# business-rules.md — U1 Ingestion 비즈니스 규칙·속성·추적성 (프로덕션)

**단계**: CONSTRUCTION → Functional Design · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: 계획서(프로덕션 재스코핑) — Q1=D·Q2=C·Q12=B·Q13=B·그 외 A · `requirements.md`.
**원칙**: 기술 무관 결정·검증·제약. 수치(백오프·동시성·타임아웃)는 정책+NFR Requirements 확정값(Q14).
**프로덕션 스코프**: 전문 청킹·다중 청크·이벤트 경로·철회 tombstone·전문 오브젝트 보관 활성.

---

## 1. 비즈니스 규칙 (BR)

| ID | 규칙 | 근거/답 |
|---|---|---|
| **BR-1 (엄격 OA 라이선스 검증)** | **팀 결정(2026-06-16): 엄격 OA 라이선스 검증.** 각 논문의 arXiv 라이선스를 검사해 **재배포 가능 라이선스만**(예 CC-BY/CC-BY-SA/CC0) 수집·전문 보관·인덱싱; **재배포 불가·미표기·불명(예 arXiv 비독점 라이선스) → NON_OA 배제**. 취득 실패도 제외. (Q5 A→엄격 검증 확정; A-5 가정 강화; 커버리지보다 정합 우선.) | C-1, A-5, **Q5=엄격** |
| **BR-2 (콘텐츠 범위)** | **OA 전문(full-text) + 메타데이터** 수집·청킹(Q2=C). 전문 원천은 오브젝트 스토리지 보관(BR-20). | FR-6, **Q2=C** |
| **BR-3 (논문 식별·버전)** | `PaperId=버전 없는 arXiv ID`. 최신 vN만 인덱스(latest-wins). NEW/CHANGED/DUPLICATE 의미(Q3=A). | Q3=A |
| **BR-4 (디덥 지문)** | `ContentFingerprint=PaperId+PaperVersion` 파생(콘텐츠 해시 아님). 동일 지문 재수신→DUPLICATE 단락(재임베딩 0). | NFR-C1, PBT-08, Q6=A |
| **BR-5 (청킹 결정성·전략)** | **섹션 인지 다중 청크**(초록·본문 섹션, 결정적 오버랩); `chunk`·`chunkId` 결정적·멱등(동일 입력→동일 ChunkSet/ChunkId). 빈/비정상 본문 안전(BR-21). | FR-6, QT-4, PBT-08, **Q2=C** |
| **BR-6 (IndexRecord 구성)** | 청크당 레코드 = 카드 필드(FR-4) + category + version + section + abstract + lexicalTerms(제목+초록+본문 토큰). 해소 가능 arXiv ID/링크 필수(FR-5). | FR-2/4/5, Q4=A |
| **BR-7 (논문 단위 원자성)** | 한 논문의 **전 청크**(다중) 임베딩·기록 성공 시에만 커밋(markIngested). 일부 실패=미커밋·재시도. **부분/조용한 인덱싱 금지.** | NFR-R1, **Q8=A** |
| **BR-8 (커밋 순서 INV-1)** | **index write durable → markIngested → advanceWatermark**. upsert 후 markIngested 전 크래시→재분류·멱등 재upsert. | NFR-R1, INV-1 |
| **BR-9 (멱등 upsert)** | upsert는 ChunkId 키 멱등(재실행·재전송이 중복 레코드 0). CHANGED는 덮어쓰기. | QT-4, PBT-08, Q3=A |
| **BR-10 (워터마크·RPO)** | 기준 시각=arXiv updated. RPO=마지막 인제스천(RES-2, 별도 백업 없음). | RES-2, Q7=A |
| **BR-11 (워터마크 역행)** | max-clamp(전진만, 역행 무시). 예외: SEED_REBUILD만 의도적 리셋(BR-13 보호). | RES-2, Q17=A |
| **BR-12 (이벤트 멱등·포이즌)** | 이벤트 at-least-once 소비(**Q12=B 활성**). 멱등=DeduplicationGuard DUPLICATE 단일 백스톱(이벤트-레벨 dedup 없음). 처리 후 ackEvent. 포이즌→DLQ. | RES-7, **Q15=A, Q12=B** |
| **BR-13 (재구축↔증분/이벤트 상호배제)** | 단일 writer 보호: SEED_REBUILD 활성 중 INCREMENTAL·EVENT 보류/거부(REBUILD_LOCK). | NFR-R1, RES-2, **Q16=A** |
| **BR-14 (철회·tombstone)** | **Q13=B 활성**: 철회/대체 탐지(**메타 철회 표시 + 전문 withdrawal 공지**) → tombstone(전 청크); INV-1 순서 준수. **순서는 DeduplicationGuard.isNew로 강제**: 더 새 vN=CHANGED→재upsert, 동일/이전=DUPLICATE→무시. 재구축 시 능동 재탐지. | **Q13=B** |
| **BR-15 (실패 분류)** | RETRIABLE=네트워크/타임아웃/5xx/429; PERMANENT=파싱·검증·비-OA·404. (전문 취득·임베딩·쓰기 실패 포함.) | RES-9, Q9=A |
| **BR-16 (재시도·쿼터)** | 지수 백오프+지터, arXiv 보수 쿼터(RES-8), 소진→DLQ. **수치는 NFR Q14 확정.** | RES-8/9, Q10=A |
| **BR-17 (DLQ·경보)** | 소진/영구→DLQ 격리 + 구조화 실패 신호 U6.ObservabilityHub. 잡 계속; 실패율 임계 초과→갱신 실패 경보. | RES-7, NFR-O1, NFR-R1, Q11=A |
| **BR-18 (fail-closed)** | 모든 외부 호출(arXiv/오브젝트 스토리지/임베딩 게이트웨이/벡터 스토어) 타임아웃·서킷; 실패 fail closed. | SEC-15, RES-9, NFR-R1 |
| **BR-19 (입력 검증)** | 파싱 산출 필수 필드·형식 검증·새니타이즈. | SEC-5 |
| **BR-20 (전문 보관·공개 차단)** | **Q2=C 활성**: OA 전문 원천을 오브젝트 스토리지 보관(StoredFullText/ObjectRef), **공개 차단(SEC-9)**, 재구축·재처리 재사용. at-rest 암호화/TLS(SEC-1, NFR Q17). | **SEC-9**, SEC-1, RES-2 |
| **BR-21 (본문 크기 정책)** | **Q2=C 활성**: 과대 본문 결정적 절단/청크 상한, 빈/손상 본문 PERMANENT 거부 또는 안전 처리. 임베딩 비용 통제(NFR-C1). | FR-6, NFR-C1 |

---

## 2. RejectedRecord 사유 분류

| RejectReason | 의미 | FailureClass |
|---|---|---|
| `NON_OA` | 비-OA/재배포 불가 라이선스(BR-1 프로덕션 검증) | PERMANENT |
| `PARSE_FAILURE` | 메타/전문 파싱 불가 | PERMANENT |
| `VALIDATION_VIOLATION` | 필수 필드/형식 위반(SEC-5) | PERMANENT |
| `FETCH_FAILURE` | 원천/전문 취득 실패 | RETRIABLE→소진 시 DLQ |

> 거부율(PARSE/VALIDATION 급증)은 BR-17 잡 실패율 경보 보조 신호(RES-7).

---

## 3. PBT 속성 (QT-4 / PBT-08 blocking)

| 속성 | 진술 | 트레이스 |
|---|---|---|
| **P1 디덥 멱등성** | isNew 결정적·입력 의존; 동일 이벤트/논문 재전송이 추가 인덱싱·중복 0(Q15=A). | PBT-08, BR-4/9/12 |
| **P2 청크 결정성** | 동일 ParsedPaper → 동일 ChunkSet·동일 ChunkId(섹션 인지 다중 청크 순서·내용 안정). | PBT-08, BR-5 |
| **P3 upsert 멱등성** | 동일 IndexRecordBatch 재upsert가 인덱스 상태 불변; CHANGED는 덮어쓰기. | PBT-08, BR-8/9 |
| **P4 무손실·무중복** | 주어진 ParsedPaper에 대해 `|upserted IndexRecords| == |ChunkSet|`(다중 청크 누락/중복 0). | NFR-R1, BR-7 |
| **P5 임베딩 정렬 보존** | `EmbeddingBatch.vectors[i] ↔ chunks[i].chunkId`(재정렬/누락 0). | NFR-R1, BR-7 |
| **P6 워터마크 단조성** | advanceWatermark는 BR-11 max-clamp(전진만); SEED_REBUILD 리셋만 예외. | RES-2, BR-11 |

> 프레임워크는 NFR Requirements(Q8=A Hypothesis)·도메인 제너레이터·shrinking·시드 재현성. P1/P3/P4/P5=PBT-08 차단성, P2=청크 결정성, P6=RES-2 정합.

---

## 4. 프로덕션 스코프 (데모 트랙 폐기 — 단일 트랙)

| 축 | 프로덕션 결정 | 비고 |
|---|---|---|
| 코퍼스 슬라이스 | cs.LG/cs.AI/cs.CL/cs.CV/stat.ML × 5년(수십만)(Q1=D) | FR-6 풀 슬라이스 |
| 본문 깊이 | OA 전문 청킹·다중 청크(Q2=C) | 전문 보관(BR-20) |
| 트리거 표면 | 수동 rebuild + 스케줄 증분 + **new-arXiv 이벤트 활성**(Q12=B) | 3경로 |
| 철회/tombstone | 탐지·tombstone 활성(Q13=B) | 메타+전문 신호(BR-14) |
| 평가셋 코퍼스 | QT-1/QT-2 대상 논문 포함 보장(Q14=A FD) | U2/U6 FD가 평가셋 구축 |
| OA 전문 보관/SEC-9 | **활성** — 오브젝트 스토리지 보관·공개 차단(BR-20) | 재구축 재사용 |
| 임베딩 모델/VectorSpec | **NFR Requirements(TD-3) 확정** | 시스템 전역 불변식(U1 writer=U2 reader 동일 공간) |
| 벡터+lexical 스토어 | **NFR Requirements(TD-4) 확정** | ANN+BM25 lexical+per-paperId 삭제 요건(BR-14) |
| NFR-C1 비용 상한 | **NFR Requirements 확정**(시스템 전역) | U6.CostGuardCircuitBreaker 강제; 디덥(BR-4)/본문 크기(BR-21) 통제 |

---

## 5. 추적성 매트릭스 (요구사항 → 규칙/속성/엔티티)

| 요구사항 | 랜딩 |
|---|---|
| **FR-6**(인제스천·인덱싱·갱신) | BR-2/5/6, IngestionPipelineService, RefreshOrchestrationService |
| **C-1**(OA 전용) | BR-1(OA 배제·라이선스), RejectReason(NON_OA) |
| **C-6**(AI/ML 전용) | CategoryFilter / resolveSliceCategories(5 카테고리, Q1=D) |
| **RES-2**(재구축 자산·RPO·런북) | BR-10/11/13, IndexStats, AS-5, BR-20(전문 재사용) |
| **RES-7**(갱신 실패 경보) | BR-17, RejectReason 거부율 |
| **RES-8**(쿼터 인지) | BR-16, ArxivSourceClient(증분+대량 하베스트) |
| **RES-9**(타임아웃·서킷·저하) | BR-15/16/18, IngestionResilienceService |
| **NFR-C1**(비용·디덥) | BR-4(DUPLICATE), BR-21(본문 크기), EmbeddingGatewayAdapter 텔레메트리; **상한=NFR Requirements 확정·시스템 전역(U6.CostGuardCircuitBreaker 강제)** |
| **NFR-R1**(부분/조용한 인덱싱 금지) | BR-7/8/13/17/18, P4/P5 |
| **NFR-O1**(관측성) | BR-17, IndexStats |
| **SEC-1 / SEC-5 / SEC-9 / SEC-15** | BR-20(at-rest/TLS) / BR-19 / BR-20(공개 차단) / BR-18 |
| **QT-4 / PBT-08** | P1~P6 |
| **US-I1**(시드 빌드) | triggerFullRebuild(대량 하베스트), BR-13 |
| **US-I2**(스케줄 갱신) | onScheduleTick, BR-10/17 |
| **US-I3**(복원력) | BR-15/16/17/18, IngestionResilienceService |
| **Q12=B**(이벤트 경로) | NewArxivEventHandler, BR-12, EVENT 잡 |
| **Q13=B**(철회) | BR-14, Tombstone, WithdrawalMarker |
| **미커버 검증** | 위 표로 U1 트레이스 0 미커버; backing US-H1/US-D2는 공유 인덱스 존재로 충족 |

---

## 6. 공유 계약 정합 주석 (VectorSpec)

- U1.EmbeddingGatewayAdapter(writer)·U2.QueryUnderstandingExpander(reader)는 **동일 VectorSpec(차원·모델·거리 — NFR Requirements PIN)**. 동일 임베딩 공간 불변식.
- 계약 산출물 소유=공유 임베딩 게이트웨이 레이어(UQ5=A); U1(빌드 #1)이 값을 PIN, 후속 유닛 재결정 없음(NS-5). 선택 스토어 ANN 인덱스가 PIN된 차원·거리 메트릭 지원 확인(ANN 호환 게이트).
- 단일 writer(U1)/단일 reader(U2) 경계.
