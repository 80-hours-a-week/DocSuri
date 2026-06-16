# tech-stack-decisions.md — U3 Accounts 기술 스택 결정서 (ADR)

**단계**: CONSTRUCTION → NFR Requirements · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/plans/u3-accounts-nfr-requirements-plan.md` (Q1~Q6 답변 반영), `tech-stack-decisions.md` [U1 Ingestion] 상속 규칙

---

## TD-U3-1 [상속] — 언어 및 런타임: **Python 3.12+**
- **결정**: 모듈형 모놀리스 API 배포 단위(①)의 전체 결정에 따라 Python을 백엔드 언어로 상속하여 사용합니다.
- **근거**: U1/U2/U6와의 아키텍처적 일관성 유지 및 모듈 간 의존성 결선 unblocked.

---

## TD-U3-2 — 비밀번호 해싱 라이브러리: **`argon2-cffi`**
- **결정**: 사용자의 자격증명 해싱 및 상수시간 연산 검증을 위해 Python 라이브러리 `argon2-cffi`를 사용합니다 (Q2 답변 반영).
- **근거**:
  - Argon2 공식 C 구현체를 가장 고성능 및 저지연으로 바인딩하여 백엔드 CPU/메모리 연산 오버헤드를 극소화합니다.
  - 최신 OWASP 암호학 표준인 Argon2id KDF 포맷을 제공하며, GPU 병렬 무차별 대입 공격에 강한 저항성을 제공합니다 (SEC-12).
- **대안**: `passlib` (두꺼운 추상화 계층으로 인해 해싱 연산 오버헤드가 발생하고 종속성이 무거움).

---

## TD-U3-3 — 영속성 스토리지 스택: **Amazon RDS(PostgreSQL) + Amazon ElastiCache(Redis)**
- **결정**: 사용자 자격증명 영속화는 **Amazon RDS (PostgreSQL)**로 처리하고, 활성 세션 보관은 **Amazon ElastiCache (Redis)** 복합 구성을 적용합니다 (Q4 답변 반영).
- **근거**:
  - **자격증명 (RDS PostgreSQL)**: 이메일 고유성(Unique Index) 강제 및 사용자 계정 데이터의 엄격한 ACID 트랜잭션, 관계형 도메인 정규화 구조를 완벽하게 보장합니다 (SEC-8).
  - **세션 (ElastiCache Redis)**: 세션 검증 레이턴시 예산(P50 < 5ms, NFR-P1)을 충족하기 위한 초고속 인메모리 조회 및 자동 만료(TTL) 필드를 기본 지원하며, Multi-AZ 복제 클러스터를 통해 유실 방지 가용성을 제공합니다 (Q3=A).
- **대안**: Amazon DynamoDB (데이터 모델은 단순해지나 세션 검증 성능 예산 만족 및 Sliding Expiration 갱신 시의 DB 비용 오버헤드가 발생함).

---

## TD-U3-4 — 봇 차단 CAPTCHA 서비스: **Google reCAPTCHA v3**
- **결정**: 비정상 로그인 및 봇 남용 방어를 위해 **Google reCAPTCHA v3**를 연동합니다 (Q5 답변 반영).
- **근거**:
  - 사용자에게 수동으로 글자를 맞추거나 그림을 고르도록 강제하여 UX를 깨뜨리는 대신, 행동 기반의 점수(Score, 0.0 ~ 1.0)를 백엔드로 전달받아 유연한 비즈니스 로직 제어가 가능합니다.
  - 로그인 10회 연속 실패 시에만 도메인 레이어에서 CAPTCHA 인증 검증을 요구하는 Functional Design 규칙(BR-A4)을 유연하게 구현할 수 있습니다 (SEC-11).
- **대안**: AWS WAF CAPTCHA (네트워크/인프라 계층에서 강제 차단하므로 비즈니스 논리 기반의 점진적 지연 백오프 제어가 불가능함).

---

## TD-U3-5 — 이메일 발송 인프라: **Amazon SES (Simple Email Service)**
- **결정**: PENDING 계정의 이메일 본인 인증 토큰 링크 발송을 위해 **Amazon SES**를 연동합니다 (Q6 답변 반영).
- **근거**:
  - AWS 환경에 네이티브하게 통합되며 높은 도메인 신뢰도와 발송 속도를 제공합니다.
  - **로컬 스위칭 설계**: 로컬 개발 및 테스트 환경에서는 실제 메일이 발송되지 않도록 환경 변수에 따라 `MockEmailHandler`가 콘솔 터미널에 인증 링크 및 토큰 값을 출력하도록 추상화 인터페이스를 설계합니다.
- **대안**: 자체 SMTP 서버 구축 (운영 부담 및 스팸 메일 분류 위험 높음).

---

## TD-U3-6 [상속] — PBT 및 테스트 도구: **Hypothesis**
- **결정**: 자격증명 강도 검증 및 해싱 멱등성 검사(PBT-U3-1/2)를 위해 Python의 `Hypothesis` PBT 프레임워크를 상속하여 테스트를 작성합니다.
- **근거**: U1/U2와의 일관성 유지 및 강력한 속성 기반 수축(Shrinking) 테스트 지원.
