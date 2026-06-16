# u1-ingestion-nfr-design-plan.md — NFR Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Design (유닛별 루프, U1) · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: `construction/u1-ingestion/nfr-requirements/`(스택·NFR 확정) · `functional-design/`(BR·INV-1·PBT) · `requirements.md`(RES/SEC/NFR)
**목적**: 확정 NFR을 **설계 패턴 + 논리 컴포넌트**로 구현. **보류된 RES-4(CI/CD·롤백·배포)·RES-12(복원력 테스트 방식)** 를 여기서 확정.
**고도**: 패턴·논리 컴포넌트·CI-CD/테스트 **방식**. 실제 클라우드 자원 매핑·**리전/AZ 토폴로지(RES-2 단일 리전 멀티 AZ)**·인스턴스 사이징·구체 IAM 정책 JSON·IaC·OpenSearch 샤드 수는 **Infrastructure Design**.
**스코프**: 프로덕션 단일 트랙. 스택 잠금(NFR Requirements): Python·OpenSearch·cross-lingual 임베딩(Bedrock)·EventBridge·SQS·S3·Hypothesis·NFR-C1 $1600/월.
**검증**: 적대적 비평 1패스 보강(_bulk 원자성 실현 신설·tombstone 삭제 패턴 신설·RES-12/RES-2 ID 정정·RES-1 트레이스·제어평면 저장소 트레이드오프).

