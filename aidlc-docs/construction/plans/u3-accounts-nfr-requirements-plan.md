# u3-accounts-nfr-requirements-plan.md — NFR Requirements 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Requirements (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/u3-accounts/functional-design/` (완료된 FD 산출물 3종), `requirements.md` (공통 NFR 및 확장 규칙)

---

## 1. 유닛 컨텍스트 및 목표 (Step 1)

U3 Accounts는 사용자 인증, 세션 수명주기, 객체 단위 소유권 인가를 담당하며, 특히 **세션 검증은 API Gateway 미들웨어(U6)를 통해 모든 동기 요청마다 실행**됩니다. 따라서 극도로 높은 성능(저지연), 고가용성 및 철저한 보안 통제가 수반되어야 합니다.

- **핵심 NFR 대상**:
  - **성능(Latency)**: 게이트웨이 세션 검증 오버헤드 최소화 (NFR-P1).
  - **보안(Security)**: 비밀번호 적응형 해싱(Argon2id)의 부하 통제, 세션 토큰 보안 전송 및 보관, 무차별 대입 및 남용 방어.
  - **기술 스택**: Python 환경에 적합한 암호화 및 영속성 라이브러리/데이터베이스 선정.

---

## 2. NFR Requirements 실행 계획 (Step 2)

> 질문 답변 완료 후, 아래 산출물들을 `aidlc-docs/construction/u3-accounts/nfr-requirements/` 디렉터리에 작성합니다.

- [ ] **nfr-requirements.md** — 성능, 확장성, 가용성, 신뢰성 요건 명세
  - 세션 검증 성능 지표(P50/P99 레이턴시 버짓) 및 처리량(TPS) 정의 (Q1).
  - 가용성(RTO/RPO) 및 세션 스토리지 장애 시의 복구 목표 정의 (Q3).
  - 보안 및 위협 모델링(Credential/Token 노출 방지, Lockout DoS 방지) 세부 정책.
- [ ] **tech-stack-decisions.md** — U3 기술 스택 및 라이브러리 선정 (ADR 형식)
  - Python 패키지: 비밀번호 해싱(Argon2id) 및 암호화 관련 라이브러리 결정 (Q2).
  - 영속성 데이터베이스: 계정 자격증명(`CredentialStore`) 및 세션(`SessionStore`) 저장용 AWS 관리형 서비스 선정 (Q4).
  - 통합 서비스 스택: CAPTCHA 검증 모듈 및 이메일 발송(SES 등) 연동 도구 결정 (Q5, Q6).

---

## 3. 가정 (Assumptions)

- **AS-1**: 백엔드 런타임은 공통 결정에 따라 **Python**을 사용합니다.
- **AS-2**: 세션 토큰의 브라우저 전송은 HTTPS(TLS 1.2+)를 통해 `Set-Cookie`로 강제되며, `secure`, `httpOnly`, `sameSite=Lax/Strict` 속성을 적용합니다.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그로 답변)

### Q1 — 세션 검증 레이턴시 예산 (NFR-P1 / Performance)
모든 API 요청마다 U6 게이트웨이가 U3.SessionVerifier를 호출하여 세션을 동기 검증합니다. U3 세션 검증 컴포넌트의 단독 레이턴시 목표(성능 예산)는 어떻게 설정합니까?

A) **극도의 저지연 (P50 < 5ms, P99 < 20ms)**: 세션 검증 오버헤드가 전체 API 응답 속도에 영향을 주지 않도록 인메모리 스토리지 계층을 보장함.

B) **일반적인 저지연 (P50 < 20ms, P99 < 80ms)**: 세션 검증을 위해 RDBMS 또는 범용 NoSQL 스토리지를 조회하는 시간 허용.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 세션 검증은 시스템에 가해지는 모든 요청의 'Gate' 역할을 하므로, **극도의 저지연 (P50 < 5ms, P99 < 20ms)**을 만족해야만 비즈니스 요청 처리율(TPS)에 병목을 유발하지 않는다. 이를 달성하기 위해 메모리 기반 스토리지 계층 배치가 필수적이다.


### Q2 — Python Argon2id 라이브러리 선정 (SEC-12 / Tech Stack)
비밀번호 해싱 및 검증을 담당할 Python 패키지로 무엇을 사용합니까?

A) **`argon2-cffi`**: C언어 원본 Argon2 구현을 CFFI로 바인딩하여 속도가 가장 빠르고 보안 패치가 잘 관리되는 업계 표준 라이브러리.

B) **`passlib` (with Argon2 backend)**: 여러 해싱 알고리즘을 추상화하여 관리하기 쉬우나 추가적인 종속성이 발생함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. Argon2 공식 C 구현체를 가장 가볍고 빠르게 바인딩하며 메모리 할당 효율이 뛰어난 **argon2-cffi**를 선정한다. passlib은 추상화 레이어가 두꺼워 고부하 Argon2id 연산 시 불필요한 오버헤드가 추가될 수 있다.


