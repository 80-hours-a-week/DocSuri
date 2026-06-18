# u7-summarization-nfr-design-plan.md — NFR Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Design (유닛별 루프, U7) · **유닛**: U7 Summarization · **트랙**: 단일 트랙 · **일자**: 2026-06-19
**근거**: `construction/u7-summarization/nfr-requirements/`(NFR 목표·TD-S1~S12) · `construction/u7-summarization/functional-design/`(FD 답변·BR-S1~S14·INV) · `requirements.md`(NFR-P2/C1·QT-5·RES-9·NFR-R2·SEC) · U2/U3 `nfr-design/`(패턴 선례)
**목적**: U7 NFR 요구사항을 **설계 패턴 + 논리 컴포넌트**로 구체화. real-first(mock 대역 없음) 하의 복원력·성능·보안 패턴, 스트리밍↔근거화 패턴 정밀화, CI 레인·복원력 테스트 확정.
**고도(altitude)**: **패턴·논리 컴포넌트·정책**. 리전/AZ·IaC·배포 타깃·**수치 실측(타임아웃 ms·TTL·토큰 캡·동시성·서킷 임계)**은 **Infra Design/Code-gen**.

> **계승**: Python·FastAPI·Bedrock(Sonnet/Haiku 스트리밍)·S3+Redis·RDS(개인 용어집)·정규식 섹션 도출·비동기 잡 fast-follow·Hypothesis·NFR-C1 $1,600. **real-first**(포트 + 실 어댑터 단일본, Production Mock Adapter 미구현·단위 Fixture/Stub 허용). **불변식**: INV-1(C-2 추출 경계)·INV-2(비용/관측 U6 단일 권위)·INV-3(SEC-9)·INV-4(fail-closed)·INV-5(캐시 키 immutable).

---

## 1. 유닛 컨텍스트 (NFR Design 렌즈)

- U7 = backend 모놀리스(배포 ①) 내 **온디맨드 요약/번역 모듈**. NFR-P1 비대상(NFR-P2).
- **핵심 설계 동인**: NFR-P2(캐시 우선·스트리밍 TTFB) · RES-9/NFR-R2(Bedrock 의존성 격리·기권 폴백) · NFR-C1(distinct×1·CostGuard 조회) · QT-5(근거화 결정적 게이트) · SEC(검증·인젝션·비노출·fail-closed·개인 용어집 격리) · CI/복원력 테스트.
- **단일 권위 경계(불변)**: 비용 판정·관측·레이트리밋·인증 = U6/게이트웨이. 근거화는 **U7 고유 결정적 게이트**(검색용 enforce와 별개·BR-S7).
- **NFR Req 결정 계승**: 캐시 read/write-through(S3+Redis) · 버퍼-검증-스트리밍 · Bedrock 타임아웃/재시도(1)/서킷→기권 · 전문 부재→초록 폴백 · stateless 수평 확장.

---

## 2. NFR Design 실행 계획 (Step 2 — 답변 확정 후, 체크박스)

> 산출물은 `aidlc-docs/construction/u7-summarization/nfr-design/` 에 생성. **§4 답변 전 미생성.**

- [x] **nfr-design-patterns.md** — 패턴 확정:
  - **복원력**: Bedrock 타임아웃+1회 재시도+서킷→기권(§4 Q1)·근거화 1차 실패→1회 재시도→기권(§4 Q2)·**비용 degradeMode(U6) ≠ 의존성 서킷(장애) ≠ 소스 저하(초록 폴백)** 3계층 구분(§4 Q3).
  - **성능**: 캐시 우선 read-through/write-through(§4 Q4)·**스트리밍↔근거화 패턴**(버퍼-검증-점진렌더, §4 Q5)·async I/O·캐시 HIT가 TTFB 주 경로.
  - **확장성**: stateless + 공유 외부 캐시 상태(§4 Q6)·Bedrock 동시성/쿼터 관리(§4 Q7).
  - **보안**: 진입 검증 + 본문 격리(인젝션) + 출력 SEC-9 필터 + 전역 fail-closed + 개인 용어집 owner 스코프 방어심층(§4 Q8).
  - **배포/테스트**: CI=GHA U7 레인(단위 Fixture/Stub + 통합 실 의존성 게이트)·복원력 폴트 인젝션(§4 Q10).
  - 추적성 매트릭스(패턴↔NFR/BR/PBT/검증).
