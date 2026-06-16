# business-logic-model.md — U1 Ingestion 비즈니스 로직 모델

**단계**: CONSTRUCTION → Functional Design · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: 계획서 답변(Q1~Q17=A, **Q13=B**) · `inception/application-design/{services,component-methods,component-dependency}.md`
**원칙**: 기술 무관 알고리즘 수준. 타임아웃·동시성 수치, 큐/스토어 구현은 NFR/Infra.

---

## 1. 서비스 오케스트레이션 (3종, 전부 이벤트/스케줄 백본 — 사용자 동기 경로 아님)

### 1.1 IngestionPipelineService — 논문 단위 end-to-end (FR-6, US-I1, NFR-R1, NFR-C1)
한 논문(또는 배치)을 인제스천하는 핵심 오케스트레이터. **논문 단위 원자성(Q8=A) + 커밋 순서 INV-1.**

```
ingestOne(record, job):
  1. parsed | rejected ← FetchParseProcessor.parse(record)            # Q2=A: 메타데이터→초록까지
       rejected → IngestionResilienceService.handle(PERMANENT, reason)  # RejectReason
  2. validation ← FetchParseProcessor.validate(parsed)                # SEC-5 필수필드/형식
       violation → handle(PERMANENT, VALIDATION_VIOLATION)
  3. (Q13=B) if FetchParseProcessor 가 철회 신호 탐지 → WithdrawalMarker
       → VectorIndexWriter.tombstone(paperId) → markIngested(paperId+vN) → advanceWatermark(job.id, parsed.updatedAt) → return TOMBSTONED   # INV-1 순서 일관; §2 순서 규칙
  4. decision ← DeduplicationGuard.isNew(parsed)                      # Q6=A: paperId+version
       DUPLICATE → return SKIPPED (단락, 재임베딩 비용 0 — NFR-C1)
       NEW | CHANGED → 계속
  5. chunkSet ← Chunker.chunk(parsed)                                 # Q2=A: 초록 1청크(ordinal=0), 결정적
  6. embeddings ← EmbeddingGatewayAdapter.embedBatch(chunkSet)        # 공유 VectorSpec 공간; 비용 텔레메트리
  7. records ← assemble IndexRecordBatch (IndexRecord[], chunk + parsed 메타 + vector, Q4=A)  # 논문 단위 원자 커밋 단위
  8. # ── INV-1 커밋 순서 (논문 단위 원자성) ──
     writeResult ← VectorIndexWriter.upsert(records)                  # 전 청크 성공해야 commit
       partial/fail → handle(classify(err)); 미커밋(부분 인덱싱 금지, NFR-R1); return RETRY|DLQ
     DeduplicationGuard.markIngested(paperId, fingerprint)            # upsert durable 후에만
     RefreshScheduler.advanceWatermark(job.id, parsed.updatedAt)      # 잡 단위, max-clamp(Q17)
  9. 모든 단계 오류 → IngestionResilienceService (재시도/DLQ/경보)
```
- **원자성(Q8=A)**: 한 논문의 전 청크가 임베딩·기록 성공해야 `markIngested`. 일부 실패 = 미커밋·재시도(부분 인덱싱 금지). Q2=A에서 논문당 1청크라 자명하나 계약은 다중 청크.
- **크래시 복구(INV-1)**: upsert 후 markIngested 전 크래시 → 다음 실행이 CHANGED/NEW 재분류·**멱등 재upsert**(동일 ChunkId 키)로 정합.

### 1.2 RefreshOrchestrationService — 제어 평면 (US-I1/I2, RES-2, Q12=A, Q16=A)
인제스천 개시 진입점 통합·잡 분배.

