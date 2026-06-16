# u3-accounts-nfr-design-plan.md — NFR Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Design (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/u3-accounts/nfr-requirements/` (NFR 요구사항 및 스택 결정 완료), `requirements.md` (공통 NFR 및 확장 규칙)

---

## 1. 유닛 컨텍스트 및 목표 (Step 1)

U3 Accounts는 RDS PostgreSQL(자격증명) 및 ElastiCache Redis(세션) 복합 스택과 Google reCAPTCHA v3, Amazon SES 연동을 확정했습니다. 이 단계에서는 이러한 구체적 스택을 안전하고 복원력 있게 운영하기 위한 **디자인 패턴(재시도, 서킷 브레이커, 커넥션 풀 등) 및 논리적 컴포넌트 간 상호작용**을 디자인합니다.

- **핵심 NFR 디자인 요소**:
  - **복원력(Resilience)**: Redis/RDS 커넥션 타임아웃 및 재시도 정책, 외부 서비스(reCAPTCHA, SES) 장애 대응 방안.
  - **확장성/성능(Scalability/Performance)**: 커넥션 풀 크기, Redis 메모리 축소(Eviction) 및 세션 캐싱 패턴.
  - **보안(Security)**: 환경변수 및 암호화 키 관리 패턴, CORS 및 쿠키 전송 무결성 설계.

---

## 2. NFR Design 실행 계획 (Step 2)

> 질문 답변 완료 후, 아래 산출물들을 `aidlc-docs/construction/u3-accounts/nfr-design/` 디렉터리에 작성합니다.

- [ ] **nfr-design-patterns.md** — 비즈니스 예외 및 시스템 장애 관련 디자인 패턴 정의
  - 데이터베이스(RDS/Redis) 장애 조치 및 폴백 패턴 (Q1).
  - 외부 API(reCAPTCHA, SES) 타임아웃, 재시도 백오프 및 서킷 브레이커 디자인 (Q2).
  - 무차별 로그인 대입 시 적용할 도메인 백오프 대기 큐 및 CAPTCHA 검증 로직 상세 패턴.
- [ ] **logical-components.md** — 인프라 연동 논리 컴포넌트 구조도 및 책임 명세
  - 데이터베이스 커넥션 풀 관리 컴포넌트 및 설정 정보 (Q3).
  - 환경변수 및 시크릿(Secret) 키 관리 컴포넌트 연동 설계 (Q4).
  - CORS 통제 및 HTTPS 리디렉션 논리 구성 정보 (Q5).
  - PBT-02/03을 충족하기 위한 단위 테스트 및 CI 보안 스캔 통합 모델.

---

## 3. 가정 (Assumptions)

- **AS-1**: Redis 스토리지는 LRU(Least Recently Used) 만료 정책을 기본 적용하며 세션 TTL은 비즈니스 규칙(2시간 Sliding)에 의해 관리됩니다.
- **AS-2**: 데이터베이스 드라이버 및 클라이언트 커넥션은 비동기가 아닌, 동기식 멀티스레드/멀티프로세스 컨테이너 런타임 환경에 맞게 관리됩니다.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그로 답변)

### Q1 — 세션 스토리지(Redis) 장애 시 폴백 패턴 (Resilience / SessionStore)
세션 검증 시 Amazon ElastiCache(Redis) 스토리지 연결이 일시적으로 타임아웃되거나 다운되는 경우, 어떻게 처리합니까?

A) **철저한 보안 우선 (Fail-Closed)**: 세션 검증이 실패한 것으로 처리하여 모든 사용자 요청을 인증 오류(401 Unauthorized / 500 Internal Error)로 거부함. 가용성보다 세션 보안 및 데이터 무결성을 엄격하게 보호.

B) **가용성 우선 (RDS 임시 조회 폴백)**: Redis 스토리지 장애 감지 시, RDS PostgreSQL의 백업 세션 레코드를 즉각 조회하여 복원하는 폴백 로직을 가동함 (레이턴시 예산 P50 < 5ms는 희생되나 서비스 가용성을 보장).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 세션 검증은 시스템 전체의 권한을 결정하는 최전방 방어선이다. Redis 장애 시 RDS로 폴백하는 구조(B안)는 일시적인 캐시 장애나 네트워크 단절 상황에서 무거운 RDBMS 조회를 폭발적으로 발생시켜 **데이터베이스 전체를 마비시키는 연쇄 장애(Cascading Failure)**를 유발한다. 따라서 철저한 보안 우선(Fail-Closed) 정책을 채택하되, Redis 클라이언트 단에 1~2초 이내의 타임아웃과 서킷 브레이커를 짧게 설정하여 시스템이 빠르게 에러(500 혹은 401)를 반환하고 대기할 수 있도록 디자인한다.


### Q2 — 외부 서비스(reCAPTCHA & SES) 장애 대처 방안 (Resilience / External API)
외부 Google reCAPTCHA v3 API 또는 Amazon SES 이메일 발송 서비스가 일시적으로 중단되거나 네트워크 타임아웃(예: 3초 초과)이 발생하는 경우 어떻게 대처합니까?

A) **소프트 바이패스 (Soft Bypass)**: 외부 장애로 인해 회원가입/로그인 흐름이 완전히 차단되는 것을 방지하기 위해, 에러 로그를 남기고 검증/발송을 통과 처리하거나(임시 ACTIVE 계정 활성화 등) mock 결과로 우회함.

