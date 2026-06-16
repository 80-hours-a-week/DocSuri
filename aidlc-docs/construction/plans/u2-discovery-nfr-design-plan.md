# u2-discovery-nfr-design-plan.md — NFR Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Design (유닛별 루프, U2) · **유닛**: U2 Discovery · **트랙**: Track 3(@kyjness) · **일자**: 2026-06-16
**근거**: `construction/u2-discovery/nfr-requirements/`(NFR 목표·스택) · `construction/u2-discovery/functional-design/`(FD 답변 A·INV-1) · `requirements.md`(NFR-P1/C1/R2, SEC, QT) · U1 `nfr-design/`(패턴 선례)
**목적**: U2 NFR 요구사항을 **설계 패턴 + 논리 컴포넌트**로 구체화. 보류된 RES-4(CI/CD·롤백·배포)·RES-12(복원력 테스트)를 본 단계에서 확정.
**고도(altitude)**: **패턴·논리 컴포넌트·정책**. 리전/AZ(RES-2)·IaC·배포 타깃(ECS/Lambda)·**수치 실측(타임아웃 ms·TTL·동시성)**·구체 캐시 스토어는 **Infra Design**.

> **계승**: FastAPI(⏳ app-shell 합의 전제)·Python·Cohere `search_query`·OpenSearch·앱 레벨 RRF·임베딩 캐시·NFR-C1 $1600·mock-first 2구현. **INV-1**(U2 enforce 미호출, U6 단일 권위)·**INV-3**(fail-closed)는 설계 불변.

---

## 1. 유닛 컨텍스트 (NFR Design 렌즈)

- U2 = backend 모놀리스(배포 ①) 내 **동기 검색 읽기 모듈**. NFR-P1 주 대상.
- **핵심 설계 동인**: NFR-P1(레이턴시 예산·캐시·병렬 검색) · RES-9/NFR-R2(의존성 격리·폴백) · NFR-C1(임베딩 캐시·degradeMode 조회) · SEC(검증·비노출·fail-closed 패턴 위치) · QT-3(저하 검증) · RES-4/RES-12(보류 확정).
- **단일 권위 경계(불변)**: 근거화 enforce·비용 판정·레이트리밋·인증 = U6/게이트웨이. U2는 포트 소비·도메인 검증·저하 폴백만.
- **NFR Req 결정 계승**: 앱 레벨 RRF·PaperId 디덥 · 임베딩 캐시(TTL) · stateless 수평 확장 · 임베딩장애→lexical 폴백 / 인덱스장애→fail-closed.

---

## 2. NFR Design 실행 계획 (Step 2 — 답변 확정 후, 체크박스)

> 산출물은 `aidlc-docs/construction/u2-discovery/nfr-design/` 에 생성. **§4 답변 전 미생성.**

- [x] **nfr-design-patterns.md** — 패턴 확정:
  - **복원력**: 동기 경로 fail-fast + 폴백(§4 Q1)·의존성별 서킷(§4 Q2)·임베딩장애→lexical / 인덱스장애→fail-closed·degradeMode(U6) vs dependency 서킷 구분.
  - **성능**: 임베딩 read-through 캐시(§4 Q3)·k-NN∥BM25 병렬 검색(§4 Q4)·async I/O·레이턴시 예산 분해(U2 단계 + U6 근거화 별도).
  - **확장성**: stateless + 수평 확장·공유 캐시/서킷 상태(§4 Q5).
  - **보안**: SEC-5/9/15 계층 분리 + 게이트웨이 방어심층(§4 Q6).
  - **배포/테스트**: CI=GHA·CD/배포 Infra(§4 Q8, RES-4)·폴트 인젝션 스위트(§4 Q9, RES-12).
  - 추적성 매트릭스(패턴↔NFR/BR/PBT/검증).
- [x] **logical-components.md** — 논리 컴포넌트·토폴로지(§4 Q7):
  - FastAPI U2 라우터 + 검색 어댑터(opensearch-py) + 임베딩 어댑터(Bedrock) + 임베딩 캐시 + 포트(Grounding/Cost/Observability via U6) + mock/real DI.
  - FD 7컴포넌트 ↔ 논리 컴포넌트 매핑(재계수 아님).
  - 동기 읽기 데이터플레인 + 비차단 이벤트(SearchExecuted) 경계.