- [x] **logical-components.md** — 논리 컴포넌트·토폴로지(§4 Q9):
  - FastAPI U7 라우터 + 어댑터(BedrockLlmGateway 스트리밍·S3+Redis SummaryStore·S3 FullTextSource·RDS GlossaryRepo) + GroundingValidator(U7 결정적) + Ports(Cost/Observability→U6) + 실 어댑터 단일본(+테스트 Fixture/Stub).
  - FD 9컴포넌트 ↔ 논리 컴포넌트 매핑(재계수 아님). 온디맨드 데이터플레인 + 비차단 텔레메트리 경계.

---

## 3. 가정 (잘못이면 §4 또는 지적으로 정정)

- **DS-1**: 리전/AZ·IaC·배포 타깃·**수치 실측(타임아웃·재시도 백오프·TTL·토큰 캡·서킷 임계·동시성)**은 **Infra Design/Code-gen**(본 단계는 패턴·정책·범위).
- **DS-2 [U6 위임]**: 비용 판정·관측·레이트리밋·인증은 U6/게이트웨이. U7은 포트 소비. (근거화는 U7 고유 결정적 게이트 — BR-S7.)
- **DS-3 [backend-shared]**: FastAPI·CI 파이프라인·CD/무중단 배포는 app-shell(@ELSAPHABA) 공유 — U7 제안 + 합의.
- **DS-4 (real-first)**: 출하 코드 = 실 어댑터 단일본(Production Mock Adapter 없음). 단위 테스트 Fixture/Stub 허용·통합 테스트 실 의존성.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그; A/B/C/D 또는 X) 기타)

> 답변 방법: 각 `**[Answer]**:` 뒤에 **A/B/C/D** 또는 **X) 기타: 직접 기술**. 모호 답변엔 후속 질문(Step 5).

### A. 복원력 패턴 (Resilience)

**Q1 — Bedrock 호출 복원력 자세(RES-9/NFR-R2).** 생성 LLM 호출 장애/타임아웃 시?
- A) **명시 타임아웃 + 1회 재시도(백오프) + 서킷브레이커 → 기권**(저하 모드, FR-11). 캐시 HIT 경로(LLM 0콜)는 영향 없음(격리). 재시도 1회로 폭주 방지. **수치는 Infra/Code-gen.** (권장)
- B) 재시도 없이 즉시 기권.
- C) 다회 재시도(지수 백오프).
- X) 기타.
- **권장**: A — RES-9 의존성 격리·NFR-R2 우아한 저하. 온디맨드라 약간의 재시도 여유(검색 동기 경로와 달리 SLA 비대상). 근거 없는 출력보다 기권(fail-closed).
- **[Answer]**: A

**Q2 — 근거화 실패 재시도 패턴(BR-S7).** 결정적 게이트(앵커/수치/스키마) 1차 실패 시?
- A) **1회 재시도(재생성) → 그래도 실패 시 기권**(fail-closed). 정당한 코퍼스밖 abstain은 재시도 없음. LLM 장애 재시도(Q1)와 **구분**(별도 카운트). (권장)
- B) 재시도 없이 즉시 기권.
- X) 기타.
- **권장**: A — 설계 입력 §7.1·BR-S7. 1회 재시도로 일시적 생성 변동 흡수, 폭주 방지. 근거화 재시도와 의존성 장애 재시도는 의미가 달라 분리.
- **[Answer]**: A

