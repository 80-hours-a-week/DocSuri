# u7-summarization-nfr-requirements-plan.md — NFR Requirements 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Requirements (유닛별 루프, U7) · **유닛**: U7 Summarization · **트랙**: 단일 트랙 · **일자**: 2026-06-19
**근거**: `construction/u7-summarization/functional-design/`(FD 산출물·17문 답변 확정: A 14·B 1·X 2) · `requirements.md`(FR-12~14·NFR-P2·NFR-C1·QT-5·RES-9·NFR-R2·SEC) · 설계 입력 §2·§8·§11·§12 · U1/U2/U3 `tech-stack-decisions.md`(전역 계승) · `construction/infrastructure-design/infrastructure-design.md`(기존 인프라)
**목적**: U7 비기능 요구사항 확정 + **기술 스택 바인딩**(FD가 NFR로 이연한 모델 식별자·Bedrock·S3/Redis·토큰 캡·TTFB·개인 용어집 영속화). **real-first 구현 전제**(mock 대역 없음, Q10/Q11) 하의 의존성·테스트 전략 확정.
**고도(altitude)**: **스택 종류 + NFR 목표(정책 형태)**. 리전/AZ·IaC·배포 타깃·비동기 잡 인프라 상세는 **Infra Design**; CI/CD·복원력 테스트·구체 서킷 수치는 **NFR Design**; TTFB·토큰 캡 **수치 실측/튜닝**은 Build & Test/Code-gen.

> **[전역 계승](재결정 아님)**: 시스템 전역 PIN 결정을 U7이 상속 — **backend 런타임=Python · 웹 프레임워크=FastAPI(app-shell 기존 자산) · LLM 게이트웨이=AWS Bedrock · NFR-C1=$1,600/월(시스템 전역 상한) · 영속화=RDS PostgreSQL·핫캐시=ElastiCache Redis·오브젝트=S3(전부 프로덕션 배포 완료) · PBT=Hypothesis**. 해당 질문엔 `[전역 계승]` 표기.
> **[U6 위임](단일 권위)**: 비용 게이트(`get_budget_state`)·관측(`emit*`)·레이트리밋(게이트웨이)·인증/인가(게이트웨이/U3)는 U6/게이트웨이 소관 — U7은 소비만.
> **real-first**: FD Q10/Q11로 LLM·스토어 어댑터는 **포트 유지 + 첫 구현부터 실 어댑터(Bedrock·S3·Redis), mock/인메모리 대역 미구현**. 따라서 본 단계의 "병렬 개발(mock)" 카테고리는 **실 의존성 구성·테스트 전략**(§4-G)으로 대체.

---

## 1. 유닛 컨텍스트 (NFR 렌즈)

- U7 = **온디맨드 요약/번역 API 모듈**(배포 ① backend 모놀리스 내). 결과 카드의 보조 액션 — 검색 SLA(NFR-P1) **비대상**, **NFR-P2**(캐시 히트 즉시 / 첫 생성 스트리밍 TTFB).
- **U7 핵심 NFR 동인**:
  - **NFR-P2(온디맨드)** — 캐시 HIT = 즉시(LLM 0콜), 첫 생성 = 스트리밍 빠른 TTFB. 첫 생성 자체는 수십 초 가능(Sonnet 풀논문) → **스트리밍·캐시가 체감 관리**. 초장문(map-reduce)만 비동기 잡.
  - **NFR-C1(시스템 전역 $1,600/월)** — U7 슬라이스 = **"열어본 distinct 논문 × 1회"**(온디맨드 + 영구저장). 요약 Sonnet(건당 ≈$0.1~0.2)·번역 Haiku(≈$0.01~0.02). 신규 비용 라인(별도 텔레메트리 계상). U6 CostGuard 게이트.
  - **RES-9 / NFR-R2** — Bedrock 호출 명시 타임아웃·재시도(1회, BR-S7)·서킷 → 저하 모드 = 기권(FR-11). 전문 부재 → 초록 폴백.
  - **QT-5** — 요약/번역 근거화(날조 0·기권·앵커). U7 `GroundingValidator` 결정적 게이트 출력 표면 제공(평가 실행=U6/OP).
- **FD 잠금(답변)**: 모델 정책 task→tier·선택기 비노출(BR-S5)·캐시 키 immutable(BR-S1)·정제 보존 경계(BR-S3)·용어집 2경로(BR-S4)·U7 고유 결정적 근거화(BR-S7)·버퍼-검증-스트리밍(BR-S8)·종단 4-union(BR-S9)·**real-first(Q10/Q11)**.

