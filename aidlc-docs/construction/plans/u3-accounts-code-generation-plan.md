# u3-accounts-code-generation-plan.md — U3 Accounts 코드 생성 계획서

**단계**: CONSTRUCTION → Code Generation (Part 1 - Planning) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/u3-accounts/functional-design/` (도메인, 비즈니스 모델, 비즈니스 규칙), `construction/u3-accounts/nfr-requirements/` (기술 스택), `construction/u3-accounts/nfr-design/` (Redis Fail-Closed, SES/reCAPTCHA 폴백, 풀 제한), `construction/u3-accounts/infrastructure-design/` (Fargate, RDS PostgreSQL, ElastiCache Redis, VPC 격리, SES 도메인)
**피드백 반영**: 사용자 피드백 ①(블랙리스트 메모리 set 캐싱), ②(Redis max 50 풀 및 예외 래핑), ③(FastAPI asyncio.sleep 비동기 스레드 고갈 방지), ④(AuthorizationGuard resource_owner_id 명시 인자화)
**문서 언어**: 한국어

---

## 1. 유닛 컨텍스트 및 구현 대상 (Step 1 & Step 3)

U3 Accounts 유닛은 시스템 전체의 계정 관리, 회원가입(Signup), 로그인 인증(Authentication), 세션 관리(Session Management) 및 Stateless 인가(Authorization)를 담당하는 핵심 보안 모듈입니다.

### 1.1. 구현 대상 스토리 (Story Mapping)
- **US-A1 (회원가입 및 이메일 인증)**: 일반 공개 가입 시 `PENDING` 상태 등록 및 SES 인증 메일 발송, 토큰 검증 후 `ACTIVE` 전환.
- **US-A2 (인증 및 세션 만료)**: 로그인 성공 시 보안 세션 발급, Sliding(2h)/Absolute(30d) 세션 만료 검증 및 갱신, 10회 연속 실패 시 CAPTCHA 요구, 3회 이상 실패 시 Exponential Backoff 적용.
- **US-H1 (히어로 스토리 - 통합 플로우)**: 가입부터 논문 검색 및 이력 조회까지 이어지는 전체 엔드투엔드 유저 흐름에서의 인증 통과 보장.
- **US-L1..L3, US-D1..D7 (인가 의존)**: 타 모듈(U2, U4)이 객체 단위 소유권 조회를 수행할 때 `AuthorizationGuard`를 통해 Stateless 인가 결정(`ALLOW`/`DENY`) 제공.
- **US-R1..R5 (신뢰성 및 장애 복원)**: Redis 세션 캐시 장애 시 RDS 세션 폴백 없이 Fail-Closed 처리, reCAPTCHA 실패 시 로그인 Fail-Closed, SES 발송 실패 시 소프트폴백(`EmailDeliveryFailureSignal` 이벤트 발행) 대응.

### 1.2. 타 모듈 의존성 및 인터페이스
- **shared/dtos.md**: `SignupRequest`, `SignupResult`, `LoginRequest`, `SessionInfo`
- **shared/events.md**: `AccountCreated`, `SignupAbuseSignal`, `AuthFailureSignal`
- **shared/ports.md**: `ObservabilityHub` (U3에서 발생하는 메트릭 및 로그 구조화 수집용)

### 1.3. 소유 데이터베이스 엔티티 및 스토어
- **RDS PostgreSQL (CredentialStore)**: `Account` 테이블 (id, email, password_hash, status, created_at, failure_count, last_failed_at) 및 `EmailVerificationToken` 테이블 (token, email, expires_at).
- **ElastiCache Redis (SessionStore)**: `SessionRecord` 키-값 쌍 (session_handle -> JSONString {user_id, created_at, last_active_at, expires_at}).

---

## 2. 상세 코드 생성 계획 (Step 2)

> 코드 작성 경로는 `backend/modules/accounts/` 및 `tests/accounts/` 입니다.
> 모든 생성 작업은 아래의 세부적인 순서에 따라 차례대로 진행되며, 완료 시 `[x]` 처리됩니다.

### Phase 1: 파일 스케폴딩 및 리소스 정의
- [x] **Step 1: 디렉터리 구성 및 1만개 최다 취약 패스워드 블랙리스트 리소스 복사**
  - 경로: `backend/modules/accounts/resources/common_passwords.txt`
  - 내용: OWASP 기준 흔히 쓰이는 비밀번호 1만 개 목록 로드용 텍스트 파일 배치.
  - 스토리: US-A1, BR-A1
- [x] **Step 2: Pydantic DTO 스키마 작성 및 공유 계약 연동**
  - 경로: `backend/modules/accounts/schemas.py`
  - 내용: `shared/dtos.md` 스펙을 만족하는 `SignupRequest`, `SignupResult`, `LoginRequest`, `SessionInfo` 클래스 정의.
  - 스토리: US-A1, US-A2

### Phase 2: 도메인 엔티티 및 정책 정의
- [x] **Step 3: 도메인 데이터 모델 및 예외 정의**
  - 경로: `backend/modules/accounts/models.py`
  - 내용: `AccountId`, `EmailAddress`, `AccountStatus`, `Principal`, `Action` 등의 값 객체와 도메인 예외 정의.
  - 스토리: US-A1, US-A2, BR-A6
- [x] **Step 4: 비밀번호 복잡도 및 블랙리스트 검증기 작성**
  - 경로: `backend/modules/accounts/password.py`
  - 내용: `PasswordPolicy` 정의. 최소 10자, 대소문자/숫자/특수문자 포함 검사 구현.
  - **설계 규칙 (피드백 ① 반영)**: `common_passwords.txt` 로드는 모듈 초기 기동 시 단 1회 수행되어 메모리 내 `set` 구조에 캐싱되어야 하며, 실제 유출 패스워드 대조 시 파일 I/O 없이 $O(1)$ 시간 복잡도로 즉시 수행되어야 함.
  - 스토리: US-A1, BR-A1

### Phase 3: 외부 인프라 연동 구현 (Mocking 지원)
- [x] **Step 5: Google reCAPTCHA v3 백엔드 인증 클라이언트 작성**
  - 경로: `backend/modules/accounts/integrations/recaptcha.py`
  - 내용: reCAPTCHA v3 HTTP API 호출 및 점수 검증. Fail-Closed 원칙 적용.
  - 스토리: US-A2, BR-A4, TD-U3-4
- [x] **Step 6: Amazon SES 이메일 인증 링크 발송 클라이언트 및 로컬 Mock 구현**
  - 경로: `backend/modules/accounts/integrations/email.py`
  - 내용: SES `boto3` 발송 모듈 작성. 환경변수(`ENV=local`) 시 실제 전송 대신 터미널 로그로 링크 출력하는 `MockEmailClient` 스위칭 제공. 실패 시 소프트폴백(`EmailDeliveryFailureSignal` 로그/이벤트 연동).
  - 스토리: US-A1, BR-A5, TD-U3-5

### Phase 4: 스토리지 레포지토리 계층 구현
- [x] **Step 7: PostgreSQL CredentialStore (SQLAlchemy 기반) 레포지토리 작성**
  - 경로: `backend/modules/accounts/repository/credential.py`
  - 내용: 사용자 계정 영속화 및 `verify-all-then-commit` 원칙 준수. 타이밍 공격 방어 더미 연산용 상수시간 비교 래퍼 포함.
  - 스토리: US-A1, US-A2, TD-U3-3
- [x] **Step 8: Redis SessionStore 레포지토리 작성**
  - 경로: `backend/modules/accounts/repository/session.py`
  - 내용: `redis-py` 기반 세션 정보 조회/저장/삭제.
  - **설계 규칙 (피드백 ② 반영)**: `redis.ConnectionPool(max_connections=50, socket_timeout=2.0)`을 명시적으로 사용해 전용 풀을 구성하고, 연결 시 `redis.exceptions.ConnectionError` 및 `TimeoutError`가 발생하면 비즈니스 예외인 `SessionStoreUnavailableException`으로 래핑하여 상위 레이어로 Fail-Closed 신호 전파.
  - 스토리: US-A2, TD-U3-3, BR-A3

### Phase 5: 비즈니스 로직 및 세션 제어 서비스 구현
- [x] **Step 9: SignupService (회원가입 오케스트레이터) 구현**
  - 경로: `backend/modules/accounts/services/signup.py`
  - 내용: 회원가입 신청, 비밀번호 강도 검사, 중복 이메일 체크, `PENDING` 등록, 인증 이메일 토큰 발급 및 발송, 인증 토큰 유효 검증 및 `ACTIVE` 전환 로직.
  - 스토리: US-A1, BR-A1, BR-A5, US-H1
- [x] **Step 10: AuthenticationService 및 SessionManager 구현**
  - 경로: `backend/modules/accounts/services/auth.py` 및 `backend/modules/accounts/services/session_manager.py`
  - 내용: 로그인 자격증명 비교, 실패 횟수별 지연 및 CAPTCHA 요구 플래그 설정, Sliding(2h)/Absolute(30d) 세션 발급 및 요청별 실시간 검증/갱신 로직.
  - **설계 규칙 (피드백 ③ 반영)**: 로그인 3회 이상 실패 시 응답을 지연시키는 Exponential Backoff 구현 시, 동기식 `time.sleep()`을 호출하여 서버의 워커 스레드가 고갈(Thread Exhaustion DoS)되는 일을 원천 방지해야 함. 백엔드가 FastAPI 기반이므로 비동기 `async def` 핸들러 및 `await asyncio.sleep(...)`을 사용하여 이벤트 루프 상에서 리소스를 차단하지 않고 양보하는 비동기 지연 메커니즘을 적용함.
  - 스토리: US-A2, BR-A3, BR-A4, US-H1
- [x] **Step 11: AuthorizationGuard (Stateless 소유권 인가 판단기) 구현**
  - 경로: `backend/modules/accounts/guard.py`
  - 내용: `principal.userId == resourceOwnerId` 단순 일치 검증 및 관리자 TOTP MFA 검증을 처리하는 Stateless Guard.
  - **설계 규칙 (피드백 ④ 반영)**: 순수한 Stateless 인가를 유지하기 위해 `AuthorizationGuard.authorize(principal: Principal, action: Action, resource_owner_id: AccountId)` 형태의 시그니처를 설계하며, 인자로서 타 서비스가 사전에 조회한 리소스 소유자 식별자(`resource_owner_id`)를 명시적으로 수신함.
  - 스토리: BR-A6, BR-A7, US-L1..L3

### Phase 6: API 라우터 및 미들웨어 통합
- [x] **Step 12: AccountController (FastAPI 라우터) 구현**
  - 경로: `backend/modules/accounts/controller.py`
  - 내용: `/auth/signup`, `/auth/login`, `/auth/verify-email`, `/auth/session` API 엔드포인트 정의. 보안 쿠키(`httpOnly`, `secure`, `sameSite=Lax`) 설정 및 일반화된 예외 처리 적용.
  - 스토리: US-A1, US-A2, SEC-BR-2, SEC-BR-3

### Phase 7: 단위 및 속성 기반 테스트 (PBT) 작성
- [x] **Step 13: PasswordPolicy PBT 단위 테스트 작성**
  - 경로: `tests/accounts/test_password_pbt.py`
  - 내용: `Hypothesis`를 이용하여 다양한 패스워드 생성 인풋에 따른 `PasswordPolicy.evaluate`의 멱등성 및 조건 정합성 검증 (PBT-U3-1).
  - 스토리: US-A1, PBT-U3-1
- [x] **Step 14: Argon2id 해싱 일관성 PBT 단위 테스트 작성**
  - 경로: `tests/accounts/test_hash_pbt.py`
  - 내용: `Hypothesis` 기반 임의 비밀번호 비교 일관성 및 상수시간 동작 보장 검증 (PBT-U3-2).
  - 스토리: US-A2, PBT-U3-2
- [x] **Step 15: 서비스 및 세션 만료 정책 통합 단위 테스트 작성**
  - 경로: `tests/accounts/test_services.py` 및 `tests/accounts/test_session.py`
  - 내용: 회원가입, 로그인 실패 백오프, Sliding/Absolute 세션 타임아웃 모킹 테스트.
  - 스토리: US-A1, US-A2

### Phase 8: 마이그레이션 스크립트 및 문서화
- [x] **Step 16: PostgreSQL DDL 마이그레이션 스크립트 작성**
  - 경로: `backend/modules/accounts/migrations/001_create_accounts_table.sql`
  - 내용: `Account` 및 `VerificationToken` 스키마 생성을 위한 DDL 파일.
  - 스토리: US-A1, TD-U3-3
- [x] **Step 17: API 및 모듈 사용법 README 작성**
  - 경로: `backend/modules/accounts/README.md`
  - 내용: 엔드포인트 요약, 로컬 모킹 기법, 세션 관리 모듈 연동 가이드 문서화.
  - 스토리: US-A1, US-A2

---

## 3. 완료 기준 (Completion Criteria)

1. `backend/modules/accounts/` 폴더 내에 정의된 17개의 상세 코드 생성 계획 단계가 모두 완료되어 체크박스 `[x]`가 표시됨.
2. `tests/accounts/` 폴더 하위에 Hypothesis PBT 테스트 2종 및 서비스 통합 테스트가 작성됨.
3. 모든 컴포넌트가 `shared/` 스펙(DTO, Event, Port) 및 U3 설계 불변식(Fail-Closed, Non-disclosure, Timing Attack 방어)을 충족함.