```
triggerFullRebuild():                                  # US-I1 시드/전체 재구축, RES-2
  acquire REBUILD_LOCK (Q16=A 상호 배제)                 # 활성 rebuild 동안 INCREMENTAL 보류/거부
  job ← IngestionJob(SEED_REBUILD, slice=resolveSliceCategories(), since=null)
  reset Watermark (의도적 리셋 — Q17 예외 경로)
  for page in paginate(ArxivSourceClient.fetchMetadataPage(slice, cursor, since=null)):
      for record in page.records: IngestionPipelineService.ingestOne(record, job)  # 쿼터 인지 배치(Q10)
  release REBUILD_LOCK; emit job 건강도(진행도·실패율)

onScheduleTick(trigger):                               # US-I2 증분
  if REBUILD_LOCK held → defer/reject (Q16=A)           # RPO 손상 방지(NFR-R1)
  job ← RefreshScheduler.onSchedule(trigger) → IngestionJob(INCREMENTAL, slice, since=Watermark)
  for page in paginate(fetchMetadataPage(slice, cursor, since=Watermark)):
      for record in page.records: IngestionPipelineService.ingestOne(record, job)

onNewArxivEvent(event):                                # Q12=A 스텁(데모 비활성) — 계약만
  # 활성 시: NewArxivEventHandler.onNewArxivEvent → IngestionJob → ingestOne; ackEvent (Q15=A 멱등)
```
- **Q16=A 상호 배제**: 단일 writer 인덱스 보호. rebuild 진행 중 증분은 보류/거부 → 증분이 미재구축 레코드를 지나 워터마크 전진(RPO 손상)하는 경로 차단.
- **Q12=A**: 데모는 `triggerFullRebuild`(시드) + `onScheduleTick`(증분)만. 이벤트 경로는 계약·멱등 의미만 정의(§Q15).

### 1.3 IngestionResilienceService — 복원력 횡단 (US-I3, RES-7/8/9, NFR-R1)
```
handle(error|class, context):
  cls ← IngestFailureHandler.classify(error)            # Q9=A
  if RETRIABLE: decision ← scheduleRetry(item, attempt) # Q10=A 지수 백오프+지터, 쿼터 인지
       RETRY → 재시도 큐 ; EXHAUSTED → sendToDLQ
  if PERMANENT: sendToDLQ(item, reason)
  emitFailureSignal(jobId, error) → U6.ObservabilityHub # Q11=A 구조화 로그·경보
  # 잡은 계속 진행(한 논문 실패가 전체를 막지 않음); 잡 실패율 임계 초과 → 갱신 실패 경보(RES-7, US-I2)
```
- 외부 호출(ArxivSourceClient/EmbeddingGatewayAdapter/VectorIndexWriter)에 **타임아웃·서킷 주입(RES-9)**. 부분 인덱싱 차단(NFR-R1).

---

## 2. 컴포넌트 알고리즘 수준 (9개)

| 컴포넌트 | 핵심 알고리즘(데모, Q-답 반영) |
|---|---|
| **ArxivSourceClient** | `resolveSliceCategories`→ `CategoryFilter{[cs.LG], 최근~1년}`(Q1=A). `fetchMetadataPage` 워터마크 이후(updated 기준 Q7=A) 페이지네이션, 레이트/쿼터 보수 준수(RES-8)·타임아웃(RES-9). **`fetchFullText` 데모 비활성(Q2=A)** — 계약 보존. 실패 fail-closed(SEC-15). |
| **FetchParseProcessor** | `parse`: 메타데이터→ParsedPaper(초록까지, Q2=A). 비-OA 배제(Q5=A: 사실상 0, 취득 실패만). `validate`: 필수필드·형식(SEC-5). **(Q13=B) 철회 신호 탐지 → WithdrawalMarker**(arXiv 메타 철회 표시/초록 withdrawal 공지 패턴). 파싱 실패 분류 위임. |
| **Chunker** | `chunk`: Q2=A 초록 1청크(ordinal=0), 추적 메타(paperId·section·position) 부착, **결정적·멱등**(PBT-08). `chunkId(paperId, ordinal)` 결정적 키. 빈/비정상 초록 안전 처리. |
| **EmbeddingGatewayAdapter** | `embedBatch`: 청크 배치 벡터화(공유 VectorSpec 공간), 타임아웃·재시도·서킷(RES-9), 비용 텔레메트리(NFR-C1), **vector↔chunkId 정렬 보존**. `embeddingSchema()`→VectorSpec. 게이트웨이 장애 fail-closed(SEC-15). |
| **VectorIndexWriter** | `upsert`: ChunkId 키 **멱등 upsert**(latest-wins, Q3=A). `tombstone`(Q13=B 활성): 철회 제거, **순서 규칙** 아래. `indexStats`→IndexStats(§5). 쓰기 실패 표면화(NFR-R1). |
| **DeduplicationGuard** | `fingerprint`= paperId+version 파생(Q6=A). `isNew`→ NEW/CHANGED/DUPLICATE. `markIngested` INV-1 순서로 기록. **이벤트 재전송 멱등 단일 백스톱(Q15=A).** |
| **RefreshScheduler** | `onSchedule`→ INCREMENTAL 잡. `advanceWatermark` **max-clamp(Q17=A, 전진만)**. `triggerFullRebuild`→ SEED_REBUILD 잡(워터마크 리셋). |
| **NewArxivEventHandler** | **Q12=A 스텁**: `onNewArxivEvent`/`ackEvent` 계약만. 활성 시 at-least-once, 멱등은 DedupGuard DUPLICATE 백스톱(Q15=A), 포이즌 이벤트 DLQ. |
| **IngestFailureHandler** | `classify`(Q9=A), `scheduleRetry`(Q10=A), `sendToDLQ`(US-I3), `emitFailureSignal`(Q11=A → ObservabilityHub). |

