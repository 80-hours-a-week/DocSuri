# domain-entities.md — U1 Ingestion 도메인 엔티티

**단계**: CONSTRUCTION → Functional Design · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: `u1-ingestion-functional-design-plan.md`(답변: Q1~Q17 전부 A, **단 Q13=B**) · `inception/application-design/component-methods.md` U1 시그니처 · `requirements.md`
**원칙**: 기술 무관(엔티티 = 도메인 개념·관계·식별 규칙). 직렬화 포맷·저장 표현·임베딩 모델/차원은 NFR/Infra Design.
**범위 주석(데모)**: Q2=A(초록+메타데이터만 임베딩) → 본문 전문 엔티티는 계약만 보존하고 데모 비활성. Q13=B(철회 탐지·tombstone **활성**). Q12=A(이벤트 엔티티는 계약만, 스텁).

---

## 1. 식별자 값타입 & 식별/버전 규칙

| 엔티티 | 정의 | 규칙 |
|---|---|---|
| **ArxivId** | arXiv 식별자(버전 포함 가능, 예 `2401.01234`, `2401.01234v2`) | 원천 식별자. 버전 토큰 분리 가능. |
| **PaperId** | **정규 논문 식별자 = 버전 없는 ArxivId**(예 `2401.01234`) | **Q3=A**: 한 논문의 모든 버전이 동일 PaperId. 인덱스·디덥·라이브러리(U4) 참조의 안정 키. |
| **PaperVersion** | arXiv 버전 정수(vN) | 최신 버전만 인덱스에 존재(Q3=A latest-wins upsert). |
| **ChunkId** | 청크 결정적 식별자 = `chunkId(PaperId, ordinal)` | **PBT-08 결정성**: 동일 (PaperId, ordinal) → 동일 ChunkId(멱등 업서트 키). Q2=A에서 ordinal=0 단일 청크. |
| **ContentFingerprint** | 디덥 키. **Q6=A: `PaperId + PaperVersion`에서 파생한 값(콘텐츠 해시 아님)** | 잠긴 시그니처 `fingerprint()->ContentHash`와의 정합: `ContentHash`는 ID+버전 파생 키를 담는다(개념상 `VersionKey`). 콘텐츠 바이트 해싱 안 함. |
| **EventId** | new-arXiv 이벤트 식별자 | **Q12=A 스텁**. at-least-once 멱등 경계의 ack 단위. **Q15=A: 이벤트-레벨 dedup 없음** — 멱등은 ContentFingerprint(DUPLICATE) 백스톱이 단독 보장. |
| **JobId** | 인제스천 잡 식별자 | 잡 단위 진행도·실패율·워터마크 전진(advanceWatermark)의 상관 키. |

> **버전 의미(Q3/Q6/Q7 일관)**: 신규 게재 = 신규 PaperId(NEW). 동일 PaperId의 vN 증가 = CHANGED(재처리·덮어쓰기). 동일 PaperId·동일 vN 재수신 = DUPLICATE(단락). 워터마크 기준 시각 = arXiv **updated**(Q7=A)로 vN 개정도 증분 포착.

---

## 2. 수집·파싱 엔티티

| 엔티티 | 필드(개념) | 비고 |
|---|---|---|
| **CategoryFilter** | `categories[]`, `from`/`to`(기간) | **Q1=A 데모: `categories=[cs.LG]`, 최근 ~1년.** `resolveSliceCategories()` 산출. 프로덕션 타깃(5개·5년)은 동일 엔티티로 확장. |
| **PageCursor** | 불투명 페이지 커서 | `fetchMetadataPage` 페이지네이션 상태. |
| **MetadataPage** | `records[]`(원천 메타), `nextCursor`, `hasMore` | 슬라이스 페이지 단위 조회 결과. |
| **RawDocument** | `rawBody?`, `sourceMeta`, `oaStatus` | `fetchFullText` 산출. **Q2=A: `rawBody`(전문)는 데모 비활성** — 초록은 `sourceMeta`(메타데이터)에 포함. |
| **ParsedPaper** | `paperId`(PaperId), `version`(vN), `title`, `authors[]`, `year`, `abstract`, `categories[]`, `arxivUrl`, `updatedAt` | **Q2=A: 본문 없음 — 초록까지.** FetchParseProcessor.parse 산출. FR-4 카드 필드의 원천. |
| **RejectedRecord** | `reason`(RejectReason), `sourceRef` | parse/validate 거부 산출. **§4 RejectReason 분류 참조.** |
| **ValidationResult** | `ok`(bool), `violations[]` | `FetchParseProcessor.validate` 산출(SEC-5). `ok=false` → `VALIDATION_VIOLATION` RejectReason / PERMANENT(BR-15). |
| **WithdrawalMarker** | `paperId`, `detectedAt`, `signal`(withdrawal 근거) | **Q13=B 활성.** 철회/대체 탐지 산출 → tombstone 라우팅. Q2=A 탐지원: arXiv 메타데이터 철회 표시 / 초록의 withdrawal 공지 패턴. |

