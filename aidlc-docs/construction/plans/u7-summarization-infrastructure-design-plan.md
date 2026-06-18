# u7-summarization-infrastructure-design-plan.md — Infrastructure Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → Infrastructure Design (유닛별 루프, U7) · **유닛**: U7 Summarization · **트랙**: 단일 트랙 · **일자**: 2026-06-19
**근거**: `construction/u7-summarization/nfr-design/`(논리 컴포넌트·패턴) · `nfr-requirements/`(TD-S1~S12) · `construction/infrastructure-design/infrastructure-design.md`(시스템 전역 인프라·배포됨) · U3 `infrastructure-design/`(선례) · `requirements.md`(NFR-C1·RES-2)
**목적**: U7 논리 컴포넌트를 **실제 AWS 리소스에 매핑**. **핵심 특성: 신규 관리형 서비스 0** — 전부 기존 프로덕션 자산(S3·ElastiCache Redis·RDS PostgreSQL·Bedrock·ECS Fargate) 재사용. 본 단계는 **기존 인프라에 U7 자원(프리픽스·키스페이스·테이블·IAM·비용 라인) 추가**가 중심이라 **경량**이다.
**고도**: AWS 리소스 매핑·정책. 리전은 시스템 전역 계승(**ap-northeast-2 서울**). 비용 상한 NFR-C1 $1,600/월 내.

> **계승(시스템 전역 인프라, 배포 완료)**: ECS Fargate(배포 ① backend 모놀리스, ALB 후면, 퍼블릭 서브넷·NAT 0)·RDS PostgreSQL(Multi-AZ)·ElastiCache Redis(Multi-AZ)·S3(코퍼스/전문)·Bedrock(Cohere 임베딩 액세스)·CloudWatch·AWS Budget. CDK 5 스택(Network·Search·Compute·Ingestion·Frontend). **⚠️ IaC 변경 = @ELSAPHABA/Infra 조율 존.**

---

## 1. 유닛 컨텍스트 (Infra 렌즈)

- U7 = backend 모놀리스(배포 ①, 기존 ECS Fargate) 내 **모듈** — **신규 컴퓨트 없음**. 게이트웨이 경유 마운트(`backend/wiring.py`).
- **U7이 기존 인프라에 추가하는 것**:
  - **S3**: 요약 영구 객체(`summaries/` 프리픽스) — 기존 버킷/전문과 공존.
  - **Redis(ElastiCache)**: 요약 핫캐시 키스페이스(TTL) — 기존 세션 캐시와 분리.
  - **RDS(PostgreSQL)**: 개인 용어집 테이블 — 기존 accounts/library DB와 공존(마이그레이션).
  - **Bedrock IAM**: Sonnet 4.6/Haiku 4.5 `InvokeModel`/`InvokeModelWithResponseStream` 권한 — 기존 ECS task role에 추가.
  - **비용/관측**: NFR-C1 U7 라인(CloudWatch 메트릭·Budget)·ObservabilityHub→CloudWatch(기존).
  - **CI**: 통합 테스트 자격증명(실 Bedrock/S3/Redis/RDS).
- **비동기 잡 인프라(SQS+워커)**: TD-S9 fast-follow → **v1 미프로비저닝**(확인 Q8).

---

## 2. Infrastructure Design 실행 계획 (Step 2 — 답변 확정 후, 체크박스)

> 산출물은 `aidlc-docs/construction/u7-summarization/infrastructure-design/` 에 생성. **§4 답변 전 미생성.**

- [x] **infrastructure-design.md** — 논리 컴포넌트 → AWS 리소스 매핑:
  - S3 프리픽스/라이프사이클(Q2) · Redis 키스페이스/TTL(Q3) · RDS 용어집 테이블 DDL/마이그레이션(Q4) · Bedrock IAM/아웃바운드(Q5) · 비용 라인/알람(Q6) · CI 자격증명(Q7).
  - 보안: IAM 최소권한(Bedrock 모델 ARN 스코프·S3 프리픽스 스코프)·RDS owner 격리·시크릿(기존 패턴).
- [x] **deployment-architecture.md** — 배포/네트워크/모니터링:
  - 컴퓨트 = 기존 ECS Fargate 모듈(신규 0, Q1)·네트워크 = 기존 VPC/ALB(Bedrock 아웃바운드 경로, Q5)·모니터링 = CloudWatch/Budget(Q6)·비동기 잡 v1 미프로비저닝(Q8)·공유 인프라 IaC 추가 조율(Q9).

