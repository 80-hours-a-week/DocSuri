# u3-accounts-infrastructure-design-plan.md — Infrastructure Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → Infrastructure Design (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/u3-accounts/nfr-design/` (NFR 디자인 및 논리 컴포넌트 완료), `requirements.md` (공통 NFR 및 확장 규칙), `tech-stack-decisions.md` (RDS PostgreSQL, ElastiCache Redis, SES, reCAPTCHA v3 확정)

---

## 1. 유닛 컨텍스트 및 목표 (Step 1)

U3 Accounts는 API 모듈형 모놀리스(배포 ①)의 일부로 함께 패키징되어 배포됩니다. 자격증명 저장용 RDS PostgreSQL 및 세션 저장용 ElastiCache Redis, 외부 연동(Amazon SES, Google reCAPTCHA)의 구체적인 AWS 리소스 매핑과 VPC 네트워크 토폴로지, 비용 가드레일을 준수하는 인프라 사양을 최종 설계합니다.

- **핵심 인프라 설계 요소**:
  - **컴퓨트(Compute)**: API 서비스(모놀리스)의 ECS Fargate vs Lambda 서버레스 런타임 결정.
  - **스토리지(Storage)**: RDS PostgreSQL 및 ElastiCache Redis의 인스턴스 사양, 백업 정책 설정.
  - **네트워크(Networking)**: VPC 토폴로지 구성 (NAT Gateway 비용 최적화 및 서브넷 격리 규칙).
  - **이메일(SES)**: 도메인 인증 및 샌드박스 설정 모델.

---

## 2. Infrastructure Design 실행 계획 (Step 2)

> 질문 답변 완료 후, 아래 산출물들을 `aidlc-docs/construction/u3-accounts/infrastructure-design/` 디렉터리에 작성합니다.

- [x] **infrastructure-design.md** — 논리 컴포넌트의 AWS 리소스 구체 매핑 명세
  - 데이터베이스 리소스 정의: Amazon RDS PostgreSQL 및 ElastiCache Redis의 구체 인스턴스 타입, 엔진 버전, Multi-AZ 구성 여부 (Q2, Q3).
  - 이메일 서비스 정의: Amazon SES 도메인/이메일 자격증명 검증 및 샌드박스 정책 (Q5).
  - 보안 매개변수: VPC, 보안 그룹(Security Group), IAM Role 권한 정의.
- [x] **deployment-architecture.md** — 컴퓨트 런타임 및 물리 네트워크 설계
  - 컴퓨트 인프라 정의: ECS Fargate vCPU/Memory 사양, 오토스케일링 및 로드밸런서(ALB) 구성 여부 (Q1).
  - 네트워크 토폴로지: 서브넷 구성 및 NAT Gateway 비용 최적화 모델 (Q6).
  - 모니터링: CloudWatch Logs 그룹 및 Alarms 지표 설정.

---

## 3. 가정 (Assumptions)

- **AS-1**: 배포 리전은 U1 Ingestion 및 시스템 전역 리전 설정을 상속받아 **ap-northeast-2 (서울)** 리전을 기준으로 삼습니다.
- **AS-2**: 총 비용 상한($1,600/월, NFR-C1) 내에서 인프라를 구성해야 하므로 불필요한 고비용 리소스(예: 대용량 NAT Gateway 다중화)는 최대한 억제하고 스케일링을 보수적으로 조정합니다.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그로 답변)

### Q1 — API 서비스(모듈형 모놀리스) 컴퓨트 인프라 선정 (Compute / Deployment)
U2, U3, U4 및 U6 미들웨어가 통합 배포되는 모듈형 모놀리스 API 배포 단위(①)의 AWS 컴퓨트 서비스를 무엇으로 선정합니까?

A) **AWS Lambda (behind API Gateway)**: 완전 서버리스로 구동하여 트래픽이 없을 때의 비용을 0으로 수렴시킴. 초기 트래픽이 낮고 크레딧 절약이 극대화되는 장점이 있으나, Python 웹 프레임워크 로딩 시 최초 요청 콜드 스타트 지연(Cold Start)이 발생할 수 있음.

B) **AWS ECS Fargate (behind Application Load Balancer)**: 도커 컨테이너를 상시 가동(최소 1~2개 태스크)하여 콜드 스타트가 없는 고성능 API 서비스를 보장함. 상시 구동 비용(ALB 및 ECS Fargate 기본 비용 약 $30~$40/월 이상)이 기본 차징됨.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 세션 검증(U3)과 데이터 수집(U1/U2)이 통합된 API 서비스 특성상, 람다의 콜드 스타트 지연(A안)은 게이트웨이 단계에서 치명적인 레이턴시 스파이크를 유발한다. 따라서 **AWS ECS Fargate(Application Load Balancer 후면)**를 선정하여 고성능 상시 가동 런타임을 확보한다. 비용 가드레일을 위해 초기에는 최소 태스크(Task) 개수를 1~2개로 제한하여 구동 비용을 최적화한다.


### Q2 — RDS PostgreSQL 데이터베이스 인스턴스 사양 (Storage / DB Instance)
사용자 정보 및 자격증명(`CredentialStore`)을 영속화할 Amazon RDS PostgreSQL의 인스턴스 사양과 Multi-AZ 구성을 어떻게 설계합니까?

A) **db.t4g.micro / 단일 가용 영역(Single-AZ)**: 비용 최적화 사양. 초기 개발 및 크레딧 절감에 최적이며 가동 비용이 매우 낮음 (RTO/RPO 지연 감수).

