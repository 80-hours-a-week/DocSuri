# business-logic-model.md — U1 Ingestion 비즈니스 로직 모델 (프로덕션)

**단계**: CONSTRUCTION → Functional Design · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: 계획서(프로덕션 재스코핑) — Q1=D·Q2=C·Q12=B·Q13=B·그 외 A.
**원칙**: 기술 무관 알고리즘 수준. 타임아웃·동시성 수치·큐/스토어 구현은 NFR/Infra.
**프로덕션 스코프**: 전문 수집·다중 청크·이벤트 경로·철회 tombstone·전문 오브젝트 보관 전부 활성.

---

## 1. 서비스 오케스트레이션 (3종, 이벤트/스케줄 백본)

### 1.1 IngestionPipelineService — 논문 단위 end-to-end (FR-6, US-I1, NFR-R1, NFR-C1)
**논문 단위 원자성(Q8=A) + 커밋 순서 INV-1.** Q2=C로 전문 취득·다중 청크 활성.

```
ingestOne(record, job):
  1. raw ← ArxivSourceClient.fetchFullText(arxivId)                  # Q2=C 전문 취득(활성)
  2. parsed | rejected ← FetchParseProcessor.parse(raw)              # 메타+전문 본문 정규화
       rejected → IngestionResilienceService.handle(PERMANENT, reason)
  3. validation ← FetchParseProcessor.validate(parsed)              # SEC-5 필수필드/형식
       violation → handle(PERMANENT, VALIDATION_VIOLATION)
  4. (Q13=B) if 철회 신호 탐지(메타 + 전문 withdrawal 공지) → WithdrawalMarker
       → VectorIndexWriter.tombstone(paperId) → markIngested(paperId+vN) → advanceWatermark → return TOMBSTONED   # INV-1; §2 순서 규칙
  5. decision ← DeduplicationGuard.isNew(parsed)                    # Q6=A paperId+version
       DUPLICATE → return SKIPPED (단락, 재임베딩 0 — NFR-C1)
       NEW | CHANGED → 계속
  6. (Q2=C) 전문 원천 보관: StoredFullText(objectRef) ← ObjectStorage.put(raw)   # SEC-9 공개 차단, 재구축 재사용
  7. chunkSet ← Chunker.chunk(parsed)                               # 섹션 인지 다중 청크, 결정적
  8. embeddings ← EmbeddingGatewayAdapter.embedBatch(chunkSet)      # 공유 VectorSpec(NFR PIN); 비용 텔레메트리
  9. records ← assemble IndexRecordBatch (IndexRecord[] = 논문 전 청크, Q4=A)   # 논문 단위 원자 커밋 단위
  10. # ── INV-1 커밋 순서 (논문 단위 원자성) ──
      writeResult ← VectorIndexWriter.upsert(records)               # 전 청크 성공해야 commit
        partial/fail → handle(classify(err)); 미커밋(부분 인덱싱 금지, NFR-R1); return RETRY|DLQ
      DeduplicationGuard.markIngested(paperId, fingerprint)         # upsert durable 후
      RefreshScheduler.advanceWatermark(job.id, parsed.updatedAt)   # 잡 단위, max-clamp(Q17)
  11. 모든 단계 오류 → IngestionResilienceService (재시도/DLQ/경보)
```
- **원자성(Q8=A)**: 한 논문의 **전 청크**(다중) 임베딩·기록 성공 시에만 markIngested. 일부 실패=미커밋·재시도(부분 인덱싱 금지).
- **크래시 복구(INV-1)**: upsert 후 markIngested 전 크래시 → 다음 실행 CHANGED/NEW 재분류·**멱등 재upsert**(ChunkId 키)로 정합.

### 1.2 RefreshOrchestrationService — 제어 평면 (US-I1/I2, RES-2, Q12=B, Q16=A)
인제스천 개시 **3 진입점** 통합·잡 분배.