---

## 3. 가정 (잘못이면 §4 또는 지적으로 정정)

- **AS-1**: 리전 = **ap-northeast-2(서울)** 시스템 전역 계승. 멀티 AZ는 기존 RDS/Redis 구성 계승.
- **AS-2**: NFR-C1 $1,600/월 상한 내. 신규 관리형 서비스 0 → 인프라 증분 비용 = **Bedrock 토큰 비용(가변)** + S3 저장(~무시) 중심.
- **AS-3 [조율 존]**: IaC(CDK 스택)·ECS task role·CI 파이프라인 변경 = **@ELSAPHABA/Infra 공유** — U7 제안 + 합의.
- **AS-4**: 구체 수치(Redis TTL·토큰 캡·오토스케일)는 Code-gen/튜닝. 본 단계는 리소스·정책 매핑.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그; A/B/C/D 또는 X) 기타)

### A. 컴퓨트 / 배포 (Compute / Deployment)

**Q1 — U7 컴퓨트.** 요약/번역 모듈의 런타임?
- A) **기존 ECS Fargate(배포 ① backend 모놀리스)에 모듈로 포함 — 신규 컴퓨트 0.** app-shell 마운트, ALB 후면. (권장)
- B) U7 전용 별도 서비스(컨테이너/Lambda) 분리.
- X) 기타.
- **권장**: A — U7은 동기 API 모듈(배포 ①, unit-of-work). 별도 서비스는 과분할·운영 부담. 온디맨드 LLM 대기는 async I/O로 흡수. **⚠️ 마운트=조율 존.**
- **[Answer]**: A

### B. 스토리지 (Storage)

**Q2 — S3 요약 객체.** 영구 산출물(§11)을 어디에/어떻게?
- A) **기존 S3 버킷에 `summaries/` 프리픽스** 추가(전문과 공존). 라이프사이클 = **현행 키 영구 보존**; modelVer/promptVer 변경 시 옛 객체는 미참조 방치(선택적 라이프사이클 만료는 운영 옵션). IAM은 프리픽스 스코프. (권장)
- B) U7 전용 신규 버킷.
- X) 기타.
- **권장**: A — 신규 버킷 불필요(설계 입력 §11·~600MB 무시 수준). 프리픽스 분리 + IAM 스코프로 격리. 키 immutable(INV-5).
- **[Answer]**: A

**Q3 — Redis 핫캐시.** 요약 핫캐시를 기존 ElastiCache에?
- A) **기존 ElastiCache Redis에 별도 키스페이스(프리픽스, 예 `sum:`) + TTL**. 세션 캐시와 키 충돌 없음·메모리 경계 모니터. (권장)
- B) U7 전용 신규 캐시 노드.
- X) 기타.
- **권장**: A — 신규 노드 불필요. 키스페이스 프리픽스 분리. TTL 구체값은 Code-gen. 메모리 사용량은 CloudWatch 모니터(요약 ~2KB).
- **[Answer]**: A

**Q4 — RDS 개인 용어집 테이블.** P2 용어집(TD-S6)을 기존 RDS에?
- A) **기존 RDS PostgreSQL에 신규 테이블**(예 `user_glossary{user_id FK, term_from, term_to, glossary_ver, ...}`) + **마이그레이션(기존 U3/U4 마이그레이션 러너 재사용)**. owner FK·인덱스·RLS 또는 앱 레벨 owner 스코프. (권장)
- B) 신규 DB 인스턴스.
- X) 기타.
- **권장**: A — accounts/library와 동일 DB 공존(신규 인스턴스 0). 시드 도메인 용어집(P1)은 코드/구성 자산(DB 아님). DDL/마이그레이션은 산출물에 명세.
- **[Answer]**: A

### C. 통합 / 네트워크 (Bedrock / Networking)

**Q5 — Bedrock 액세스 + 아웃바운드.** Sonnet/Haiku 호출 권한·경로?
- A) **기존 ECS task role에 Bedrock 권한 추가**(`bedrock:InvokeModel`·`InvokeModelWithResponseStream`, **모델 ARN 스코프**: Sonnet 4.6·Haiku 4.5). 아웃바운드는 **기존 퍼블릭 서브넷 경로**(NAT 0, U3 패턴) 또는 Bedrock VPC 엔드포인트(선택). (권장)
- B) 별도 IAM 주체/네트워크.
- X) 기타.
- **권장**: A — 최소권한(모델 ARN 스코프). 기존 아웃바운드 경로 재사용(NAT 비용 0). VPC 엔드포인트는 보안 강화 옵션(Infra trade-off). **⚠️ task role 변경=조율 존.**
- **[Answer]**: A