---

## 3. 가정 (잘못이면 §4 또는 지적으로 정정)

- **DS-1**: 리전/AZ(RES-2)·IaC·배포 타깃(ECS/Fargate vs Lambda)·**수치 실측(타임아웃·재시도 횟수·TTL·동시성)**·구체 캐시 스토어(Redis/ElastiCache vs 인메모리)는 **Infra Design**(본 단계는 패턴·정책·범위).
- **DS-2**: 근거화 enforce 메커니즘·레이턴시는 **U6 소관**(종단 NFR-P1의 의존성). U2는 포트 소비 + 개발 스텁.
- **DS-3 [backend-shared]**: FastAPI·CI 파이프라인·CD/무중단 배포는 **app-shell(@ELSAPHABA) 공유** — U2 제안 + 합의.
- **DS-4**: NFR-P1 **수치 실측**은 Build & Test/Infra. 본 단계는 예산 분해·패턴.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그; A/B/C/D 또는 E=기타)

### A. 복원력 패턴 (Resilience)

**Q1 — 동기 경로 재시도 자세(NFR-P1 vs RES-9).** P50<3s 예산에서 외부 호출(Bedrock 임베딩·OpenSearch) 실패 시?
- A) **fail-fast + 폴백 우선(재시도 0~최소)**: 임베딩 타임아웃→**즉시 lexical-only 폴백**(저하), OpenSearch 타임아웃→**fail-closed**. 재시도로 레이턴시 예산 잠식 안 함. (권장)
- B) 짧은 1회 재시도(지터) 후 폴백.
- C) 기타.
- **권장**: A — 동기 사용자 경로는 **fail-fast가 NFR-P1 우선**; 재시도는 레이턴시 위험. 폴백(lexical/fail-closed)이 신뢰성 메커니즘. 수치는 Infra(DS-1).
- **[Answer]**: A

**Q2 — 서킷 브레이커 범위.** 의존성 장애 격리(RES-9)?
- A) **의존성별 서킷**(per-dependency): Bedrock 임베딩 서킷 OPEN→**lexical-only 폴백**; OpenSearch 서킷 OPEN→**fail-closed**. **비용 degradeMode(U6, NFR-C1)와 별개**(이건 장애 격리). (권장)
- B) 단일 글로벌 서킷.
- C) 기타.
- **권장**: A — RES-9 의존성 격리(U1 패턴 정합). **degradeMode(비용·U6 조회) ≠ dependency 서킷(장애·U2)** 명확 구분.
- **[Answer]**: A

### B. 성능 패턴 (Performance)

**Q3 — 임베딩 캐시 패턴(TD-U2-7).**
- A) **read-through 캐시**(정규화 질의(NFC) 키 → 임베딩 벡터, **명시 TTL**; 미스 시 Bedrock 호출 후 적재). 스토어는 Infra. (권장)
- B) 캐시 없음(매 요청 임베딩).
- C) 기타.
- **권장**: A — NFR-P1(캐시 히트 시 임베딩 레이턴시 0)·NFR-C1(중복 임베딩 회피). 캐싱 규약(미스 시 원본·TTL 필수). 키=정규화 질의(BR-2 NFC 결정성과 정합).
- **[Answer]**: A

**Q4 — k-NN/BM25 병렬 발행(NFR-P1).** 하이브리드 두 검색의 실행?
- A) **병렬 발행**(k-NN + BM25 동시 → 앱 RRF 병합) — async로 레이턴시 단축. (권장)
- B) 순차.
- C) 기타.
- **권장**: A — async I/O로 두 검색 대기 중첩, NFR-P1 예산 절감. (OpenSearch `_msearch` 또는 동시 요청; 구체는 어댑터 구현.)
- **[Answer]**: A

### C. 확장성 패턴 (Scalability)

**Q5 — 캐시/서킷 상태 공유(NFR-S1 수평 확장).** stateless 모듈 다중 인스턴스에서 임베딩 캐시·서킷 상태?
- A) **공유 외부 캐시/상태**(인스턴스 간 공유) — 캐시 히트율·서킷 일관성. 스토어는 Infra. (권장)
- B) 인스턴스 로컬(인메모리) — 단순하나 히트율↓·서킷 불일치(소규모 NFR-S1엔 허용 가능).
- C) 기타.
- **권장**: A — 수평 확장 시 공유 상태가 히트율·서킷 일관성에 유리. **단 NFR-S1(~50 동시) 소규모라 비용/복잡도상 B 폴백 허용** — 최종 stand는 Infra trade-off. (권장 A, B 폴백 명시.)
- **[Answer]**: A

