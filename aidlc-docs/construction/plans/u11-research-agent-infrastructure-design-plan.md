# u11-research-agent-infrastructure-design-plan.md — Infrastructure Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → Infrastructure Design (유닛별 루프) · **유닛**: U11 Research Agent · **일자**: 2026-06-24
**근거(SSOT)**: `u11-research-agent/nfr-design/`(논리 컴포넌트·토폴로지) · `nfr-requirements/`(TD-RA-1~15) · `functional-design/` · 시스템 전역 `construction/infrastructure-design/infrastructure-design.md` · 아키텍처 게이트 `docmodel-fulltext-index-pivot-plan.md`.
**핵심 방향(선례 계승)**: U7처럼 **신규 관리형 서비스 최소화 — 기존 프로덕션 자산 재사용 + 자원 증분**. 리전 = **ap-northeast-2(서울)**. 단 U11은 **① SQS Agent 워커(비동기 잡)** 와 **② 전문 통합 인덱스 노드 증설(아키텍처 게이트)** 라는 신규/증설 요소가 있음.
**선례 비교(질문 설계 입력 — 하나만 안 봄)**:
- **U7**(논리→AWS 매핑·S3 프리픽스·Redis 키스페이스·RDS 테이블·Bedrock IAM ARN 스코프·증분 비용·SQS 워커 별도 배포)
- **U8**(외부 API 쿼터·스냅샷 캐시·런타임/네트워크/스케일링 — 모드 B 참고)
- **U3**(deployment-architecture·시크릿·서브넷·Multi-AZ)
- **시스템 전역 infrastructure-design.md**(CDK 스택·CD·예산 알람)

> 본 계획서는 **리뷰 게이트**다. `[Answer]:`가 모두 확정되기 전에 Infra 산출물(`infrastructure-design.md`·`deployment-architecture.md`)을 만들지 않는다. **본 게이트는 질문만 — 결정은 답변 후.**

---

## 1. 유닛 컨텍스트 (Infra 렌즈)

U11 = backend 모놀리스 모듈(동기) + **Agent 워커(비동기 잡)**. 대부분 기존 자산 재사용(ECS·RDS·Redis·S3·Bedrock·CloudWatch)이나, **신규/증설 2가지**: (1) **SQS 큐 + Agent 워커**(긴 다논문 분석), (2) **전문 통합 인덱스 → OpenSearch 노드 증설**(아키텍처 게이트·#120 추정 월 +$100~220). 후자는 **U1/U2/infra 조율 + 게이트 승인** 선결.

---

## 2. Infrastructure Design 실행 계획 (답변 확정 후, 체크박스)

`aidlc-docs/construction/u11-research-agent/infrastructure-design/`에 작성:
- [ ] **infrastructure-design.md** — 논리→AWS 매핑·스토리지(RDS 테이블·S3 프리픽스·Redis 키스페이스·OpenSearch 사이징)·Bedrock IAM·SQS·모니터링/비용·보안·CI 자격증명·증분 비용 요약.
- [ ] **deployment-architecture.md** — 컴퓨트/배포(모듈+워커)·네트워크 토폴로지·메시징·IaC 증분·배포 체크리스트.

---

## 3. 가정 (잘못이면 §4 또는 지적으로 정정)

- **AS-I1**: 리전 ap-northeast-2·기존 VPC/서브넷/ALB/CloudFront·Secrets Manager·CD(ECR/ECS) 패턴 계승.
- **AS-I2**: U6 게이트웨이·근거화·CostGuard·ObservabilityHub→CloudWatch는 기존 경로 재사용(신규 0).
- **AS-I3**: 전문 통합 인덱스·eager doc-model·OpenSearch 노드 증설은 **아키텍처 게이트 결정** + U1/U2/infra 조율(본 유닛 단독 확정 아님).
- **AS-I4**: 수치(인스턴스 사양·TTL·SQS 가시성 타임아웃·K·서킷 임계)는 본 단계에서 형태/등급까지, 정밀 튜닝은 Code-gen/Build&Test.
- **AS-I5**: 조율 존(`backend/wiring.py`·게이트웨이·CI/CD·IAM task role)은 app-shell/Infra(@ELSAPHABA) 사인오프.

---

## 4. 명확화 질문 (`[Answer]:` 태그; 권장안=A, 변경 시 B/C/X+사유)

### A. 컴퓨트 / 배포 (Compute / Deployment)

#### Q1 — 동기 모듈 배포 (U7 §1 패턴)
U11 동기 경로 컴퓨트는?

A) **ECS Fargate 기존 backend 모놀리스에 모듈 추가(권장)** — ALB 후면, 신규 컴퓨트 0. (U7과 동형)

