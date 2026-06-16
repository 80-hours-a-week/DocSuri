# domain-entities.md — U3 Accounts 도메인 엔티티 및 값 객체 정의

**단계**: CONSTRUCTION → Functional Design (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/plans/u3-accounts-functional-design-plan.md` (Q1~Q7 답변 반영)

---

## 1. 도메인 엔티티 (Domain Entities)

### 1.1. Account (계정 엔티티)
사용자의 가입 정보 및 활성 상태를 나타내는 루트 엔티티입니다.
- **속성**:
  - `id`: `AccountId` (고유 식별자)
  - `email`: `EmailAddress` (이메일 주소)
  - `status`: `AccountStatus` (계정 상태)
  - `createdAt`: `DateTime` (생성 일시)
- **불변식**:
  - `status`가 `PENDING`인 계정은 `ACTIVE`로 전환되기 전까지 어떠한 세션도 발급받을 수 없다 (US-A2).
- **Trace**: FR-7, US-A1, US-A2, SEC-11

### 1.2. Session (세션 엔티티)
인증에 성공한 사용자의 활성 세션 상태를 유지하는 엔티티입니다.
- **속성**:
  - `handle`: `SessionHandle` (서버측 조회용 난수 식별자)
  - `userId`: `AccountId` (세션 소유 사용자 식별자)
  - `createdAt`: `DateTime` (세션 생성 일시)
  - `lastActiveAt`: `DateTime` (마지막 요청 일시 - Sliding Expiration용)
  - `expiresAt`: `DateTime` (절대 만료 일시 - Absolute Expiration용)
- **불변식**:
  - `lastActiveAt + 2시간`이 현재 시각보다 이전이거나, `createdAt + 30일`이 현재 시각보다 이전이면 이 세션은 만료된다 (Q3 답변 반영).
- **Trace**: FR-7, US-A2, SEC-12

---

## 2. 값 객체 (Value Objects)

### 2.1. AccountId (계정 식별자)
계정을 고유하게 식별하는 유일 값 객체입니다. (예: UUID v4 문자열 형식 포맷 검증)

### 2.2. EmailAddress (이메일 주소)
식별성을 확보하고 RFC 5322 문법을 준수하는 값 객체입니다.
- **검증 규칙**:
  - `@` 기호를 반드시 포함해야 하며, 도메인 파트와 로컬 파트의 길이 제한을 만족해야 한다 (SEC-5).

### 2.3. PasswordHash (비밀번호 해시)
KDF 알고리즘을 통해 암호화된 해시 값 객체입니다. 평문 비밀번호를 소유하지 않으며, 솔트 및 매개변수를 포함하거나 가집니다.
- **Trace**: US-A1, SEC-3, SEC-12

### 2.4. HashParameters (해싱 파라미터)
적응형 해싱 알고리즘(Argon2id)에 필요한 매개변수 메타데이터입니다.
- **속성**:
  - `memoryCost`: 메모리 사용량 (KB)
  - `timeCost`: 반복 횟수 (Iterations)
  - `parallelism`: 병렬 처리 스레드 수
  - `salt`: 암호학적 임의 솔트 (최소 16바이트)
  - `version`: KDF 알고리즘 버전
- **Trace**: Q2 답변 반영, SEC-12

### 2.5. SessionHandle (세션 핸들)
세션을 서버측에서 구별 및 즉각 무효화하기 위한 암호학적으로 강한 난수 값 객체입니다. (최소 32바이트의 임의 바이트열)

### 2.6. SessionToken (세션 토큰)
클라이언트와 전송 계층 간 통신 시 제공되는 인증 토큰 값 객체입니다. (쿠키 또는 Authorization 헤더에 실려 전달)
- **보안 요구사항**:
  - 절대 일반 로그에 기록되어서는 안 된다 (SEC-3).

### 2.7. Principal (인증 정보 컨텍스트)
현재 요청을 수행 중인 인증된 사용자의 보안 컨텍스트입니다.
- **속성**:
  - `userId`: `AccountId` (사용자 식별자)
  - `role`: `UserRole{USER|ADMIN}` (역할 권한)
  - `mfaVerified`: `boolean` (MFA 인증 완료 여부)
- **Trace**: SEC-8, SEC-12

### 2.8. Action (인가 액션)
사용자가 리소스에 수행하고자 하는 행동을 나타내는 Enum입니다.
- **값**: `READ`, `WRITE`, `DELETE`, `RERUN`
- **Trace**: SEC-8

---

## 3. 상태 정의 (State Configurations)

### 3.1. AccountStatus (계정 상태)
- `PENDING`: 가입 완료 후 이메일 인증을 대기 중인 상태. (로그인 불가)
- `ACTIVE`: 이메일 인증이 완료되어 정상적인 서비스 이용이 가능한 상태.
- `LOCKED`: 로그인 실패 누적 또는 이상 징후로 인해 관리자 또는 보안 시스템에 의해 잠긴 상태.
- **Trace**: Q5 답변 반영, SEC-11

### 3.2. VerificationResult (자격증명 검증 결과)
- **속성**:
  - `matched`: `boolean` (일치 여부)
  - `needsRehash`: `boolean` (해시 설정 업그레이드 필요 여부)
- **Trace**: SEC-12

### 3.3. Decision (인가 판정)
- `ALLOW`: 요청한 리소스 및 액션에 대한 접근을 승인함.
- `DENY`: 접근을 거부함.
- **Trace**: SEC-8