---

## 2. NFR Requirements 실행 계획 (Step 2 — 답변 확정 후, 체크박스)

> 산출물은 `aidlc-docs/construction/u7-summarization/nfr-requirements/` 에 생성. **§4 답변 전 미생성.**

- [x] **nfr-requirements.md** — U7 NFR 확정:
  - 성능(**NFR-P2**: 캐시 HIT 즉시·첫 생성 스트리밍 TTFB 목표 형태·콜드스타트 가정), 확장성(stateless 수평 확장·LLM 동시 호출·Bedrock 쿼터), 가용성/신뢰성(Bedrock 의존성 격리·타임아웃/재시도/서킷·기권 폴백).
  - 비용(**NFR-C1 U7 라인** = distinct 논문×1·모델별 토큰 비용·영구저장 bounded·CostGuard 게이트).
  - 보안: SEC-8 인가(게이트웨이/U3 위임)·SEC-11 레이트리밋(게이트웨이)·SEC-9 비노출·**프롬프트 인젝션 방어(본문 격리)**·SEC-3(원문/번역 로깅 PII 정책)·**개인 용어집 owner 격리**.
  - 관측성(NFR-O1: 토큰·비용·지연·persona·task → ObservabilityHub), 유지보수성(PBT·모노레포 빌드).
  - 테스트(QT-5 근거화 평가셋 표면·PBT-S1~S5·**real-first 통합 테스트 전략**).
- [x] **tech-stack-decisions.md** — ADR 형식(결정·근거·대안·전환 비용):
  - **[전역 계승]**: Python·FastAPI·Bedrock·RDS PostgreSQL·ElastiCache Redis·S3·NFR-C1·Hypothesis.
  - **U7 고유**: 모델 바인딩(Sonnet 4.6 요약/Haiku 4.5 번역)·Bedrock 스트리밍 호출 메커니즘·요약 스토어(S3+Redis 키/TTL)·개인 용어집 영속화 위치·섹션 도출 메커니즘·토큰 캡/map-reduce 임계·비동기 잡 v1 범위·재현성 추출(정규식+LLM).
- [x] **real-first 의존성·테스트 경계** — 포트 + 실 어댑터 단일본; 통합 테스트(실 Bedrock/S3/Redis 또는 테스트 픽스처 한정 단위 테스트); CI 자격증명/엔드포인트 구성(Infra 연계).
- [x] **추적성** — NFR/스택 결정 → NFR-P2/C1, QT-5, RES-9/NFR-R2, SEC-3/8/9/11, FR-11~14, US-S1~S6 역추적.

---

## 3. 가정 (잘못이면 §4 또는 지적으로 정정)

- **NS-1**: 리전/AZ·IaC·배포 타깃·비동기 잡 워커 인프라 상세는 Infra Design. 구체 서킷/타임아웃 수치·CI/CD·복원력 테스트는 NFR Design. TTFB·토큰 캡 **수치 실측**은 Build & Test/Code-gen.
- **NS-2 [전역 계승]**: Python·FastAPI·Bedrock·RDS·Redis·S3·NFR-C1·Hypothesis는 시스템 전역 확정 — **U7 재논의 아님**(계승·정합만 확인).
- **NS-3 [U6 위임]**: 비용 게이트·관측·레이트리밋·인증/인가는 U6/게이트웨이 단일 권위. U7은 포트 소비. Bedrock 비용/지연은 NFR-C1/P2 동인이나 게이트 판정은 U6.
- **NS-4 (real-first)**: mock/인메모리 대역 없음. real 어댑터 가동은 기존 프로덕션 인프라(S3·ElastiCache·Bedrock·RDS) 위에서(이미 배포). 테스트는 실 통합 또는 테스트 픽스처 한정.
- **NS-5**: 개인 용어집(P2)은 **사용자 데이터** — owner 격리(SEC-8)·영속화 위치는 §4-A Q4 결정.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그; A/B/C/D 또는 X) 기타)

> 답변 방법: 각 `**[Answer]**:` 뒤에 **A/B/C/D** 또는 **X) 기타: 직접 기술**. 모호 답변엔 후속 질문(Step 5). `[전역 계승]`은 정합 확인용(대개 A).

### A. 기술 스택 (FD가 NFR로 이연한 바인딩)