### Q3 — 세션 스토리지 장애 가용성 요건 (Session Availability / Resilience)
세션 데이터베이스(SessionStore)에 일시적인 장애가 발생하거나 복구가 필요할 때, 허용되는 서비스 수준은 무엇입니까?

A) **강한 복원력 (세션 유실 최소화)**: 세션 스토리지 장애 발생 시 기존 로그인한 사용자의 세션이 유실되지 않고 유지되어야 함 (고가용성 다중화 필수).

B) **약한 복원력 (세션 파기 허용)**: 장애 조치(Failover) 또는 세션 스토리지 초기화 시 로그인 데이터가 일부 유실되어 사용자가 재로그인하는 것은 허용함 (인메모리 단일 노드 또는 캐시 수준의 단순 스토리지 구성 허용).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 세션 스토리지가 유실되면 활동 중인 모든 유저가 동시 로그아웃되는 대규모 장애가 발생하므로, **강한 복원력(세션 유실 최소화)**을 지향한다. 고가용성(Multi-AZ 복제 및 Failover 자동화)이 보장되는 클러스터 구조를 기반으로 Non-Functional Requirements 요건을 명세한다.


### Q4 — 영속성 스토리지(Credential & Session DB) 기술 선정 (SEC-8 / Tech Stack)
계정 자격증명(`CredentialStore`)과 세션 상태(`SessionStore`)를 보관할 AWS 관리형 데이터베이스 기술로 무엇을 선정합니까?

A) **Amazon RDS(PostgreSQL) [자격증명] + Amazon ElastiCache(Redis) [세션]**: 자격증명은 안전한 RDBMS 트랜잭션으로 관리하고, 세션은 저지연(Q1=A) 및 TTL을 지원하는 Redis 캐시를 결합하여 성능 극대화 (복합 스택 구성).

B) **Amazon DynamoDB [자격증명 및 세션 통합]**: 데이터베이스 구조를 단순화하고 인프라 관리 포인트를 일원화함. 세션은 DynamoDB의 TTL(Time-To-Live) 기능을 활용해 자동 파기함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. 정형화된 계정 정보 및 암호 자격증명은 강한 일관성과 ACID 트랜잭션이 보장되는 **Amazon RDS(PostgreSQL)**에 안전하게 격리하고, Q1 및 Q3의 요구사항(초저지연, 고가용성 복원력)을 완벽히 충족하기 위해 세션 저장소는 자동 TTL과 인메모리 복제를 지원하는 Amazon ElastiCache(Redis) 복합 스택을 채택한다.


### Q5 — 봇 차단 CAPTCHA 연동 스택 (SEC-11 / Tech Stack)
대량 가입 및 무차별 로그인 대입 시 봇 필터링을 위해 연동할 CAPTCHA 기술 스택은 무엇을 선정합니까?

A) **AWS WAF CAPTCHA**: 인프라(WAF) 계층에서 CAPTCHA를 연동하여 애플리케이션 코드를 간결하게 유지하고 에지에서 차단함.

B) **Google reCAPTCHA v3**: 백엔드 애플리케이션에서 직접 Google reCAPTCHA API를 호출해 점수(Score) 기반으로 봇을 판단 및 완화함.

C) **Mock CAPTCHA (로컬 스텁)**: v1 출시 단계에서는 외부 CAPTCHA 비용 및 연동 복잡성을 줄이기 위해 mock/스텁 구현체로 대체함.

D) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. Function Design 단계에서 '3회 실패 시 백오프, 10회 실패 시 도메인 레이어 CAPTCHA 검증 신호 강제'라는 세밀한 비즈니스 규칙 기반의 제어를 결정했으므로, 인프라 단에서 무조건 차단하는 AWS WAF보다는 백엔드 애플리케이션 흐름 내에서 유연한 점수(Score) 제어가 가능한 Google reCAPTCHA v3를 백엔드에 직접 연동한다.


### Q6 — 이메일 인증 발송 인프라 선정 (SEC-11 / Tech Stack)
가입 시 `PENDING` 상태 계정의 본인 인증을 위해 발송하는 이메일 전송 인프라로 무엇을 선정합니까?

A) **Amazon SES (Simple Email Service)**: AWS 네이티브 Simple Email Service를 연동하여 이메일을 발송하고 샌드박스를 해제하여 사용함.

B) **Mock SMTP / Local Console Logging**: 개발 환경 및 v1 범위 고려 시 외부 SES 연결 없이 로그 또는 mock 이메일 핸들러를 사용해 인증 토큰 값을 콘솔에 출력함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. PENDING 계정의 이메일 활성화는 가입 흐름의 핵심 도메인 규칙이므로, 인프라 구성 단계부터 실제 운영 환경을 고려해 Amazon SES (Simple Email Service) 연동 프로토콜을 규격화한다. (단, 로컬 개발/테스트 환경 환경변수에 따라 가짜 핸들러로 스위칭될 수 있도록 추상화 설계 적용)