B) **철저한 격리 및 에러 처리 (Fail-Closed)**: 외부 서비스 장애를 시스템의 예외 상황으로 규정하여 가입/로그인 처리를 중단하고 사용자에게 "일시적인 시스템 오류"를 리턴함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B (reCAPTCHA v3) / A (Amazon SES 폴백 완화 적용)

선택 근거 및 보완: 서비스의 성격에 따라 차등 분리 처리를 적용한다.
- reCAPTCHA v3 (Fail-Closed, B안): 인증/가입 남용 방어는 보안상 우회할 수 없으므로, reCAPTCHA API 장애 시 가입 및 로그인을 중단하고 일반화된 시스템 오류를 리턴한다.
- Amazon SES (소프트 폴백, A안 유사): 이메일 발송 인프라 장애로 인해 회원 데이터 생성이 가로막히는 것은 방지해야 한다. 따라서 SES 호출 타임아웃 발생 시, 계정은 PENDING 상태로 정상 데이터베이스 영속화를 완료하되, 이메일 발송 실패 신호(EmailDeliveryFailureSignal)를 발행하고 로컬 큐/로그에 적재하여 운영자가 수동 재발송하거나 시스템이 재시도할 수 있는 완화 패턴을 설계한다.


### Q3 — 데이터베이스(RDS & Redis) 커넥션 풀 및 타임아웃 설계 (Performance / Scalability)
API 모듈의 동시 요청 대응력을 높이고 소켓 고갈을 방지하기 위한 데이터베이스 커넥션 관리 수치는 어떻게 디자인합니까?

A) **관리형 커넥션 풀 적용**: RDBMS(PostgreSQL)의 풀 크기를 기본 10, 최대 20으로 제한하고 커넥션 대기 타임아웃을 3초로 디자인함. Redis 풀 크기는 최대 50으로 유지.

B) **서버리스 스케일링 대비 고용량 풀**: RDBMS 풀 크기를 최대 50 이상으로 높게 설정하고 대기 타임아웃을 1초로 짧게 끊어 빠른 실패를 유도함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 동기식 런타임 환경(WSGI 등)에서는 무작정 풀의 최대 크기를 늘리는 것보다 예측 가능한 범위 내로 자원을 제어하는 것이 중요하다. RDBMS 풀 크기 기본 10 / 최대 20, 커넥션 대기 타임아웃 3초를 설정하여 스레드 고갈 및 커넥션 스파이크를 방지하고, 단독 레이턴시 버짓이 극도로 짧은 Redis 풀은 최대 50으로 넉넉히 주어 게이트웨이 동기 검증 시의 소켓 대기 오버헤드를 원천 차단한다.


### Q4 — 애플리케이션 시크릿(Secret) 키 관리 패턴 (Security / Secrets Manager)
cookie-signing 키, RDS 비밀번호, Google reCAPTCHA API 키 등 민감한 시크릿 정보는 컴포넌트 기동 시 어떻게 로드합니까?

A) **런타임 환경변수(OS Environment Variables) 주입**: 컨테이너 배포 시 환경 변수(env)로 안전하게 주입받아 메모리에서만 사용하고, 코드나 레포지토리 내에는 어떤 시크릿도 남기지 않음 (SEC-10).

B) **AWS Secrets Manager / SSM Parameter Store 연동**: 애플리케이션 기동 시 AWS SDK(boto3)를 통해 AWS Secrets Manager API를 직접 호출하여 실시간으로 보안 변수를 메모리에 캐싱함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 기동 시 AWS SDK(boto3)를 통해 실시간 API 호출을 수행하는 방식(B안)은 컨테이너 스케일 아웃 시 AWS Secrets Manager API Rate Limit에 걸려 컨테이너 기동이 실패하는 가용성 리스크가 존재한다. 따라서 12-Factor App 원칙 및 SEC-10에 따라 배포 파이프라인(예: AWS ECS/EKS 배포 정의) 단계에서 Secrets Manager의 값을 런타임 환경변수(OS Environment Variables)로 안전하게 주입받아 애플리케이션 메모리 내에서만 사용하는 구조로 디자인한다.


### Q5 — CORS 및 HTTP 보안 헤더 통제 정책 (Security / HTTP Headers)
AccountController 및 U6 게이트웨이와 연계한 HTTP 인그레스 보안 헤더 및 CORS는 어떻게 디자인합니까?

A) **엄격한 특정 도메인 바인딩**: `Access-Control-Allow-Origin`을 환경 변수로 설정한 구체적인 프런트엔드 도메인으로만 제한하고, 쿠키 기반 세션 처리를 위해 `Access-Control-Allow-Credentials: true`를 강제함. 와일드카드(`*`) 허용은 개발 환경(localhost) 환경변수 설정 시에만 우회 허용.

B) **비교적 관대한 구성**: 동일한 모노레포 환경이므로, 서브도메인 전체 및 로컬 호스트를 폭넓게 허용하도록 기본 와일드카드 규칙을 세팅함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 세션 토큰을 secure, httpOnly, sameSite 속성을 지닌 쿠키로 안전하게 다루기 위해서는 프런트엔드와 백엔드 간의 CORS 무결성이 필수적이다. 와일드카드(*)는 Access-Control-Allow-Credentials: true와 상충하여 브라우저 단에서 거부되므로, 환경 변수로 지정된 신뢰할 수 있는 구체적인 프런트엔드 도메인 원출처(Origin)만 명시적으로 바인딩하도록 설계한다.