**Q1 [전역 계승·FD Q14 바인딩] — LLM 모델 바인딩.** FD BR-S5(task→역량 등급 자동)의 구체 모델은?
- A) **요약=Claude Sonnet 4.6(`claude-sonnet-4-6`) · 번역=Claude Haiku 4.5(`claude-haiku-4-5`)**, 둘 다 Bedrock 경유(설계 입력 §2). (권장)
- B) 다른 모델 조합(명시).
- X) 기타.
- **권장**: A — 난해 코퍼스 요약=정밀 모델(Sonnet), 번역=경량(Haiku, 품질은 용어집 좌우). Bedrock으로 IAM·관측·비용 일원화. 선택기 비노출(BR-S5).
- **[Answer]**: A

**Q2 — Bedrock 스트리밍 호출 메커니즘.** 첫 생성 스트리밍(NFR-P2)을 어떻게?
- A) **Bedrock 스트리밍 API**(`InvokeModelWithResponseStream` / Converse stream)로 토큰 점진 수신 → 버퍼-검증-스트리밍(BR-S8). boto3(bedrock-runtime) async 래핑. (권장)
- B) 비스트리밍(완성 후 반환) — 단순하나 TTFB 악화·NFR-P2 저해.
- X) 기타.
- **권장**: A — NFR-P2 스트리밍 필수(첫 생성 수십 초). 근거화는 버퍼 후 통과분부터 노출(BR-S8). U6 게이트웨이 경유 형태 유지.
- **[Answer]**: A

**Q3 [전역 계승] — 요약 스토어(영구+핫) 바인딩.** §11 2단 캐시?
- A) **S3(영구 진실원본) + ElastiCache Redis(핫, 짧은 TTL)**, 키=immutable `SummaryCacheKey`. 객체 경로 예 `summaries/{paperId}/v{version}/{task}_{lang}_{persona}_{modelVer}_{promptVer}.json`. read-through/write-through. (권장)
- B) 다른 스토어.
- X) 기타.
- **권장**: A — 설계 입력 §11·기존 자산 재사용(신규 인프라 0). Redis TTL·S3 라이프사이클 구체값은 Infra. 스토리지 부담 무시 수준(~2KB×30만≈600MB).
- **[Answer]**: A

**Q4 — 개인 용어집(P2) 영속화 위치.** 사용자 선호 용어(BR-S4·`glossaryVer`)를 어디에?
- A) **RDS PostgreSQL**(기존 U3/U4 자산) — per-user 구조화 소량 데이터·트랜잭션·owner 격리(SEC-8), accounts/library와 동형. (권장)
- B) Redis(핫) — 빠르나 영속성/백업 약함.
- C) S3 — 객체 단위, 쿼리/갱신 불리.
- X) 기타.
- **권장**: A — 개인 용어집은 사용자 데이터(소량·관계형·owner 스코프). RDS가 격리·영속·백업 정합. `glossaryVer` 증가 관리도 트랜잭션 용이. 시드 도메인 용어집(P1 공유·고정)은 코드/구성 자산.
- **[Answer]**: A

**Q5 — 섹션 도출 메커니즘(FD Q6 바인딩).** 앵커용 섹션/캡션 구조 도출(`InputRefiner`)을?
- A) **정규식·휴리스틱(헤딩 패턴) 코드 구현** — 경량(외부 ML 의존 없음). 헤딩/번호/Table·Figure 라벨 인식 → label+char span, 실패 시 span-only. (권장)
- B) 외부 과학문서 파서 라이브러리(GROBID 등) 도입 — 정확하나 무겁고 신규 인프라.
- X) 기타.
- **권장**: A — AI/ML arXiv는 섹션 헤딩 규칙적이라 정규식 실효. 신규 인프라 0·결정성(PBT). B는 과투자(전문이 이미 정제 텍스트라 재파싱 불필요).
- **[Answer]**: A

**Q6 — 초장문 비동기 잡(map-reduce) v1 범위.** BR-S12(초장문만 비동기 잡, 배포 ③)를 v1에?
- A) **v1=동기 스트리밍 + 입력 토큰 캡**; 캡 초과 초장문은 **map-reduce를 동기 경로에서 처리(스트리밍 유지)하거나, 초과 시 명시 저하/기권**. **별도 비동기 잡 인프라(SQS+워커)는 후속(fast-follow)**. (권장)
- B) v1에 비동기 잡(SQS+워커) 포함 — 초장문 완전 지원, 신규 인프라·복잡도.
- X) 기타.
- **권장**: A — 대다수 논문(~13K, 길어도 ~40K 토큰)은 단일/동기 map-reduce로 충분(§2). 비동기 잡 인프라는 아웃라이어 대비 과투자 → 토큰 캡으로 상한 두고 fast-follow. real-first v1 범위 bounded 유지.
- **[Answer]**: A