**Q3 — 저하 3계층 구분(NFR-C1 vs RES-9 vs NFR-R2).** 비용·장애·소스부재를 어떻게 분리?
- A) **3계층 명확 구분**: ① **비용 degradeMode**(U6 CostGuard 조회 → `CostDegradedDTO`, 비용) ② **의존성 서킷**(Bedrock 장애 → 기권, 장애) ③ **소스 저하**(전문 부재 → 초록 폴백, 가용 데이터). 각기 다른 종단 상태·텔레메트리. (권장)
- B) 단일 "저하" 상태로 통합.
- X) 기타.
- **권장**: A — 운영 신호(RES-11) 구분·종단 union(BR-S9) 정합. 셋은 원인·행동이 다름(비용=일시중단/장애=기권/소스부재=폴백 또는 SourceUnavailable).
- **[Answer]**: A

### B. 성능 패턴 (Performance)

**Q4 — 캐시 패턴(NFR-P2/§11).** 2단 캐시 동작?
- A) **read-through(Redis→S3) + write-through(S3 영구 + Redis 핫)**, 키=immutable `SummaryCacheKey`. 캐시 HIT = LLM 0콜 즉시(TTFB 주 경로). 무효화 = 키 변경(자동). TTL/라이프사이클 수치는 Infra. (권장)
- B) 단일 계층(영구만 또는 핫만).
- X) 기타.
- **권장**: A — 설계 입력 §11·NFR-P2. 핫(Redis) 즉시·영구(S3) 진실원본·키 immutable로 stale 없음.
- **[Answer]**: A

**Q5 — 스트리밍 ↔ 근거화 패턴 정밀화(BR-S8/FR-5).** §3 구조화 JSON(앵커 포함)은 완성돼야 근거화(앵커/수치/스키마) 가능 — 첫 생성 스트리밍을 어떻게?
- A) **생성-버퍼-검증-점진렌더**: 생성은 내부 스트리밍(liveness·타임아웃 관리)으로 받되 **완성 draft를 근거화 통과한 뒤 클라이언트에 점진 렌더**(통과 필드부터). 근거 없는 토큰 유출 0(FR-5 최우선). 첫 생성 TTFB는 생성+검증에 종속(캐시 HIT가 즉시 경로). (권장)
- B) 필드 완성 즉시 점진 검증·렌더(부분 앵커 검증) — TTFB↑이나 복잡·부분 검증 리스크.
- C) 비스트리밍(완성 후 일괄).
- X) 기타.
- **권장**: A — 구조화 출력은 앵커/스키마가 전체 draft에 의존 → 완성 후 검증이 안전(FR-5 날조 0 절대 우선). 체감은 캐시 HIT(주 경로)·내부 스트리밍 liveness로 관리. 구체 버퍼/부분렌더 전략 수치는 Code-gen.
- **[Answer]**: A

### C. 확장성 패턴 (Scalability)

**Q6 — 캐시/상태 공유(수평 확장).** stateless 다중 인스턴스에서 캐시/상태?
- A) **공유 외부 스토어**(S3+Redis 인스턴스 간 공유) — 캐시 히트율·일관성. 로컬 인메모리 상태 없음(stateless). (권장)
- B) 인스턴스 로컬 캐시 병행.
- X) 기타.
- **권장**: A — S3/Redis는 본디 외부 공유. stateless 수평 확장 자연 정합. 키 immutable로 일관성 보장.
- **[Answer]**: A

**Q7 — Bedrock 동시성/쿼터 관리(NFR-C1/가용성).** 온디맨드 LLM 호출 부하?
- A) **async I/O + 계정 쿼터 내 동시 호출 + 초과 시 큐잉/저하**(ThrottlingException → 백오프/기권). 쿼터·동시성 수치는 Infra. 비용 상한은 U6 CostGuard. (권장)
- B) 무제한 동시 호출.
- X) 기타.
- **권장**: A — Bedrock 쿼터는 가용성/비용 경계. async로 외부 대기 중첩. 스로틀링은 복원력(Q1) 경로로 흡수.
- **[Answer]**: A

### D. 보안 패턴 (Security)