### D. 모니터링 / 비용 (Monitoring / Cost)

**Q6 — NFR-C1 U7 비용 라인 + 알람.** Sonnet 신규 비용 가시화?
- A) **CloudWatch 메트릭(U7 토큰·비용, 모델별) + 기존 AWS Budget/OpsAlerts에 U7 반영**. ObservabilityHub→CloudWatch(기존 G3 경로). 비용 라인 = Infra 비용표에 U7 추가. CostGuard(U6) 게이트는 앱 레벨. (권장)
- B) 별도 비용 대시보드/알람 스택.
- X) 기타.
- **권장**: A — 기존 관측/Budget 재사용(운영 하드닝 패스 자산). U7 토큰 메트릭 emit → CloudWatch. RES-11a 신호. 신규 스택 불필요.
- **[Answer]**: A

### E. CI 자격증명 (Shared / Deployment)

**Q7 [backend-shared] — 통합 테스트 자격증명.** real-first 통합 테스트(실 Bedrock/S3/Redis/RDS)의 CI 액세스?
- A) **별도 게이트 레인에 스코프된 CI IAM 역할**(Bedrock 모델·S3 `summaries/` 프리픽스·테스트 RDS/Redis 한정) — OIDC/시크릿(기존 CD 패턴). 단위 레인(Fixture/Stub)은 자격증명 불필요·항상 실행. (권장)
- B) 통합 테스트를 CI에서 제외(수동/스테이징만).
- X) 기타.
- **권장**: A — NFR Design Q10 정합(단위 항상·통합 게이트). 최소권한 CI 역할. **⚠️ CI 파이프라인=조율 존.**
- **[Answer]**: A

### F. 메시징 (Messaging — 비동기 잡)

**Q8 — 비동기 잡 인프라(초장문 map-reduce).** TD-S9 fast-follow를 v1에?
- A) **v1 미프로비저닝** — SQS/워커 인프라 없음(동기 + 토큰 캡). 후속 도입 시 기존 이벤트 백본/Ops 워커(배포 ③) 패턴 재사용. (권장)
- B) v1에 SQS+워커 프로비저닝.
- X) 기타.
- **권장**: A — TD-S9 결정 계승(v1 bounded). 신규 메시징 인프라 0. 후속 도입은 기존 EventBridge/Ops 워커 패턴.
- **[Answer]**: A

### G. 공유 인프라 (Shared Infrastructure)

**Q9 [조율 존] — IaC 자원 추가 방식.** U7 신규 자원(S3 프리픽스·RDS 테이블·Bedrock IAM·CI)을 어떻게 IaC에?
- A) **기존 CDK 스택에 증분 추가**(Compute 스택=task role/IAM·Search/Storage 스택=S3 프리픽스 정책·DB 마이그레이션=러너). 신규 스택 없음. **@ELSAPHABA/Infra 사인오프**. (권장)
- B) U7 전용 신규 CDK 스택.
- X) 기타.
- **권장**: A — 신규 관리형 0이라 증분 추가가 적절(신규 스택 과분). 마이그레이션은 기존 러너. **⚠️ IaC 변경=조율 존(U7 제안 + Infra 합의).**
- **[Answer]**: A

---

## 5. 다음 절차

1. `§4`의 `[Answer]:` 태그를 채운다(또는 채팅으로 회신). 모호 답변 시 후속 질문(Step 5).
2. **[조율 존] Q1/Q5/Q7/Q9**(task role·CI·IaC·마운트)는 @ELSAPHABA/Infra 합의 표시.
3. 답변 확정 → `§2` 산출물 생성(`u7-summarization/infrastructure-design/` infrastructure-design·deployment-architecture).
4. 완료 메시지 + 리뷰 게이트 → 승인 시 **U7 Code Generation**(Part 1 계획 → Part 2 생성, real-first).

> 본 계획·질문은 **리뷰 게이트**입니다. 답변 전까지 Infrastructure Design 산출물을 생성하지 않으며, 아직 커밋하지 않았습니다.