### B. 성능 (NFR-P2)

**Q7 — NFR-P2 TTFB 프레이밍.** 온디맨드 응답 목표를?
- A) **2-트랙 목표(형태)**: 캐시 HIT = **즉시**(스토어 조회 수준, 목표 형태만); 첫 생성 = **스트리밍 first-token 목표**(빠른 TTFB)로 체감 관리. **구체 수치는 Build&Test 실측**. NFR-P1(검색 SLA) 비대상 명시. (권장)
- B) 단일 종단 지연 목표(첫 생성 완료까지) — 수십 초라 비현실적.
- X) 기타.
- **권장**: A — NFR-P2 정의(캐시 즉시·스트리밍 TTFB). 첫 생성 완료 시간은 SLA 아님(스트리밍으로 체감 관리). 콜드스타트는 long-running 컨테이너 가정.
- **[Answer]**: A

**Q8 — 토큰 예산 + map-reduce 임계(형태).** LengthRouter(BR-S6)·입력 캡?
- A) **형태만 정의**: 모델 컨텍스트 윈도우 기반 입력 토큰 예산 + 단일/맵-리듀스 분기 임계 + 입력 토큰 캡(아웃라이어 상한). **구체 수치는 Code-gen/튜닝**. (권장)
- B) 본 단계에서 임계 토큰값 확정.
- X) 기타.
- **권장**: A — 기술/수치 이연 원칙(NS-1). 분기 규칙·결과 동등성(통합 출력도 §3 스키마)만 NFR에서 보장.
- **[Answer]**: A

### C. 확장성 · 가용성

**Q9 — 동시성/확장 모델.** 온디맨드 LLM 호출 부하에서 U7?
- A) **stateless 모듈 + 수평 확장**(backend 인스턴스 복제) + **async I/O**(Bedrock·S3·Redis 외부 대기 중첩); **Bedrock 동시 호출은 계정 쿼터 내**(초과 시 큐잉/저하). 오토스케일 트리거/쿼터 수치는 Infra. (권장)
- B) 기타.
- **권장**: A — stateless 온디맨드 경로·수평 확장. LLM 호출은 외부 대기라 async가 동시성 확보. Bedrock 쿼터는 비용/가용성 경계(NFR-C1/Infra).
- **[Answer]**: A

**Q10 — 가용성 목표(NFR-P2 비-SLA).** U7 가용성 프레이밍?
- A) **온디맨드 비-SLA**(검색 NFR-P1·NFR-A1과 분리). 캐시 HIT 경로는 스토어 가용성 의존; 생성 경로는 Bedrock 가용성 의존 → **장애 시 기권/저하**(FR-11), 핵심 검색 기능에 영향 없음(격리). 별도 높은 SLA 미설정. (권장)
- B) 검색과 동일 가용성 목표.
- X) 기타.
- **권장**: A — U7은 보조 기능(NFR-P2). 장애는 우아한 기권으로 흡수, 검색 경로와 격리(의존성 분리). B는 과도 요구(Bedrock 외부 의존).
- **[Answer]**: A

### D. 신뢰성 (RES-9 / NFR-R2)

**Q11 — Bedrock 의존성 격리(타임아웃·재시도·서킷) 정책.** LLM 호출 장애 시?
- A) **명시 타임아웃 + 재시도(1회, BR-S7) + 서킷브레이커 → 기권**(FR-11, 저하 모드). 전문 부재 → 초록 폴백(BR-S2). **수치는 NFR Design/Infra.** 근거화 1차 실패 재시도(1회)와 LLM 장애 재시도는 구분. (권장)
- B) 기타.
- **권장**: A — RES-9·NFR-R2. 근거 없는 출력보다 기권(fail-closed). 재시도 폭주 방지(1회). 수치는 후속.
- **[Answer]**: A

### E. 보안