---

## 3. 청킹·임베딩 엔티티

| 엔티티 | 필드(개념) | 비고 |
|---|---|---|
| **Chunk** | `chunkId`, `paperId`, `text`, `section`, `position`(ordinal) | 추적 메타 부착(FR-5 근거화 지원). **Q2=A: 논문당 초록 1청크(ordinal=0).** 계약은 다중 청크(전문) 확장 가능. |
| **ChunkSet** | `paperId`, `chunks[]` | Chunker.chunk 산출. **결정성**: 동일 ParsedPaper → 동일 ChunkSet(PBT-08). |
| **EmbeddingBatch** | `vectors[]`(**chunkId에 정렬**), `vectorSpecRef` | EmbeddingGatewayAdapter.embedBatch 산출. **정렬 불변식**: `vectors[i] ↔ chunks[i].chunkId`(재정렬/누락 0, PBT). 임베딩 공간 = 공유 `VectorSpec`. |

---

## 4. 인덱스 엔티티 (공유 벡터 인덱스 — U1 write-only 생산자)

| 엔티티 | 필드(개념) | 비고 |
|---|---|---|
| **IndexRecord** | `chunkId`, `paperId`, `version`, `vector`, **카드 필드**(title·authors·year·arxivId·abstractSnippet·arxivUrl) + `categories` + `abstract`(전체, 스니펫 산출용) + `lexicalTerms`(제목+초록 토큰) | **Q4=A.** FR-2 하이브리드(lexical) + FR-4 카드 + FR-5 해소 가능 ID/링크. U2 reader가 동일 레코드 소비. |
| **IndexRecordBatch** | `records[]`(IndexRecord), `paperId`, `jobRef?` | `VectorIndexWriter.upsert` 입력 = **논문 단위 원자 커밋 단위**(Q8=A/BR-7). Q2=A에서 논문당 1 IndexRecord이나 계약은 다중. PBT P3/P4 대상. |
| **WriteResult** | `written`, `skipped`, `failed[]` | upsert/tombstone 결과. `failed[]`는 IngestionResilienceService로. |
| **IndexStats** | `docCount`, `vectorCount`, `lastWrite` | **소비 계약(business-logic-model §5)**: U6.HealthCheckService.deepCheck(RES-6) + RES-2 재구축 완전성 검증. `lastWrite`는 성공 upsert/tombstone 커밋 시 전진. |
| **Tombstone** | `paperId`, `tombstonedAt`, `reason` | **Q13=B 활성.** 철회 논문을 인덱스에서 제거. **순서 규칙(business-rules BR)**: tombstone이 우선하되 **엄격히 더 새로운 vN의 upsert가 오면 그것이 우선**(stale in-flight upsert 방지). |

> **단일 writer/단일 reader**: U1.VectorIndexWriter만 쓰고 U2.HybridRetriever만 읽는다(inception 잠금). U1 엔티티는 인덱스 **쓰기 측** 진실.

---

## 5. 제어 평면 엔티티

| 엔티티 | 필드(개념) | 비고 |
|---|---|---|
| **ScheduleTrigger** | `firedAt`, `kind`(`INCREMENTAL`) | RefreshScheduler.onSchedule 입력(제안 일 1회, 수치는 Infra). |
| **NewArxivEvent** | `eventId`, `arxivRef` | **Q12=A 스텁** — NewArxivEventHandler 계약만. 데모 비활성. |
| **IngestionJob** | `jobId`, `kind`(**`SEED_REBUILD` \| `INCREMENTAL`**), `slice`(CategoryFilter), `since?`(Watermark), `status` | RefreshOrchestrationService가 생성·분배. `SEED_REBUILD`=US-I1 초기/전체 재구축(워터마크 리셋), `INCREMENTAL`=US-I2 증분(since=watermark). |
| **Watermark** | 단일 전역 타임스탬프(arXiv **updated** 기준, Q7=A) | RPO 지표(RES-2). **Q17=A max-clamp**: advanceWatermark는 전진만(역행 무시); `SEED_REBUILD`만 의도적 리셋 허용(Q16 상호배제로 보호). |

