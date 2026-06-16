# business-rules.md — U3 Accounts 비즈니스 규칙 및 검증 설계

**단계**: CONSTRUCTION → Functional Design (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/plans/u3-accounts-functional-design-plan.md` (Q1~Q7 답변 반영)

---

## 1. 비즈니스 결정 규칙 (Business Rules)

### BR-A1: 비밀번호 강도 및 오프라인 유출 검사 정책 (Q1 반영)
- **비밀번호 강도 규칙**:
  - 비밀번호의 길이는 반드시 **10자 이상**이어야 한다 (SEC-12).
  - 영문 대문자, 영문 소문자, 숫자, 특수문자를 각각 최소 1개 이상 포함해야 한다.
- **오프라인 유출 검사**:
  - 외부 API 가용성 위스크(Availability Risk)를 방지하기 위해 로컬 1만 개 다빈도 취약 패스워드 블랙리스트 파일(Static File/Memory Map)을 사용해 검증한다.
  - 가입 요청 비밀번호가 블랙리스트에 포함된 경우 `POLICY_VIOLATION` 에러 사유로 가입이 거절된다.

### BR-A2: Argon2id 비밀번호 해싱 규칙 (Q2 반영)
- 저장소에 저장될 사용자의 비밀번호 해시는 반드시 **Argon2id** 단방향 KDF를 통해 생성되어야 한다 (SEC-12).
- **권장 파라미터 세트**:
  - `m` (Memory Cost): `65536` (64 MB)
  - `t` (Time Cost / Iterations): `3`
  - `p` (Parallelism): `4` (스레드 수)
  - `salt`: 암호학적으로 안전한 의사 난수 생성기(CSPRNG)를 사용하여 최소 16바이트의 고유 솔트를 생성해 주입한다.

### BR-A3: 복합 세션 수명 및 만료 정책 (Q3 반영)
- 세션의 생명주기는 Sliding Expiration과 Absolute Expiration을 동시에 적용해 강제한다 (SEC-12).
- **Idle Timeout (Sliding)**:
  - 세션이 마지막으로 사용된 시각(`lastActiveAt`)으로부터 **2시간**이 경과하면 해당 세션은 서버측에서 즉시 만료 및 파기된다.
- **Maximum Lifetime (Absolute)**:
  - 세션이 최초로 생성된 시각(`createdAt`)으로부터 **30일**이 경과하면, 사용자의 지속적인 요청 활동 여부와 무관하게 해당 세션은 강제로 즉시 만료 및 파기된다.

### BR-A4: 로그인 무차별 대입 방어 정책 (Q4 반영)
- 임시 계정 잠금(Lockout)으로 인해 유발되는 타인의 정상 계정 DoS 공격을 방어하기 위해 계정을 잠그지 않는 **점진적 응답 지연 + CAPTCHA 강제**를 비즈니스 규칙으로 정의한다 (SEC-12).
- **실패 횟수별 대처**:
  - **1~2회 연속 실패**: 일반 실패 처리 (지연 없음).
  - **3~9회 연속 실패**: 로그인 응답 시간을 `2^(실패 횟수 - 3)` 초만큼 점진적으로 지연(Backoff Delay)시킨다 (스레드 지연).
  - **10회 이상 연속 실패**: 로그인 API 요청 시 프런트엔드 CAPTCHA 인증 토큰 제출 및 검증을 필수 조건으로 추가 강제한다.

### BR-A5: 가입 인증을 통한 봇 및 허위 가입 완화 (Q5 반영)
- 가입 완료 시 사용자는 즉시 로그인할 수 없다.
- **가입 후 계정 라이프사이클**:
  - 가입 완료 시 계정 상태는 `AccountStatus.PENDING`으로 등록된다.
  - 가입과 동시에 이메일로 전송된 24시간 유효의 인증 링크(암호학적 토큰)를 사용자가 클릭하여 `GET /auth/verify-email?token=...` 검증이 통과될 때만 상태가 `AccountStatus.ACTIVE`로 전환된다.
  - 가입 후 24시간 동안 `PENDING` 상태를 탈출하지 못한 계정은 비즈니스 규칙에 의해 배치 작업 등으로 저장소에서 자동 정리된다.

### BR-A6: Stateless 기본 거부 및 소유권 인가 (Q6 반영)
- U3의 `AuthorizationGuard`는 타 유닛의 비즈니스 데이터 모델이나 스키마에 결합되지 않도록 **완전한 Stateless 인가 결정**을 수행한다.
- **인가 매개변수 바인딩**:
  - 호출자(U4, U6 등)는 직접 DB를 조회하여 객체의 소유자 식별자(`resourceOwnerId`)를 획득한 뒤 `AuthorizationGuard.authorize(principal, action, resourceOwnerId)`를 호출해야 한다.
  - Guard는 `principal.userId == resourceOwnerId` 조건만을 검증하여 승인(`ALLOW`) 또는 기본 거부(`DENY`)를 반환한다 (SEC-8).

### BR-A7: 관리자(Admin) 권한 생성 및 MFA 강제 (Q7 반영)
- 일반적인 공개 가입 API(`/auth/signup`)를 통한 역할(`ADMIN`) 설정 계정 생성은 원천 차단된다.
- **관리자 규칙**:
  - 관리자 계정은 인프라 배포 시 DB 시딩(Seeding) 또는 지정된 관리용 환경변수/스크립트로만 사전에 주입 및 생성 가능하다.
  - 주체(Principal)의 역할이 `ADMIN`일 경우, 일반적인 세션 토큰 검증 외에 **TOTP(RFC 6238) 기반 MFA 다요소 인증**이 통과되었음이 보안 컨텍스트에 기록되어야만 관리자 전용 제어 평면 API에 접근을 허용한다.

---

## 2. 보안 및 개인정보 보호 불변식 (SEC Rules)

### SEC-BR-1: 민감 정보 로그 노출 방지 (SEC-3)
- 비밀번호 평문, 세션 토큰 문자열, 이메일 인증 토큰, 복호화용 임시 자격증명 등은 어떠한 경우에도 애플리케이션 로그(`structlog` 등)에 기록되어서는 안 된다.
- 로그 메시지 출력 전 필터 이음새를 구성하여 `password`, `token` 등의 필드를 마스킹 또는 원천 배제한다.

### SEC-BR-2: 자격증명 존재 여부 비노출 (SEC-9/12)
- 로그인 실패, 가입 시 이메일 중복 등의 시나리오에서 시스템은 구체적으로 어떤 자격증명이 일치하지 않거나 중복되었는지를 알리지 않는다.
- 로그인 오류 시 "이메일 또는 비밀번호가 올바르지 않습니다." 등의 통합 오류 메시지를 응답한다.

### SEC-BR-3: 예외 발생 시 안전 거부 (Fail-Closed) (SEC-15)
- 세션 스토리지 장애, KDF 모듈 오류 등 예외 상황이 발생할 경우, 인가 및 인증 판정은 항상 거부(`DENY`, 401/403)로 종결되어야 한다. 시스템이 오류로 인해 보호막이 열린 채로 실행되는 상태를 방지한다.

---

## 3. PBT 속성 정의 (Property-Based Testing Properties)

### PBT-U3-1: 비밀번호 강도 검증의 멱등성 및 정합성 (PBT-02)
- **속성**: 임의의 무작위 생성 알파뉴메릭 문자열 중 길이 10자 미만이거나, 대소문자/숫자/특수문자가 결여되었거나, 로컬 블랙리스트에 포함된 경우 `PasswordPolicy.evaluate` 결과는 항상 `false`여야 하며, 이를 모두 통과한 비밀번호는 항상 `true`여야 한다.

### PBT-U3-2: 자격증명 해싱 및 검증 일관성 (PBT-03)
- **속성**: 임의의 평문 비밀번호 문자열 `P`에 대해 Argon2id를 적용해 생성한 비밀번호 해시 `H`가 있을 때, 동일한 비밀번호 `P`를 사용한 `verifyCredential`의 결과는 항상 `true`이고, `P`와 다른 임의의 무작위 문자열 `P'`를 사용한 검증 결과는 항상 `false`이다 (상수시간 처리 유지).

---

## 4. 추적성 매트릭스 (Traceability Matrix)

| 설계 요소 (컴포넌트/규칙) | 추적 대상 요구사항 ID | 인수 기준 스토리 ID | 설계 목적 및 불변식 |
|---|---|---|---|
| **AccountController** | FR-7, SEC-5, SEC-12, SEC-15 | US-A1, US-A2 | 가입/로그인 API 노출 및 입력 데이터 검증, 예외 상황 Fail-Closed 처리 |
| **SignupService** | FR-7, SEC-11, SEC-12, SEC-3 | US-A1, US-H1 | 신규 사용자 셀프 가입 오케스트레이션 및 중복 가입 신호 발행 |
| **AuthenticationService** | FR-7, SEC-12, SEC-15 | US-A2 | 로그인 및 자격증명 검증, 무차별 대입 지연 적용 |
| **SessionManager** | FR-7, SEC-8, SEC-12 | US-A2 | 세션 토큰 발급 및 수명주기(Sliding/Absolute 만료) 관리 |
| **AuthorizationGuard** | SEC-8, SEC-12, SEC-15 | US-A2, US-L1..L3 | **Stateless 객체 단위 소유권 인가 판단 단일 권위점** 및 관리자 MFA 검증 |
| **CredentialStore** | FR-7, SEC-12, SEC-3 | US-A1, US-A2 | Argon2id 적응형 해싱 및 상수시간 연산 비교 구현, 민감정보 비로깅 |
| **PasswordPolicy** | SEC-12 | US-A1 | 최소 10자 복잡도 및 로컬 취약 패스워드 블랙리스트 오프라인 검증 |
| **BR-A3 (세션 만료 정책)** | SEC-12 | US-A2 | 2시간 비활성 Sliding + 30일 절대 만료 강제 |
| **BR-A4 (브루트포스 방어)** | SEC-12 | US-A2 | 점진적 Exponential Backoff 지연을 통한 Lockout DoS 방어 |
| **BR-A5 (이메일 인증)** | SEC-11 | US-A1 | 가입 시 PENDING 계정 생성 후 이메일 인증 토큰 강제로 봇 계정 양산 방어 |
| **SEC-BR-1 (구조화 로그)** | SEC-3 | US-A1, US-A2 | 패스워드, 세션 토큰 등의 로그 출력 필터 마스킹 불변식 |
| **PBT-U3-1 / PBT-U3-2** | PBT-02, PBT-03 | US-A1, US-A2 | PBT 기반 자격증명 정책 및 해싱 검증의 무결성 테스트 보장 |