**Q12 — 보안 처분(인가·레이트리밋·비노출·인젝션·PII·개인 용어집).**
- A) **U7 직접**: SEC-9(BR-S14 내부 필드 비노출)·**프롬프트 인젝션 방어**(본문 격리 `[지시]┃[데이터]`, BR-S3)·SEC-3(원문/번역·프롬프트 로깅 PII 정책 — 원문 텍스트 무분별 로깅 금지). **위임**: SEC-8 인가·SEC-11 레이트리밋=U6 게이트웨이. **개인 용어집=owner 격리**(사용자별 비공개, SEC-8). **공유**: SEC-10 공급망=backend 모노레포 툴링. (권장)
- B) 기타.
- **권장**: A — 단일 권위 경계(레이트리밋·인증=U6). 인젝션 방어는 U7 본문 격리. 개인 용어집 owner 스코프. 원문/번역 로깅은 PII·저작권 주의.
- **[Answer]**: A

### F. 비용 (NFR-C1)

**Q13 — NFR-C1 U7 비용 라인 + CostGuard.** Sonnet 신규 비용을?
- A) **기존 $1,600 상한 내 흡수 + U7 별도 텔레메트리 라인**(모델별 토큰·비용 계상); **distinct 논문×1 영구저장으로 bounded**; **U6 CostGuard 게이트**(예산 초과 시 요약 일시 기권, BR-S13). Infra 비용표에 U7 라인 추가. (권장)
- B) U7 전용 서브예산 분리.
- X) 기타.
- **권장**: A — 요구사항 NFR-C1 보강(팀 합의)·설계 입력 §8 그대로. 온디맨드+영구저장으로 상한 내 흡수. 별도 라인 가시화로 RES-11a 신호.
- **[Answer]**: A

### G. 테스트 (QT-5 / PBT / real-first)

**Q14 — real-first 테스트 전략(mock 대역 없음).** Q10/Q11로 mock 어댑터 미구현 — 어떻게 검증?
- A) **2계층**: (1) **단위 테스트** = 도메인/오케스트레이션 로직을 **테스트 픽스처(테스트 전용 더블, *출하 어댑터 아님*)** 로 검증 + Hypothesis PBT(PBT-S1~S5); (2) **통합 테스트** = 실 의존성(Bedrock·S3·Redis·U6 후크·U1 전문) 대상(자격증명/엔드포인트=CI/Infra 구성). **QT-5 근거화 평가셋(요약/번역 케이스)** 출력 표면 제공(평가 실행 소유=U6/OP). (권장)
- B) 통합 테스트만(실 의존성) — 단위 격리 약화·CI 비용·비결정성.
- X) 기타.
- **권장**: A — real-first라도 단위 테스트의 결정성·속도를 위해 **테스트 픽스처**는 허용(이는 "mock 어댑터 출하"가 아니라 테스트 코드). 실 통합은 핵심 경로 검증. PBT는 Hypothesis 계승. QT-5는 표면 제공.
- **[Answer]**: A — **Production Mock Adapter는 구현하지 않는다.** 다만 **단위 테스트에서는 테스트 전용 Fixture/Stub 사용을 허용**한다(출하 어댑터 아님). 통합 테스트는 실 의존성(Bedrock·S3·Redis·U6·U1) 대상.

**Q15 [전역 계승] — 관측성(NFR-O1).** U7 텔레메트리?
- A) **`ObservabilityHub.emit*`** 로 토큰·비용·지연·persona·task·근거화 결과(통과/기권) 제출(NFR-C1 라인·RES-11 신호·QT-5 운영). 구조화 로그·메트릭·트레이스. (권장)
- B) 기타.
- **권장**: A — U6 단일 권위 소비(재구현 없음). US-S6 운영 모니터링 표면.
- **[Answer]**: A

---

## 5. 다음 절차

1. `§4`의 `[Answer]:` 태그를 채운다(또는 채팅으로 A/B/C/D/X 회신). 모호 답변 시 후속 질문(Step 5) — 해소 전 진행 불가.
2. 답변 확정 → `§2` 산출물 생성(`u7-summarization/nfr-requirements/` nfr-requirements·tech-stack-decisions + real-first 테스트 경계·추적성).
3. 완료 메시지 + 리뷰 게이트 → 승인 시 **U7 NFR Design**(스트리밍/근거화/캐시/저하 패턴·논리 컴포넌트·서킷 수치·CI 등).

> 본 계획·질문은 **리뷰 게이트**입니다. 답변 전까지 NFR Requirements 산출물을 생성하지 않으며, 아직 커밋하지 않았습니다.