```
triggerFullRebuild():                                  # US-I1 시드/전체 재구축, RES-2
  acquire REBUILD_LOCK (Q16=A 상호 배제)                 # rebuild 동안 INCREMENTAL/EVENT 보류·거부
  job ← IngestionJob(SEED_REBUILD, slice=resolveSliceCategories() [5cat,5yr], since=null)
  reset Watermark (의도적 리셋 — Q17 예외 경로)
  for batch in harvest(대량 시드 하베스트):              # 프로토콜=NFR Q2; 수십만
      for record in batch: IngestionPipelineService.ingestOne(record, job)  # 쿼터 인지 동시성(NFR Q11=B, 쓰기 직렬화)
  release REBUILD_LOCK; emit job 건강도(진행도·실패율)

onScheduleTick(trigger):                               # US-I2 증분(일 1회)
  if REBUILD_LOCK held → defer/reject (Q16=A)
  job ← RefreshScheduler.onSchedule(trigger) → IngestionJob(INCREMENTAL, slice, since=Watermark)
  for page in paginate(ArxivSourceClient.fetchMetadataPage(slice, cursor, since=Watermark)):  # 증분 조회(프로토콜=NFR Q2)
      for record in page.records: IngestionPipelineService.ingestOne(record, job)

onNewArxivEvent(event):                                # Q12=B 활성(이벤트 경로)
  if REBUILD_LOCK held → defer (Q16=A)
  job ← NewArxivEventHandler.onNewArxivEvent(event) → IngestionJob(EVENT, 단건)
  IngestionPipelineService.ingestOne(event.record, job); NewArxivEventHandler.ackEvent(eventId)  # at-least-once 멱등(Q15=A)
```
- **Q16=A 상호 배제**: 단일 writer 인덱스 보호. rebuild 중 증분·이벤트 보류/거부(RPO 손상 차단).
- **Q12=B 활성**: 이벤트·스케줄·수동 재구축 3경로 모두 운영. 동시성은 fetch/embed 병렬·인덱스 쓰기 직렬화(NFR Q11=B, 단일 writer 유지).

### 1.3 IngestionResilienceService — 복원력 횡단 (US-I3, RES-7/8/9, NFR-R1)
```
handle(error|class, context):
  cls ← IngestFailureHandler.classify(error)            # Q9=A (전문 취득·임베딩·쓰기 실패 포함)
  if RETRIABLE: decision ← scheduleRetry(item, attempt) # Q10=A 지수 백오프+지터, 쿼터 인지
       RETRY → 재시도 큐(NFR Q6 PIN) ; EXHAUSTED → sendToDLQ
  if PERMANENT: sendToDLQ(item, reason)
  emitFailureSignal(jobId, error) → U6.ObservabilityHub # Q11=A 구조화 로그·경보
  # 잡 계속 진행; 잡 실패율 임계 초과 → 갱신 실패 경보(RES-7, US-I2)
```
- 외부 호출(ArxivSourceClient/ObjectStorage/EmbeddingGatewayAdapter/VectorIndexWriter)에 **타임아웃·서킷 주입(RES-9)**. 부분 인덱싱 차단(NFR-R1).

---

## 2. 컴포넌트 알고리즘 수준 (9개, 프로덕션)

| 컴포넌트 | 핵심 알고리즘(프로덕션) |
|---|---|
| **ArxivSourceClient** | `resolveSliceCategories`→ 5 카테고리·최근 5년(Q1=D). `fetchMetadataPage`(증분, updated 기준 Q7=A) + 대량 시드 하베스트(프로토콜 NFR Q2). **`fetchFullText` 활성(Q2=C)** — OA 전문 취득. 레이트/쿼터 보수 준수(RES-8)·타임아웃(RES-9)·fail-closed(SEC-15). |
| **FetchParseProcessor** | `parse`: 메타+**전문 본문** ParsedPaper(Q2=C). OA 판정(엄격 라이선스 검증, BR-1). `validate`: 필수필드·형식(SEC-5). **(Q13=B) 철회 신호 탐지**(메타 철회 표시 + 전문 withdrawal 공지) → WithdrawalMarker. |
| **Chunker** | `chunk`: **섹션 인지 다중 청크**(초록·본문 섹션, 오버랩 정책), 추적 메타(paperId·section·position), **결정적·멱등**(PBT-08). `chunkId(paperId, ordinal)` 결정적. 과대/빈/손상 본문 정책(BR-21). |
| **EmbeddingGatewayAdapter** | `embedBatch`: 다중 청크 배치 벡터화(**공유 VectorSpec, NFR PIN**), 타임아웃·재시도·서킷(RES-9), 비용 텔레메트리(NFR-C1), vector↔chunkId 정렬 보존. `embeddingSchema()`→VectorSpec. fail-closed(SEC-15). |
| **VectorIndexWriter** | `upsert`: ChunkId 키 멱등 upsert(논문 전 청크 배치, latest-wins Q3=A). `tombstone`(Q13=B): 철회 논문 전 청크 제거(순서 규칙 아래). `indexStats`→IndexStats(§5). 쓰기 실패 표면화(NFR-R1). |
| **DeduplicationGuard** | `fingerprint`=paperId+version(Q6=A). `isNew`→NEW/CHANGED/DUPLICATE. `markIngested` INV-1 순서. **이벤트 재전송 멱등 단일 백스톱(Q15=A).** |
| **RefreshScheduler** | `onSchedule`→INCREMENTAL 잡. `advanceWatermark` max-clamp(Q17=A). `triggerFullRebuild`→SEED_REBUILD(워터마크 리셋). |
| **NewArxivEventHandler** | **Q12=B 활성**: `onNewArxivEvent`→EVENT 잡, `ackEvent`(at-least-once, 멱등=DedupGuard DUPLICATE 백스톱 Q15=A, 포이즌 이벤트 DLQ). |
| **IngestFailureHandler** | `classify`(Q9=A), `scheduleRetry`(Q10=A), `sendToDLQ`(US-I3), `emitFailureSignal`(Q11=A→ObservabilityHub). |