---

## 6. 디덥·상태 엔티티

| 엔티티 | 필드(개념) | 비고 |
|---|---|---|
| **DedupState** | `paperId` → `fingerprint`(ContentFingerprint), `ingestedAt` | DeduplicationGuard.markIngested가 기록. **INV-1**: upsert 내구화 성공 후에만 기록. |
| **DedupDecision** | `NEW` \| `CHANGED` \| `DUPLICATE` | isNew 산출. NEW/CHANGED만 chunk→embed→upsert 진행; DUPLICATE 단락(NFR-C1 재임베딩 비용 회피). |

---

## 7. 실패 엔티티 (US-I3 / RES-7/8/9)

| 엔티티 | 필드(개념) | 비고 |
|---|---|---|
| **IngestError** | `stage`, `cause`, `httpStatus?` | 파이프라인 단계 오류 원천. |
| **FailureClass** | `RETRIABLE` \| `PERMANENT` | **Q9=A**: RETRIABLE=네트워크/타임아웃/5xx/429; PERMANENT=파싱·검증·비-OA·404. |
| **RetryDecision** | `RETRY`(at delay) \| `EXHAUSTED` | **Q10=A**: 지수 백오프+지터, 보수적 쿼터(수치 Infra). |
| **IngestItem** | 재시도 가능 작업 단위(per-paper: `MetadataPage.record` + 잡 컨텍스트) | `scheduleRetry`/`sendToDLQ` 파라미터. 재시도/DLQ 입도 = **논문 단위**(Q8=A 정합). |
| **DLQItem** | `item`(IngestItem), `reason`(FailureReason), `attempts` | 소진/영구 항목 격리(US-I3). |
| **FailureReason** | 사유 코드 | RejectReason ∪ {RETRY_EXHAUSTED, EMBEDDING_FAILURE, WRITE_FAILURE …}. |

**RejectReason 분류(business-rules §RejectedRecord)**: `NON_OA` · `PARSE_FAILURE` · `VALIDATION_VIOLATION` · `FETCH_FAILURE`. (Q5=A·Q2=A에서 NON_OA는 사실상 0.)

---

## 8. 공유 계약 (참조 — U1 소유 아님)

| 엔티티 | 정의 | 비고 |
|---|---|---|
| **VectorSpec** | `dimensions`, `modelRef`, `distanceMetric` | 공유 임베딩 게이트웨이 레이어 소유 단일 진실 원천. **U1 writer ↔ U2 reader 동일 임베딩 공간 불변식**(인덱스 정합성). **구체 값은 NFR Requirements**(EmbeddingGatewayAdapter.embeddingSchema()로 노출). |

---

## 9. 엔티티 관계 (요약)

```
CategoryFilter ──(fetchMetadataPage)──▶ MetadataPage{ records[] }
   record ──(parse)──▶ ParsedPaper{ paperId, version, abstract, ... }   │ (Q13=B) 철회 탐지 ─▶ WithdrawalMarker ─▶ Tombstone
      │                                                                  │
      ├─(fingerprint = paperId+version, Q6=A)─▶ ContentFingerprint ─(isNew)─▶ DedupDecision
      │                                                                       │ NEW|CHANGED
      ▼                                                                       ▼
   (Q2=A) ParsedPaper.abstract ─(chunk)─▶ ChunkSet{ Chunk(ordinal=0) } ─(embedBatch)─▶ EmbeddingBatch{ vectors aligned to chunkId }
                                                                                          │
                                                       Chunk + ParsedPaper 메타 + vector ─▶ IndexRecord ─(upsert)─▶ [공유 벡터 인덱스]
                                                                                          │ INV-1: upsert durable ─▶ markIngested(DedupState) ─▶ advanceWatermark(Watermark, max-clamp)
IngestionJob{ SEED_REBUILD | INCREMENTAL } ── 제어 ──▶ (위 파이프라인을 논문 단위로 분배; Q8 논문 단위 원자성)
실패(IngestError) ─(classify)─▶ FailureClass ─▶ RetryDecision | DLQItem ─▶ (경보)
```

> 식별 규칙·관계의 **결정·검증 규칙**은 `business-rules.md`, **오케스트레이션 흐름**은 `business-logic-model.md` 참조.
