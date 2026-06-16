# business-logic-model.md — U3 Accounts 비즈니스 로직 및 알고리즘 설계

**단계**: CONSTRUCTION → Functional Design (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/plans/u3-accounts-functional-design-plan.md` (Q1~Q7 답변 반영)

---

## 1. 공개 셀프 가입 오케스트레이션 (SignupService.register)

새로운 사용자가 시스템에 계정 등록을 요청할 때 수행되는 오케스트레이션 프로세스입니다.

### 1.1. 가입 등록 알고리즘
1. **입력 수신**: `SignupCommand` (이메일, 평문 비밀번호, 요청 컨텍스트)
2. **비밀번호 정책 검증**:
   - `PasswordPolicy.evaluate(password)`를 호출합니다.
   - 비밀번호 길이가 **10자 이상**이며, **영문 대문자, 소문자, 숫자, 특수문자**가 각각 최소 1개 이상 포함되어 있는지 검증합니다 (Q1 답변 반영).
   - 로컬 1만 개 최다 취약 패스워드 블랙리스트를 조회하여 매칭되는 경우 `POLICY_VIOLATION` 에러를 반환하고 중단합니다 (외부 API 호출은 가용성 보장을 위해 배제).
3. **이메일 유일성(중복) 검증**:
   - `CredentialStore`에서 입력 이메일의 계정 존재 여부를 조회합니다.
   - 만약 이미 가입된 이메일인 경우:
     - 중복 회원가입 요청 임계치(단위 시간당 특정 대역/IP)를 검증하고, 초과 시 `SignupAbuseSignal`을 이벤트 버스로 발행합니다 (SEC-11).
     - 보안 상의 사용자 존재 노출을 차단하기 위해 일반화된 성공 결과처럼 응답하거나(비밀번호 재설정 유도), 일반화된 가입 충돌 응답(`EMAIL_TAKEN`)을 반환합니다 (SEC-9/12).
4. **암호학적 해싱 (Argon2id)**:
   - 보안 난수 생성기를 사용하여 최소 16바이트 크기의 독립 솔트(Salt)를 생성합니다.
   - **Argon2id** KDF 파라미터(OWASP 권장 메모리 하드 강도 기준: m=65536 KB, t=3, p=4)를 적용하여 비밀번호를 단방향 해싱합니다 (Q2 답변 반영).
5. **계정 및 자격증명 영속화**:
   - 계정을 **`PENDING`** 상태(이메일 인증 대기)로 설정하여 저장소에 기록합니다 (Q5 답변 반영).
   - 해싱된 결과값(`PasswordHash`)과 해시 매개변수(`HashParameters`)를 `CredentialStore`에 영속화합니다.
6. **이메일 인증 토큰 생성**:
   - 암호학적으로 안전한 임의의 인증 링크 토큰(24시간 유효)을 생성하여 영속화하고, 사용자 이메일로 링크 발송 이벤트를 발행합니다 (Q5).
7. **도메인 이벤트 발행**:
   - `AccountCreated` 이벤트를 이벤트 백본으로 발행합니다 (민감 정보 제외, PII 최소화).
8. **출력**: 성공 시 `AccountId` 반환.

---

## 2. 로그인 및 자격증명 검증 (AuthenticationService.authenticate)

사용자의 자격증명을 확인하고 세션을 수립하는 프로세스입니다.

### 2.1. 인증 처리 알고리즘
1. **입력 수신**: `LoginCommand` (이메일, 평문 비밀번호, 요청 컨텍스트)
2. **자격증명 조회**:
   - `CredentialStore`에서 입력 이메일에 해당하는 해시값 및 해시 매개변수를 조회합니다.
   - **타이밍 공격 방어 (Constant-Time)**: 만약 일치하는 계정이 존재하지 않는 경우, 임의의 더미 해시값과 비교 연산을 동일한 시간 동안 실행하여 계정 존재 여부가 외부에서 유추되지 않도록 처리합니다 (SEC-12).
3. **자격증명 비교**:
   - 조회한 파라미터(Argon2id)로 입력 비밀번호를 해싱하여 데이터베이스에 저장된 값과 상수시간 내에 비교합니다 (`verifyCredential`).
4. **결과 처리**:
   - **검증 실패 시**:
     - 대상 계정의 실패 횟수(`FailureCount`)를 1 증가시킵니다.
     - `AuthFailureSignal`을 발행하여 보안 관측 시스템에 전달합니다 (SEC-12).
     - **점진적 시간 지연 (Exponential Backoff Delay)**: 실패 횟수가 3회 이상일 경우, `2^(실패 횟수 - 3)` 초 동안 스레드를 인위적으로 대기(delay)한 후 에러를 반환합니다. 10회 연속 실패 시 다음 로그인 요청에 프런트엔드 CAPTCHA 토큰 검증 필드를 필수로 설정하도록 클라이언트에 플래그를 전달합니다 (Q4 답변 반영 - DoS 방어 정책).
     - 일반화된 인증 에러(`INVALID_CREDENTIALS`, 401)를 반환합니다.
   - **검증 성공 시**:
     - 계정의 `status`가 **`ACTIVE`** 인지 확인합니다. 만약 `PENDING`이거나 `LOCKED`인 경우, 인증을 거부하고 일반화된 오류를 반환합니다 (Q5).
     - 로그인 실패 횟수를 0으로 리셋합니다.
     - **해시 자동 업그레이드 (Rehash)**: 저장된 해시 파라미터가 최신 권장 강도보다 낮을 경우, 성공한 현재 평문 비밀번호를 활용하여 백그라운드에서 최신 Argon2id 파라미터로 재해싱(`rehash`)하여 업데이트합니다 (SEC-12).
     - `SessionManager.issue(principal)`를 호출하여 신규 세션을 생성합니다.
5. **출력**: `IssuedSession` 반환 (세션 토큰 및 쿠키 메타데이터).

---

## 3. 세션 수명주기 관리 (SessionManager & SessionVerifier)

요청별 세션 검증 및 Sliding Expiration을 구현합니다.

### 3.1. 세션 발급 (`issue`)
1. 사용자 식별자 및 역할을 포함하는 `Principal`을 정의합니다.
2. 32바이트의 보안 난수로 서버측 세션 핸들(`SessionHandle`)을 생성합니다.
3. 세션 절대 만료 일시(`expiresAt = 현재 시각 + 30일`)와 Sliding 만료 일시(`expiresAtLimit = 현재 시각 + 2시간`)를 설정합니다.
4. `SessionRecord`를 `SessionStore`에 영속화합니다.

### 3.2. 요청별 토큰 검증 및 Sliding Expiration (`verify`)
1. **토큰 수신**: HTTP 요청 헤더 또는 보안 쿠키로부터 `SessionToken`을 획득합니다 (SessionVerifier).
2. **세션 로드**: `SessionStore.load(sessionHandle)`를 호출하여 세션 레코드를 불러옵니다.
3. **만료 검증 (Q3 답변 반영)**:
   - **Sliding 만료 검사**: `현재 시각 > lastActiveAt + 2시간`인 경우 만료 판정합니다.
   - **절대 만료 검사**: `현재 시각 > expiresAt (최초 생성 + 30일)`인 경우 만료 판정합니다.
   - 만료되었거나 세션 레코드가 존재하지 않는 경우 `SessionError.EXPIRED`를 반환하고, 저장소에서 해당 세션을 즉시 삭제하여 무효화합니다 (Fail-Closed, US-A2).
4. **활성 시각 갱신 (Sliding)**:
   - 세션이 유효한 경우, `lastActiveAt`을 `현재 시각`으로 즉시 업데이트하고 `SessionStore`에 다시 저장합니다.
5. **출력**: `Principal`을 반환하여 다운스트림의 보안 컨텍스트에 주입합니다.

---

## 4. 객체 단위 소유권 인가 (AuthorizationGuard)

### 4.1. Stateless 소유권 검증 알고리즘 (`authorize`)
U3의 `AuthorizationGuard`는 타 도메인의 데이터 모델에 종속되지 않도록 완전한 **Stateless 인가 결정**을 내립니다 (Q6 답변 반영).
1. **입력**: `principal: Principal`, `action: Action`, `resourceOwnerId: UserId`
2. **판정 흐름**:
   - `principal`이 존재하지 않거나(비인증 요청) `principal.userId`가 비어있으면 즉시 **`DENY`**를 반환합니다.
   - 요청된 `action`이 사용자 데이터 관리(`READ`, `WRITE`, `DELETE`, `RERUN`)에 해당하는 경우:
     - `principal.userId`와 전달받은 `resourceOwnerId`를 일치 비교합니다.
     - 일치하면 **`ALLOW`**, 일치하지 않으면 **`DENY`**를 반환합니다.
   - 기본적으로 매칭되지 않는 모든 인가 시도는 **`DENY`**로 수렴합니다 (기본 거부 정책 - SEC-8).

### 4.2. 관리자 권한 및 MFA 검증 (`authorizeAdmin`)
1. **입력**: `principal: Principal`, `action: AdminAction`, `mfaContext: MfaContext`
2. **판정 흐름**:
   - `principal.role`이 `ADMIN`이 아니면 즉시 **`DENY`**를 반환합니다 (Fail-Closed).
   - `mfaContext.mfaVerified`가 `false`이면(MFA 완료되지 않음) **`DENY`**를 반환합니다 (Q7 답변 반영 - 관리자 기능 보호).
   - 두 조건이 모두 충족되면 **`ALLOW`**를 반환합니다.