B) 별도 서비스.  X) 기타.

[Answer]: 

#### Q2 — Agent 워커(비동기 잡) 배포 (U7 SQS 워커 / U8 런타임 패턴)
긴 다논문 분석 워커는?

A) **별도 ECS 서비스/태스크(SQS 소비)로 분리(권장)** — 게이트웨이 타임아웃 무관·독립 스케일. U7 요약 워커 선례. 게이트(env)로 on/off, 미설정 시 대규모는 abstain(기존 패턴).

B) 동기 모듈 내 백그라운드 스레드.  C) Lambda.  X) 기타.

[Answer]: 

### B. 스토리지 (Storage)

#### Q3 — 세션·결과 RDS (U7 §2.3 테이블 패턴)
세션·턴·결과 영속은?

A) **기존 RDS PostgreSQL + 신규 테이블(권장)** — `research_session`·`research_turn`·`research_result`(owner FK·인덱스). 마이그레이션 러너 재사용. 큰 근거표 본문은 JSONB 또는 S3 참조.

B) 신규 DB.  X) 기타.

[Answer]: 

#### Q4 — 첨부·결과 S3 (U7 §2.1 프리픽스 패턴)
첨부 원본·대용량 결과는?

A) **기존 S3 버킷 + 프리픽스(권장)** — `research-agent/attachments/{ownerId}/...`·(옵션)`research-agent/results/...`. SSE-KMS·owner 스코프·IAM 프리픽스 스코프. 라이프사이클은 운영 옵션.

B) 신규 버킷.  X) 기타.

[Answer]: 

#### Q5 — 결과 캐시 Redis (U7 §2.2 키스페이스 패턴)
`AgentCacheKey` 핫캐시는?

A) **기존 ElastiCache + 키스페이스 `agent:`(권장)** — 세션 캐시와 분리·TTL. 신규 노드 0(메모리 모니터). 영구는 S3/RDS.

B) 신규 캐시.  X) 기타.

[Answer]: 

#### Q6 — 전문 통합 인덱스 사이징 (아키텍처 게이트 · #120 · GQ1)
전문 색인 OpenSearch는?

A) **게이트·실험 종속 — 본 산출물엔 "노드 증설 가능성(월 +$100~220 추정)·granularity(GQ1) 미정"만 기록, 확정은 게이트 승인 + U1/U2/infra 조율(권장)**. 본 유닛 단독 사이징 확정 안 함.

B) 지금 노드 등급·granularity 확정.  X) 기타.

[Answer]: 

### C. 통합 / 네트워크 (Bedrock / Networking)

#### Q7 — Bedrock IAM (U7 §3 ARN 스코프 패턴)
LLM 액세스 권한은?

A) **task role에 `bedrock:InvokeModel(+Stream)` + 모델 ARN 스코프(권장)** — Sonnet 4.6·Haiku 4.5 ARN(inference profile 포함). 워커 role도 동일. ⚠️ task role 변경=조율 존.

B) 광범위 권한.  X) 기타.

[Answer]: 

#### Q8 — 검색/doc-model/OpenSearch 액세스 경로
U11이 검색·doc-model에 어떻게 접근?