B) **db.t4g.small / 다중 가용 영역(Multi-AZ) 활성화**: 프로덕션 가용성 요건을 만족하기 위해 대기 인스턴스를 다중 AZ에 배치하고 자동 페일오버를 가동함 (비용 약 2배 증가, 월 $30~$50 선).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 사용자 계정 정보와 암호 자격증명은 시스템 전체의 신뢰성 앵커(Anchor)다. 비용 절감을 위해 단일 가용 영역(A안)을 선택할 경우 장애 시 긴 RTO가 발생하여 서비스 전체 마비를 초래하므로, db.t4g.small / Multi-AZ 활성화 사양을 채택하여 자동 페일오버를 보장한다.


### Q3 — ElastiCache Redis 인스턴스 사양 (Storage / Session Cache)
세션 정보(`SessionStore`)를 초저지연(P50 < 5ms)으로 다룰 Amazon ElastiCache Redis의 노드 사양을 어떻게 선정합니까?

A) **cache.t4g.micro / 단일 노드(무복제)**: 세션 유실 복원력(Q3=A) 요건 대비 인프라 비용을 최소화함 (Redis 다운 시 모든 세션 파기됨).

B) **cache.t4g.micro / 기본 1노드 + 복제본 1노드(Multi-AZ 활성화)**: 고가용성 요건(Q3=A)을 만족하는 복제본 클러스터 구성으로 자동 페일오버 가동 (월 약 $25 내외).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. NFR Requirements 단계에서 세션 스토리지의 복원력을 '강한 복원력(세션 유실 최소화)'으로 결정했으므로, cache.t4g.micro / 기본 1노드 + 복제본 1노드 (Multi-AZ 활성화) 구성을 채택한다. 이를 통해 노드 장애 시에도 실시간 가용성을 보장하며 사용자 세션 대량 파기 사태를 방지한다.


### Q4 — AWS VPC 및 NAT Gateway 네트워크 토폴로지 (Networking / Cost Optimization)
Amazon RDS와 ElastiCache는 사설 서브넷(Private Subnet)에 배치하는 것이 보안 표준입니다. 그러나 사설 서브넷의 컴퓨트 노드가 인터넷(Amazon SES, Google reCAPTCHA 등 외부 API)과 통신하려면 NAT Gateway가 필요하며, 이는 월 $32/개당의 고정 비용을 발생시킵니다. 비용 최적화를 위해 네트워크 구성을 어떻게 조정합니까?

A) **퍼블릭 서브넷 중심 구성 (NAT Gateway 배제)**: ECS 컨테이너를 퍼블릭 서브넷에 배치하여 인터넷에 직접 아웃바운드 통신을 수행(NAT Gateway 불필요, 비용 절감). RDS 및 Redis는 보안 그룹(Security Group) 규칙을 통해 오직 ECS 컨테이너의 사설 IP 대역만 접근 가능하도록 엄격히 통제하여 보안성 절충. (가장 비용 효율적)

B) **표준 VPC 4서브넷 구성 (NAT Gateway 적용)**: ECS 컨테이너 및 DB를 모두 사설 서브넷에 격리하고, 인터넷 아웃바운드 통신을 위해 1개의 NAT Gateway(월 $32 고정 비용)를 배치하여 표준 보안 구성을 준수함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 프로덕션급 격리를 추구하는 B안도 훌륭하지만, 초기 단계에서 NAT Gateway가 차지하는 월 고정 비용($32/개)은 전체 자원 활용도 대비 낭비가 크다. 따라서 **ECS Fargate 컨테이너를 퍼블릭 서브넷에 배치(단, ALB를 통해서만 인그레스 허용)**하고 외부 API(SES, reCAPTCHA)와 NAT 없이 직접 아웃바운드 통신을 수행하도록 한다. 가장 중요한 RDS 및 ElastiCache는 퍼블릭 IP가 없는 완전한 'Isolated Private Subnet'에 격리하고, 보안 그룹(Security Group) 규칙을 통해 오직 ECS 컨테이너의 사설 IP 대역(및 VPC CIDR)으로부터의 인바운드만 허용하도록 철저하게 통제한다. 이 구조는 NAT 비용을 완전히 제로화하면서도 데이터 스토리지 계층의 네트워크 접근을 완벽히 차단하는 실리적인 보안 타협점이다.


### Q5 — Amazon SES 이메일 발송 자격증명 검증 방식 (Integration / Email Domain)
Amazon SES를 사용하여 인증 링크 메일을 발송할 때, AWS에서 어떤 발송자 인증 방식을 사용합니까?

A) **단일 이메일 주소 인증 (Single Email Verification)**: 발송자로 사용할 단일 이메일 주소(예: `admin@yourdomain.com` 혹은 개인 이메일)만 AWS SES에서 인증을 거쳐 발송자로 사용함 (개발 및 데모에 가장 빠르고 간편함).

B) **도메인 인증 (Domain Verification)**: Route 53 또는 DNS 관리 소프트웨어에 DKIM 및 TXT 레코드를 추가하여 도메인 전체(`docsuri.dev` 등)의 이메일 발송 자격을 인증함 (프로덕션 메일 수신 성공률 최대화).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 단일 이메일 주소 인증(A안)은 개발 단계에서 편리하지만 스팸 필터링(SPF/DKIM) 점수가 낮아 메일 수신 성공률이 크게 떨어진다. PENDING 상태 계정의 이메일 인증이 핵심 비즈니스 흐름인 만큼, Route 53 또는 DNS에 레코드를 등록하여 **도메인 인증(Domain Verification)**을 완전하게 수행함으로써 메일 신뢰성을 최고 수준으로 확보한다.