### Tombstone 순서 규칙 (Q13=B)
- `tombstone(paperId)`는 인덱스에서 해당 PaperId 레코드 제거. tombstone 경로도 INV-1 순서(tombstone durable → `markIngested(paperId+vN)` → `advanceWatermark`)를 따른다.
- **순서는 별도 메커니즘이 아니라 `DeduplicationGuard.isNew`로 강제**: 철회 후 **엄격히 더 새로운 vN**가 오면 isNew=CHANGED → 재upsert(부활); **동일/이전 vN**는 DUPLICATE → 무시(stale in-flight upsert가 신규 버전을 덮거나 철회를 되살리지 않음).
- **재구축 시에도** 동일 철회-신호 탐지(BR-14)가 parse 경로에서 **능동 실행**되어 철회 논문은 tombstone되거나 미upsert된다(수동적 누락이 아니라 능동적 재탐지).

---

## 3. 제어 흐름 — 트리거 표면 (Q12=A)

```
[수동/CLI/운영]            [Scheduler/Timer (제안 일1회)]        [Event Bus] (Q12=A 스텁)
      │ triggerFullRebuild         │ onScheduleTick                   │ onNewArxivEvent (비활성)
      ▼                            ▼                                   ▼
        RefreshOrchestrationService  ──(REBUILD_LOCK 상호배제, Q16=A)──
                       │ 잡 분배(논문 단위)
                       ▼
            IngestionPipelineService.ingestOne  → (per-paper 파이프라인 §1.1)
```

---

## 4. 데이터 흐름 ASCII (per-paper, 철회 분기 포함)

```
fetchMetadataPage ─▶ record ─(parse,Q2=A)─▶ ParsedPaper
                                   │
              (Q13=B) 철회신호? ──예──▶ tombstone(paperId) ─▶ markIngested ─▶ advanceWatermark(max-clamp)
                                   │아니오
                          isNew(paperId+version)
                          │DUPLICATE        │NEW|CHANGED
                          ▼                 ▼
                       SKIPPED      chunk(초록,결정적) ─▶ embedBatch(VectorSpec) ─▶ IndexRecord[]
                                                                                      │ INV-1
                                              upsert(멱등) ─durable─▶ markIngested ─▶ advanceWatermark
   실패 전 단계 ─▶ IngestionResilienceService ─▶ classify ─▶ retry|DLQ ─▶ emitFailureSignal ▶ U6.ObservabilityHub
```

---

## 5. IndexStats 소비 계약 (cross-unit)

- `indexStats() -> IndexStats{docCount, vectorCount, lastWrite}`.
- **소비자**: U6.HealthCheckService.deepCheck(RES-6, 벡터 스토어 연결성·규모) + **RES-2 재구축 완전성 검증**(시드 빌드 후 docCount가 기대 코퍼스 규모에 도달했는지).
- **`lastWrite` 의미**: 성공 upsert/tombstone 커밋 시각에 전진(인제스천 건강도·정체 탐지 신호, RES-7).
- **운영 재구축 런북**(AS-5): `triggerFullRebuild` 진입점은 여기서 정의, 절차·실행자·검증 단계 문서화는 Infra/Operations.

> 결정·검증 규칙(원자성·멱등·워터마크 역행·실패 분류·OA·tombstone 순서·PBT 속성)은 `business-rules.md`. 엔티티 정의는 `domain-entities.md`.