A) **U2 검색 재사용(모듈 내 호출) + doc-model 읽기(S3/캐시)(권장)** — OpenSearch 직접 접근은 U2 경유(U2 API 재사용 vs 직접 질의는 NFR/Code 미정·FD Q2). 아웃바운드는 기존 서브넷 경로 재사용(NAT 0).

B) U11이 OpenSearch 직접 접근.  X) 기타.

[Answer]: 

### D. 메시징 (Messaging — 비동기 잡)

#### Q9 — SQS 큐 (U7 요약 큐 / U8 패턴)
비동기 잡 큐는?

A) **신규 SQS 큐 `agent-analysis-jobs` + DLQ(권장)** — 가시성 타임아웃·재시도·멱등(캐시 히트). 워커가 소비. 게이트 env로 on/off. 수치는 Code-gen.

B) 기존 큐 공유.  C) 큐 없이 동기만.  X) 기타.

[Answer]: 

### E. 모니터링 / 비용 (Monitoring / Cost)

#### Q10 — CloudWatch·비용 라인 (U7 §4 패턴)
관측·비용은?

A) **ObservabilityHub→CloudWatch(기존 G3 경로) + 시스템 비용표에 U11 라인 추가(권장)** — 모드별 토큰·지연·기권/저하·외부 오류율. 비용 = Bedrock 토큰(가변) + (게이트 시)인덱스 노드 증분. AWS Budget·OpsAlerts 반영. 앱 게이트=U6 CostGuard(RES-11a).

B) 비용만.  X) 기타.

[Answer]: 

### F. CI 자격증명 (Shared / Deployment)

#### Q11 — CI 레인 자격증명 (U7 §6 패턴)
통합 테스트 자격증명은?

A) **스코프된 CI IAM 역할(OIDC, 기존 CD 패턴)(권장)** — Bedrock 모델·S3 `research-agent/*`·테스트 RDS/Redis/SQS·U2 검색 한정. 단위 레인은 자격증명 불필요. ⚠️ CI 파이프라인=조율 존.

B) 광범위 자격증명.  X) 기타.

[Answer]: 

### G. 공유 인프라 (Shared Infrastructure)

#### Q12 — IaC 증분 + 공유 전략 (시스템 전역 / U7 §5 패턴)
IaC는 어떻게?

A) **시스템 CDK에 U11 증분(권장)** — RDS 테이블·S3 프리픽스·Redis 키스페이스·SQS 큐+DLQ·Agent 워커 서비스·IAM. 전문 인덱스 노드 증설은 게이트 승인 후 별도(U1/U2/infra). 신규 스택 최소화. ⚠️ 조율 존.

B) U11 전용 스택 신설.  X) 기타.

[Answer]: 

#### Q13 — 증분 비용 요약 (U7 §7 패턴)
비용 요약 방식은?

A) **증분 표(권장)** — 컴퓨트(모듈 0·워커 소액)·RDS/Redis/S3(증분 무시~소액)·**Bedrock 토큰(가변·다논문 fan-out·K·캐시 bound)**·**(게이트 시)OpenSearch 노드 +$100~220/월 추정(실측 배포 후)**·SQS(소액). NFR-C1 상한 내.

B) 단일 총액.  X) 기타.

[Answer]: 

---

## 5. 다음 절차
1. **Q1~Q13 답변 확정**(애매 시 후속 질문) — 본 게이트는 질문만.
2. 답변 후 `u11-research-agent/infrastructure-design/`에 `infrastructure-design.md`·`deployment-architecture.md` 생성.
3. 승인 후 **Code Generation**(코드·테스트·배포 스캐폴드).
4. **전문 인덱스 사이징·granularity(GQ1)·랭킹(GQ2)** 은 아키텍처 게이트 승인 + U1/U2/infra 조율 + 실험으로 확정(본 유닛 단독 아님).
5. 커밋·푸시·PR(#183)은 사용자 승인 후.