**Q8 — 보안 패턴 위치(SEC-3/8/9/11 + 인젝션 + 개인 용어집).**
- A) **방어심층 계층 분리**: 진입 `SummarizationController`(요청 검증) · `InputRefiner` **본문 격리**(`[지시]┃[데이터]<paper>` 인젝션 방어) · `ResultAssembler` **SEC-9 비노출 필터** · **전역 예외 핸들러(fail-closed, INV-4)** · `GlossaryRepo` **owner 스코프**(개인 용어집 격리, SEC-8) · 원문/번역 로깅 PII 정책(SEC-3). **위임**: 인증·레이트리밋=U6 게이트웨이(이중 방어). (권장)
- B) 게이트웨이(U6)만 의존.
- X) 기타.
- **권장**: A — SEC-11 비용 기능 방어심층. 인젝션 방어는 U7 본문 격리 고유 책임. 개인 용어집 owner 스코프는 cross-user 누출 차단.
- **[Answer]**: A

### E. 논리 컴포넌트 (Logical Components)

**Q9 — U7 논리 컴포넌트 토폴로지.**
- A) **FastAPI U7 라우터 + BedrockLlmGatewayAdapter(스트리밍 Sonnet/Haiku) + SummaryStoreAdapter(S3+Redis) + FullTextSourceAdapter(S3 read) + GlossaryRepository(RDS) + GroundingValidator(U7 결정적) + Ports(Cost/Observability→U6) + 실 어댑터 단일본(+테스트 Fixture/Stub)**. backend 모놀리스 내 모듈(app-shell 마운트·게이트웨이 경유). FD 9컴포넌트↔논리 컴포넌트 매핑. (권장)
- B) 기타.
- **권장**: A — NFR Req 스택(TD-S1~S12)·real-first·INV 정합. 온디맨드 데이터플레인 + 비차단 텔레메트리 경계 명시.
- **[Answer]**: A

### F. 배포 · 복원력 테스트

**Q10 [backend-shared] — CI 레인 + 복원력 테스트(real-first).**
- A) **CI=GitHub Actions U7 레인**: 단위(pytest, **테스트 Fixture/Stub** + Hypothesis PBT-S1~S5) + ruff + shared 드리프트 가드 **항상 실행**; **통합 테스트(실 Bedrock/S3/Redis/RDS)는 별도 게이트 레인**(자격증명 필요 — Infra 구성, PR 게이트 또는 수동/주기). **복원력 폴트 인젝션**: Bedrock 장애→기권 · 전문 부재→초록 폴백 · 비용 OPEN→CostDegraded · 근거화 실패→기권 · 인젝션 입력→격리(QT-5/RES-12 연동). CD/무중단·롤백은 Infra. (권장)
- B) 기타.
- **권장**: A — real-first라 단위는 Fixture/Stub로 CI 결정성 확보, 실 통합은 자격증명 필요해 별도 게이트(CI 비용·비결정성 관리). 폴트 인젝션으로 저하/기권 실증. **⚠️ backend 공유 CI/CD — app-shell/Infra 조율**.
- **[Answer]**: A

---

## 5. 다음 절차

1. `§4`의 `[Answer]:` 태그를 채운다(또는 채팅으로 회신). 모호 답변 시 후속 질문(Step 5).
2. **[backend-shared] Q10**(및 FastAPI 전제)은 app-shell 소유자/Infra 조율 표시.
3. 답변 확정 → `§2` 산출물 생성(`u7-summarization/nfr-design/` nfr-design-patterns·logical-components + 추적성).
4. 완료 메시지 + 리뷰 게이트 → 승인 시 **U7 Infrastructure Design**(또는 기존 인프라 재사용이 커 경량 — 비용 라인·S3 prefix·RDS 테이블·Redis 키스페이스·CI 자격증명; 트랙 판단).

> 본 계획·질문은 **리뷰 게이트**입니다. 답변 전까지 NFR Design 산출물을 생성하지 않으며, 아직 커밋하지 않았습니다.