> **ID 정정 주석(SSOT requirements.md 대조)**: 복원력 테스트 = **RES-12**(RESILIENCY-14는 프레임워크 태그); 단일 리전 멀티 AZ 토폴로지 = **RES-2**; RES-8 = 오토스케일링/쿼터(Q6). 인셉션 산출물(`execution-plan.md`·`aidlc-state.md`)·NFR Requirements 계획의 RES-14/RES-8(토폴로지) 표기도 **SSOT로 정정 완료(2026-06-16, 팀 지시)**.
> **[전역] 표기**: U1(빌드 #1)이 정하면 U2~U6 상속(특히 CI/CD·IAM·제어평면 패턴)에 `[전역]`.

---

## 1. 유닛 컨텍스트 (NFR Design 렌즈)

- U1 = 비동기 인제스천 워커. 설계 패턴: **복원력**(재시도·DLQ·서킷·멱등·단일 writer 락·**비트랜잭션 _bulk 위 논문 단위 원자 커밋**), **확장성**(병렬 fetch/embed + 멱등 bulk upsert, arXiv 쿼터 한정), **성능**(배치 임베딩·bulk 인덱싱·dedup-first), **보안**(최소 권한 IAM·암호화·시크릿·SEC-10), **논리 컴포넌트**(큐+DLQ·스케줄러·**제어평면 상태 저장소**·전문 스토리지·인덱스·임베딩 엔드포인트).
- **비용 책임 경계**: U1은 임베딩 비용 텔레메트리(호출/토큰/배치)를 U6.ObservabilityHub로 **발행만**(NFR-C1/RES-11(a)); 비용 상한 서킷은 **U6.CostGuardCircuitBreaker(시스템 전역)** — U1 논리 컴포넌트 아님.
- FD 잠금: 논문 단위 원자성(BR-7)·INV-1 커밋 순서(BR-8)·멱등 upsert(BR-9)·워터마크 max-clamp(BR-11)·이벤트 멱등(BR-12)·REBUILD_LOCK(BR-13)·tombstone(BR-14)·NFR-R1 부분 인덱싱 금지.

---

## 2. NFR Design 실행 계획 (Step 2 — 답변 확정 후, 체크박스)

> 산출물은 `aidlc-docs/construction/u1-ingestion/nfr-design/` 에 생성. **답변(§4) 전 미생성.**

- [x] **nfr-design-patterns.md** — 패턴 설계:
  - 복원력: 재시도(앱 레벨 scheduleRetry로 RES-9 엔벨로프 + SQS redrive=소진/포이즌 DLQ 백스톱)·서킷 브레이커(의존성별 정의 저하 = RES-1 의존성 맵)·멱등(ChunkId/이벤트 BR-12)·단일 writer 락(BR-13)·**비트랜잭션 _bulk 위 논문 단위 원자 커밋(verify-all-then-commit)**.
  - 확장성: 병렬 컨슈머 + 멱등 bulk upsert·arXiv 공유 레이트 리미터·백프레셔.
  - 성능: dedup-first → 배치 임베딩 → OpenSearch `_bulk`(NFR-C1).
  - 보안: 최소 권한 IAM(SEC-6)·at-rest/TLS(SEC-1)·시크릿(SEC-3)·SEC-10.
  - **RES-4[전역]**: CI/CD·롤백·배포. **RES-12**: 복원력 테스트(폴트 인젝션).
- [x] **logical-components.md** — 논리 컴포넌트 토폴로지·통합:
  - 컴포넌트: 워커(컴퓨트)·SQS(큐+DLQ)·EventBridge(스케줄)·**제어평면 상태 저장소**·S3(전문)·OpenSearch(인덱스)·Bedrock(임베딩); 워커→U6.ObservabilityHub 텔레메트리; **indexStats 헬스/통계 표면(RES-6/RES-2 재구축 검증)**.
  - FD 9 컴포넌트·3 서비스 → 논리 인프라 매핑. REBUILD_LOCK·Watermark·DedupState 저장 위치.
  - 통합 다이어그램 + 패턴 적용점.
- [x] **추적성** — 패턴/컴포넌트 → **RES-1**/2/4/5/6/7/8/9/**12**, SEC-1/3/6/9/10, NFR-C1/R1/O1, BR-*, PBT-08.

---

## 3. 가정 (잘못이면 §4/지적으로 정정)

- **DS-1**: **리전/AZ 토폴로지(RES-2)**·인스턴스 사이징·구체 IAM 정책 JSON·IaC·OpenSearch 샤드 수는 Infra Design.
- **DS-2**: RES-4(CI/CD)·IAM **방식**은 [전역] — U1에서 정하면 U2~U6 상속. 구체 파이프라인/정책은 Infra/Ops.
- **DS-3**: QT-3 신뢰성/저하 인수 평가셋은 U6 소유(ReliabilityEvalProbe); U1 RES-12는 **인제스천 워커 폴트 인젝션**으로 U6 평가에 공급(중복 아님).
- **DS-4**: 관측성 전송(워커→U6.ObservabilityHub)의 구체 이벤트 백본은 U6 NFR Requirements[전역]/Infra.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그; A/B/C/D 또는 E=기타)

### A. 복원력 패턴 (Resilience)

**Q1 — 재시도+DLQ 실현(RES-9 엔벨로프 + 이벤트 멱등 BR-12).**
- A) **앱 레벨 `scheduleRetry`가 RES-9 엔벨로프 실현**(타임아웃 ~10s·≤5회·지수 base 1s×2+지터; 수치=NFR Req §3); **SQS redrive/`maxReceiveCount`는 소진·포이즌 → DLQ 백스톱 전용**(가시성 타임아웃이 지수 곡선을 대체하지 않음). 이벤트 멱등 = DeduplicationGuard DUPLICATE **단일 백스톱**(이벤트-레벨 dedup 없음, BR-12), 처리 후 `ackEvent`. (권장)
- B) SQS 가시성 타임아웃만으로 재시도(엔벨로프 불일치).
- **권장**: A — BR-16/BR-12/FD §1.3 정합.
- **[Answer]**: A (앱 레벨 scheduleRetry로 RES-9 엔벨로프 구현 + SQS redrive를 DLQ 백스톱으로 활용)

**Q2 — 서킷 브레이커(의존성별) + 의존성 맵(RES-1/RES-9).**
- A) **의존성별 서킷 + 정의된 저하**(arXiv→잡 보류·경보; Bedrock→배치 보류·재시도; OpenSearch→쓰기 보류, 부분 인덱싱 금지 NFR-R1). 이 타임아웃/서킷/저하 표가 **RES-1 의존성 맵**(arXiv/Bedrock/OpenSearch) 산출물. (권장)
- B) SQS 재시도만(서킷 없음).
- **권장**: A — RES-9 정의된 저하 + RES-1 의존성 맵 + NFR-R1.
- **[Answer]**: A (의존성별 서킷 브레이커 + 정의된 저하 테이블을 RES-1 의존성 맵으로 구성)

**Q3 [전역] — RES-4: CI/CD + 롤백 + 배포 방식.**
- A) **GitHub Actions**(RES-3 git-flow) → 락파일/SCA/SBOM(SEC-10)·핀 이미지 빌드 → **컨테이너 레지스트리 푸시(구체 레지스트리는 Infra)** → IaC 배포; **롤백 = 직전 이미지 태그/IaC 리비전 재배포**. (권장)
- B) 다른 CI(CodePipeline 등). C) 수동(비권장).
- **권장**: A — RES-3 계승([[project-git-flow-setup]]). 컴퓨트 타깃·레지스트리는 Infra.
- **[Answer]**: CI는 Github Actions로 하되 CD 도구는 compute target이 정해진 Infra Design에서 확정, 특히 사용자 API(U2/U6)는 무중단 배포 필요성 때문에 CodeDeploy/rolling update를 별도 검토

**Q4 — RES-12: 복원력 테스트 방식.**
- A) **인제스천 워커 폴트 인젝션 스위트**: arXiv 타임아웃/에러·Bedrock 실패·OpenSearch 불가·포이즌 이벤트·**_bulk 부분 실패** 주입 → 재시도/DLQ/서킷/멱등/부분 인덱싱 금지(NFR-R1) 검증; U6 QT-3에 공급(DS-3). (권장)
- B) 수동 테스트만.
- **권장**: A — RES-12 + NFR-R1/PBT-08 자동 검증.
- **[Answer]**: A (자동화된 인제스천 워커 폴트 인젝션 테스트 스위트 도입)

### B. 정합성·원자성 패턴 (Correctness — 비트랜잭션 스토어)

**Q5 — 논문 단위 원자 커밋 실현(비트랜잭션 `_bulk` 위, NFR-R1/BR-7/BR-8).** OpenSearch `_bulk`는 **트랜잭션 아님**(부분 성공 가능) — 원자성은 **앱 레벨 불변식**.
- A) **verify-all-then-commit**: 한 논문의 전 ChunkSet을 `_bulk` 발행 → **모든 per-item 응답 검사** → **어느 하나라도 오류면 논문 전체 실패**(markIngested 미호출 → 재시도/DLQ, BR-15/16/17); 재시도 시 **ChunkId 키 멱등 upsert(BR-9/P3)**로 부분 적용분 재수렴(고아/중복 0); **CHANGED가 더 적은 청크면 잔여 stale ChunkId를 markIngested 전/함께 삭제**(고아 청크 방지). (권장)
- B) `_bulk` 성공 가정(부분 실패 무시 — NFR-R1 위반).
- **권장**: A — NFR-R1/BR-7/BR-8/INV-1을 스토어 속성이 아닌 **앱 검증으로 강제**. FD §1.1 step 10 정합.
- **[Answer]**: A (verify-all-then-commit: OpenSearch _bulk 응답의 전수 검사 및 실패 시 논문 단위 롤백/재시도 및 stale 청크 삭제)

**Q6 — 철회 tombstone 삭제 패턴(BR-14, per-paperId 삭제).** 삭제도 비원자적.
- A) **per-paperId 삭제**: `delete-by-query(paperId)` 또는 ChunkId 명시 bulk-delete; 부분 실패 시 Q5와 **동일 verify/재시도 게이트**(NFR-R1); **순서는 DeduplicationGuard.isNew로 강제**(더 새 vN upsert가 stale tombstone 우선, BR-14). (권장)
- B) 단순 delete(부분 실패·순서 미보장).
- **권장**: A — TD-4 요건(iii) per-paperId 멱등 삭제 충족.
- **[Answer]**: A (per-paperId 단위 멱등 삭제 및 DeduplicationGuard.isNew를 통한 순서 보장)

### C. 확장성 패턴 (Scalability)

**Q7 — 동시성 + 단일 writer 실현.**
- A) **병렬 fetch/parse/embed 컨슈머 + ChunkId 키 멱등 bulk upsert**(물리 동시 쓰기 안전, BR-9; 원자성은 Q5); **REBUILD_LOCK만 재구축↔증분/이벤트 배제**(BR-13). (권장)
- B) 완전 직렬(수십만 시드에 느림).
- **권장**: A — "단일 writer"는 논리 계약; 멱등 upsert로 물리 동시성 안전. 락은 재구축에만.
- **[Answer]**: A (병렬 컨슈머 + 멱등 bulk upsert 적용 및 REBUILD_LOCK 상호 배제)

**Q8 — arXiv 레이트 리밋 패턴(RES-8 쿼터).**
- A) **공유 토큰 버킷/예양 지연 리미터**(워커 전역) — 병렬화에도 arXiv 쿼터 글로벌 상한. (권장)
- B) 워커별 단순 지연(전역 상한 미보장).
- **권장**: A.
- **[Answer]**: A (공유 토큰 버킷/예양 지연 리미터를 통한 global arXiv 쿼터 상한 준수)

### D. 성능 패턴 (Performance)

**Q9 — 처리량 패턴.**
- A) **dedup-before-embed**(중복 단락, NFR-C1) → **배치 임베딩**(Bedrock) → **OpenSearch `_bulk`**(원자성은 Q5 앱 검증). (권장)
- B) 건별(비용·지연↑).
- **권장**: A.
- **[Answer]**: A (dedup-before-embed -> 배치 임베딩 -> OpenSearch _bulk)

### E. 보안 패턴 (Security)

**Q10 [전역] — 최소 권한 IAM(SEC-6).**
- A) **워커 전용 역할, 와일드카드 없음**: 지정 Bedrock 모델·OpenSearch 인덱스·S3 프리픽스·SQS·제어평면 저장소만. (권장; 구체 정책 JSON은 Infra)
- B) 광범위 권한(비권장).
- **권장**: A — SEC-6. [전역].
- **[Answer]**: A (워커 전용 역할 정의 및 와일드카드 제외)

**Q11 — 암호화 + 시크릿(SEC-1/3).**
- A) **관리형 at-rest 암호화(OpenSearch/S3/SQS/상태 저장소) + TLS** + 시크릿 Secrets Manager/SSM(env/로그 비노출 SEC-3). (권장)
- B) 직접 기술.
- **권장**: A.
- **[Answer]**: A (KMS 관리형 at-rest 암호화 + TLS + AWS Secrets Manager/SSM)

**Q12 — SEC-10 공급망 실현(CI).**
- A) **CI 락파일 검증 + SCA + SBOM + 이미지 다이제스트 핀 강제**(Q3 파이프라인 내). (권장)
- B) 일부만.
- **권장**: A.
- **[Answer]**: A (CI 락파일 검증 + SCA + SBOM + 베이스 이미지 다이제스트 핀 고정)

### F. 논리 컴포넌트 (Logical Components)

**Q13 [전역] — 제어평면 상태 저장소(Watermark·DedupState 지문·Job·REBUILD_LOCK).** _팀 피드백(2026-06-16) 반영 — 결정 기준은 "쓰기 처리량"이 **아니다**: U1 워커는 **단일 writer**(Q7)라 DynamoDB의 쓰기 처리량 강점은 무용. **진짜 기준 = 시스템에 관계형 DB(RDS/Aurora)가 이미 있는가.**_
- A) **DynamoDB** — **시스템에 RDS가 전혀 없을 때.** 조건부 쓰기로 REBUILD_LOCK(BR-13)·멱등(BR-9), 서버리스.
- B) **시스템 RDS/Aurora 재사용** — **U3/U4가 RDS를 쓸 때(가능성 높음: 계정·세션·저장검색·라이브러리·이력 = owner-scoped 관계형 CRUD).** 관리 데이터스토어 1개 절감(OpenSearch+S3+SQS+RDS로 충분, 5번째 회피·NFR-C1 부담↓); **Postgres advisory lock**으로 REBUILD_LOCK 깔끔, **unique-constraint/ON CONFLICT upsert**로 dedup 멱등.
- C) OpenSearch 내 메타 인덱스(부자연).
- **권장**: **B(시스템에 RDS 존재 시) · A(RDS 전무 시).** U3/U4 데이터스토어 미확정 → **최종 pin은 시스템 데이터스토어 인벤토리 확정 시(U3/U4 NFR Requirements 또는 Infra Design)로 보류**; 본 설계는 "**제어평면은 시스템 관계형 DB 재사용 우선, 없으면 DynamoDB**" 패턴으로 기록. [전역].
- **[Answer]**: B (시스템에 RDS/Aurora 존재 시 Postgres 재사용, 없을 시 DynamoDB 사용 패턴 정의)

**Q14 — 논리 컴포넌트 토폴로지 + 헬스 표면 확인.**
- A) **워커 · SQS(큐+DLQ) · EventBridge · 제어평면 저장소(Q13) · S3(전문·공개 차단) · OpenSearch(공유 인덱스) · Bedrock(임베딩)** + 워커→U6.ObservabilityHub 텔레메트리(임베딩 비용 포함) + **`indexStats`(docCount/vectorCount/lastWrite) 데이터플레인 헬스 표면**(U6.HealthCheckService.deepCheck RES-6·RES-2 재구축 검증); **워커 프로세스 liveness 프로빙은 Infra/Ops 보류**. (권장)
- B) 가감(직접 기술).
- **권장**: A — 스택 잠금 정합. 컴퓨트 타깃(ECS/Fargate vs Lambda)은 Infra.
- **[Answer]**: A (워커, SQS, S3, OpenSearch, Bedrock 매핑 및 indexStats 데이터플레인 헬스 표면 노출)

---

## 5. 다음 절차
1. 팀이 `§4` `[Answer]:` 채움(또는 "approve recommendations"). `[전역]`(Q3·Q10·Q13) 인지.
2. 모호 답변 시 후속 명확화.
3. 답변 확정 → `§2` 산출물 생성(nfr-design-patterns.md / logical-components.md).
4. 완료 메시지 + 리뷰 게이트 → 승인 시 다음 단계(**Infrastructure Design** — AWS 자원·**리전/AZ 토폴로지(RES-2)**·IaC·사이징·구체 IAM).

> 본 계획·질문은 **리뷰 게이트**입니다. 답변 전까지 산출물 미생성, 미커밋.