### D. 보안 패턴 (Security)

**Q6 — SEC-5/9/15 패턴 위치.** U2 모듈 내 보안 패턴 배치?
- A) **계층 분리 + 방어심층**: 진입 `QueryValidator`(SEC-5 검증/새니타이즈) · 출력 `ResultAssembler`(SEC-9 비노출 필터) · **전역 예외 핸들러(FastAPI exception_handler)** (SEC-15 일반화·fail-closed). U6 게이트웨이 InputValidationGuard와 **이중(defense-in-depth)**. (권장)
- B) 게이트웨이(U6)만 의존.
- C) 기타.
- **권장**: A — SEC-11 격리·방어심층. 게이트웨이 검증 + U2 도메인 검증 이중. 전역 핸들러로 스택/내부 비노출(INV-3).
- **[Answer]**: A

### E. 논리 컴포넌트 (Logical Components)

**Q7 — U2 논리 컴포넌트 토폴로지.**
- A) **FastAPI U2 라우터 + SearchAdapter(opensearch-py, k-NN∥BM25) + EmbeddingAdapter(Bedrock search_query) + EmbeddingCache + Ports(Grounding/Cost/Observability→U6) + mock/real DI 토글**. backend 모놀리스 내 모듈(app-shell 마운트). (권장)
- B) 기타.
- **권장**: A — NFR Req 스택·mock-first(MR-1~4)·INV-1 정합. FD 7컴포넌트↔논리 컴포넌트 매핑 명시.
- **[Answer]**: A

### F. 배포 · 복원력 테스트 (보류 확정)

**Q8 [backend-shared] — CI/CD·배포 방식·롤백(RES-4).**
- A) **CI=GitHub Actions**(빌드·린트·테스트·SCA·SBOM; RES-3 git-flow 계승). **CD/배포 방식·무중단(blue-green/rolling)·롤백은 Infra Design**(backend 공유 — 사용자 대면 API라 무중단 지향 계층 분리). 롤백=이전 이미지 다이제스트/IaC 리비전. (권장)
- B) 기타.
- **권장**: A — U1 RES-4 패턴 정합. **⚠️ backend 공유 CD — app-shell/Infra 조율**(U2 단독 아님).
- **[Answer]**: **A — CI=GHA 확정(U2). ⚠️ CD/무중단 배포·롤백은 backend 공유 → app-shell(@ELSAPHABA)/Infra 합의 전제**(잠정).

**Q9 — 복원력 테스트(RES-12).** U2 우아한 저하·폴백 검증?
- A) **폴트 인젝션 스위트**: Bedrock 임베딩 타임아웃/장애→lexical 폴백 검증 · OpenSearch 장애→fail-closed 검증 · degradeMode 토글(getBudgetState 스텁)→저하 배너 · 빈/기권 경로. **QT-3(신뢰성/저하)와 연동**. (권장)
- B) 기타.
- **권장**: A — U1 RES-12 정합. QT-3 시나리오를 폴트 인젝션으로 실증(실행은 Build&Test/Operations).
- **[Answer]**: A

---

## 5. 다음 절차

1. `§4`의 `[Answer]:` 태그를 채운다(또는 채팅으로 회신). 모호 답변 시 후속 질문(Step 5).
2. **[backend-shared] Q8**(및 FastAPI 전제)은 app-shell 소유자/Infra 조율 표시.
3. 답변 확정 → `§2` 산출물 생성(`u2-discovery/nfr-design/` nfr-design-patterns·logical-components + 추적성).
4. 완료 메시지 + 리뷰 게이트 → 승인 시 **Infra Design**(또는 트랙 합의에 따라 U2 Code Generation 선행 — mock-first로 코드 착수 가능).

> 본 계획·질문은 **리뷰 게이트**입니다. 답변 전까지 NFR Design 산출물을 생성하지 않으며, 아직 커밋하지 않았습니다.