### Tombstone 순서 규칙 (Q13=B)
- `tombstone(paperId)`는 인덱스에서 해당 PaperId의 **전 청크** 제거. tombstone 경로도 INV-1 순서(durable → markIngested(paperId+vN) → advanceWatermark).
- **순서는 `DeduplicationGuard.isNew`로 강제**: 철회 후 엄격히 더 새로운 vN → CHANGED → 재upsert(부활); 동일/이전 vN → DUPLICATE → 무시(stale upsert가 신규 버전·철회를 덮지 않음).
- **재구축 시에도** 동일 철회-신호 탐지(BR-14)가 parse 경로에서 능동 실행(능동 재탐지).

---

## 3. 제어 흐름 — 트리거 표면 (Q12=B, 3경로 모두 활성)

```
[수동/CLI/운영]            [Scheduler/Timer (일1회)]        [Event Bus (Q12=B 활성)]
      │ triggerFullRebuild         │ onScheduleTick                   │ onNewArxivEvent
      ▼                            ▼                                   ▼
        RefreshOrchestrationService  ──(REBUILD_LOCK 상호배제, Q16=A; rebuild 중 증분·이벤트 보류)──
                       │ 잡 분배(논문 단위, fetch/embed 병렬·쓰기 직렬화)
                       ▼
            IngestionPipelineService.ingestOne  → (per-paper 파이프라인 §1.1)
```

---

## 4. 데이터 흐름 ASCII (per-paper, 프로덕션 — 전문·다중 청크·철회)

```
fetchFullText(Q2=C) ─▶ RawDocument ─(parse)─▶ ParsedPaper{abstract, body/sections} ─▶ StoredFullText(ObjectRef, SEC-9)
                                   │ (Q13=B) 철회신호(메타+전문)? ──예──▶ tombstone(전 청크) ─▶ markIngested ─▶ advanceWatermark
                                   │아니오
                          isNew(paperId+version)
                          │DUPLICATE        │NEW|CHANGED
                          ▼                 ▼
                       SKIPPED      chunk(섹션 인지 다중) ─▶ embedBatch(공유 VectorSpec) ─▶ IndexRecord[](청크당)
                                                                                      │ INV-1, 논문 단위 원자
                                          upsert(IndexRecordBatch, 멱등) ─durable─▶ markIngested ─▶ advanceWatermark
   실패 전 단계 ─▶ IngestionResilienceService ─▶ classify ─▶ retry(큐)|DLQ ─▶ emitFailureSignal ▶ U6.ObservabilityHub
```

---

## 5. IndexStats 소비 계약 (cross-unit)

- `indexStats() -> IndexStats{docCount, vectorCount, lastWrite}`. **프로덕션: vectorCount ≫ docCount(논문당 다중 청크).**
- **소비자**: U6.HealthCheckService.deepCheck(RES-6, 벡터 스토어 연결성·규모) + **RES-2 재구축 완전성 검증**(시드 후 docCount/vectorCount가 기대 코퍼스 규모 도달).
- **`lastWrite`**: 성공 upsert/tombstone 커밋 시 전진(인제스천 건강도·정체 탐지, RES-7).
- **운영 재구축 런북**(AS-5): triggerFullRebuild 진입점 정의; 절차·실행자·검증은 Infra/Operations.

> 결정·검증 규칙은 `business-rules.md`. 엔티티는 `domain-entities.md`.
