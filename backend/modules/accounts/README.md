# U3 Accounts/Auth 모듈

본 모듈은 DocSuri 시스템의 회원가입, 로그인 인증, 세션 생명주기 관리 및 Stateless 객체 단위 소유권 인가를 처리하는 핵심 보안 서비스입니다. (Track 2 - U3 Accounts)

## 1. 컴포넌트 목록 및 역할

- **`controller.py`**: FastAPI 기반의 `/auth/...` 라우터와 HTTP 엔드포인트를 노출합니다.
- **`services/signup.py`**: 비밀번호 정책 및 이메일 활성화 토큰 발급, 메일 발송 흐름을 오케스트레이션합니다.
- **`services/auth.py`**: 자격증명을 검증하고 로그인 실패 횟수에 따른 지수 백오프 및 reCAPTCHA 처리를 강제합니다.
- **`services/session_manager.py`**: Redis 상의 세션 발급, 무효화 및 Sliding(2시간)/Absolute(30일) 복합 만료를 판정합니다.
- **`guard.py`**: 순수 Stateless 형태로 `principal.userId == resourceOwnerId` 일치 및 ADMIN MFA 검증을 수행합니다.
- **`password.py`**: 10자 이상 복잡도 필터 및 **1만개 취약 패스워드 블랙리스트 메모리 캐싱 O(1) 대조**를 지원합니다.
- **`integrations/`**: reCAPTCHA v3 API (`recaptcha.py`) 및 AWS SES 이메일 발송 (`email.py`) 연동부입니다.
- **`repository/`**: PostgreSQL 영속 데이터 매핑 (`credential.py`) 및 aioredis 커넥션 제어 (`session.py`)를 수행합니다.

---

## 2. API 엔드포인트 규약

| 엔드포인트 | HTTP 메서드 | 설명 | 주요 에러 응답 |
|---|---|---|---|
| `/auth/signup` | POST | PENDING 상태로 신규 가입 신청 및 인증 메일 발송 | 400 (중복/정책위반) |
| `/auth/verify-email`| GET | 토큰 검증 후 계정을 ACTIVE로 활성화 | 400 (만료/부존재) |
| `/auth/login` | POST | 인증 후 `session_id` 보안 쿠키 발급 | 401 (자격증명 불일치) |
| `/auth/session` | GET | 세션 유효성 확인 및 Sliding 만료 시간 연장 | 401 (세션만료) |
| `/auth/logout` | POST | 세션 즉각 무효화 및 브라우저 보안 쿠키 파기 | - |

---

## 3. 핵심 아키텍처 및 복원력(Resiliency) 설계 규칙

### 3.1. 세션 저장소 장애 Fail-Closed 정책 (NFR-Design)
- 세션 유실 방지를 위해 ElastiCache Redis를 Multi-AZ 복제 클러스터로 가동합니다.
- Redis 통신 중 장애(`ConnectionError`, `TimeoutError`)가 발생할 경우, **데이터베이스로 폴백(Fallback)하지 않고 즉시 인증 요청을 차단(Fail-Closed, 401 Unauthorized)**하여 데이터베이스가 세션 트래픽에 의해 스로틀링(Throttling)되는 현상을 원천 방지합니다.

### 3.2. 로그인 백오프 지연 스레드 고갈 방지 (DoS Defend)
- 로그인 3회 이상 실패 시 응답 속도를 지수 백오프(`2^(failure_count - 3)`)초 동안 지연시킵니다.
- 서버 스레드 차단 DoS 공격을 차단하기 위해, 동기식 `time.sleep()` 대신 FastAPI 비동기 이벤트 루프를 사용하는 **`await asyncio.sleep(...)`** 비블로킹(Non-blocking) 메커니즘을 적용하여 리소스를 타 요청에 효율적으로 양보합니다.

### 3.3. 이메일 발송 소프트 폴백 (Soft-Fallback)
- 이메일 전송에 장애가 발생하더라도 계정 가입 자체를 롤백시키지 않습니다. 계정은 PENDING 상태를 안전하게 유지하며, `EmailDeliveryFailureSignal` 메트릭과 경보 구조화 로그가 비동기로 발행되어 재시도 큐 등으로 흘러갑니다.

### 3.4. Stateless 인가 시그니처 (Stateless Decoupling)
- `AuthorizationGuard`가 타 모듈의 테이블에 결합되지 않도록, 인자로 리소스 소유자의 키를 직접 전달받아 순수 논리 대조만 수행합니다:
  ```python
  AuthorizationGuard.authorize(principal: Principal, action: Action, resource_owner_id: AccountId)
  ```

---

## 4. 로컬 개발 및 Mocking 설정

로컬 환경이나 CI 환경 등 실제 Amazon SES 인프라가 없는 경우, 환경변수 `ENV=local` 또는 `SES_MOCK=true`로 기동하면 실제 메일 전송 대신 콘솔 터미널 출력으로 활성화 토큰 링크를 쉽게 디버깅할 수 있습니다.

```bash
# 로컬 Mocking 활성화 실행 예시
export ENV=local
export SES_MOCK=true
```
