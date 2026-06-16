# u3-accounts-functional-design-plan.md — Functional Design 계획 + 질문 게이트

**단계**: CONSTRUCTION → Functional Design (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `aidlc-docs/inception/` — `unit-of-work.md`, `unit-of-work-story-map.md`, `application-design/{components,component-methods,services,component-dependency}.md`, `user-stories/stories.md`, `requirements/requirements.md`
**원칙**: 이 단계는 **기술 무관(technology-agnostic)** — 비즈니스 로직·도메인 모델·비즈니스 규칙만 설계합니다. 구체적인 세션 스토리지 엔진(Redis/RDBMS 등)이나 웹 프레임워크는 **NFR Requirements/Infra Design**에서 결정합니다.

---

## 1. 유닛 컨텍스트 (Step 1 — Analyze Unit Context)

- **책임**: 가입, 로그인, 로그아웃, 인증 세션 수명주기 관리 및 **시스템 내 객체 단위 소유권 인가의 단일 권위 결정점(deny-by-default)**을 제공합니다.
- **스토리**:
  - **US-A1**: 공개 셀프 가입 (FR-7, SEC-11, SEC-12, SEC-3)
  - **US-A2**: 로그인/세션/로그아웃 (FR-7, SEC-8, SEC-12)
  - **기여**: **US-H1** 히어로 스토리 (가입 기여)
- **컴포넌트(9)**: AccountController, SignupService, AuthenticationService, SessionManager, SessionVerifier, AuthorizationGuard, CredentialStore, PasswordPolicy, SessionStore.
- **공유 계약**: `shared/dtos/accounts.schema.json` (SignupRequest, SignupResult, LoginRequest, SessionInfo), `shared/events/account-signals.schema.json` (AccountCreated, SignupAbuseSignal, AuthFailureSignal).
- **핵심 트레이스**: FR-7, SEC-3(민감 필드 비로깅), SEC-8(기본 거부/소유권 인가), SEC-11(가입 남용 방어), SEC-12(적응형 해싱/쿠키/브루트포스), SEC-15(Fail Closed), QT-4/PBT-02/03(자격증명 검증 및 암호 규칙 PBT).

---

## 2. Functional Design 실행 계획 (Step 2)

> 질문 답변 완료 후, 아래 산출물들을 `aidlc-docs/construction/u3-accounts/functional-design/` 디렉터리에 작성합니다.

- [ ] **domain-entities.md** — U3 도메인 엔티티 및 값 객체(Value Object) 정의 (기술 무관)
  - 계정 도메인: `Account`, `AccountId`, `EmailAddress` (유효성 검증 규칙 내장), `PasswordHash`, `AccountStatus{ACTIVE|LOCKED|PENDING}`
  - 자격증명 도메인: `Credential`, `CredentialId`, `HashParameters` (KDF 버전 및 솔트/반복 횟수 메타데이터), `VerificationResult`
  - 세션 도메인: `Session`, `SessionHandle` (서버측 인덱스용 난수 식별자), `SessionToken` (클라이언트 전달용 암호화 토큰 포맷 정의), `Principal`, `SessionExpiry`
  - 인가 및 신호: `Action{READ|WRITE|DELETE|RERUN}`, `Decision{ALLOW|DENY}`, `AbuseMetric` (남용 탐지 카운터), `FailureCount` (브루트포스 카운터)
- [ ] **business-logic-model.md** — 서비스 및 컴포넌트 알고리즘 설계
  - `SignupService.register`: 이메일 중복 체크, 비밀번호 유출 및 규칙 검증, 솔트 생성 및 적응형 해싱, 계정 영속화, `AccountCreated` 이벤트 발행 오케스트레이션.
  - `AuthenticationService.authenticate`: 자격증명 검증, 무차별 대입 방어(실패 횟수 트래킹), 성공 시 세션 발급, 실패 시 `AuthFailureSignal` 발행 흐름.
  - `SessionManager` & `SessionVerifier`: 세션 쿠키 발급 정책, 게이트웨이 요청 위임 시 REST 세션 토큰 검증 알고리즘 (Fail-Closed 작동 방식).
  - `AuthorizationGuard.authorize`: 객체 단위 소유권 판단 규칙 및 권한 확인 흐름.
- [ ] **business-rules.md** — 결정 규칙, 제약 및 예외 처리
  - **비밀번호 복잡도 규칙 및 유출 비밀번호 정책** (Q1, PasswordPolicy)
  - **비밀번호 적응형 해싱 규칙** (Q2, CredentialStore)
  - **세션 수명 및 만료 정책** (Q3, SessionManager)
  - **무차별 대입 공격(Brute Force) 보호 정책** (Q4, AuthenticationService)
  - **가입 남용(Signup Abuse) 방어 규칙** (Q5, SignupService)
  - **기본 거부(Deny-by-default) 및 객체 단위 소유권 규칙** (Q6, AuthorizationGuard)
  - **관리자 권한 및 MFA 강제화 규칙** (Q7, AuthorizationGuard)
  - **PII 및 Secrets 차단 로깅 불변식**: 비밀번호 평문, 세션 토큰, PII는 절대 로그(SEC-3)에 남기지 않으며, 일반화된 에러 응답(SEC-9/15)을 적용함.
- [ ] **PBT 속성 식별 (PBT-02/03)** — 테스트 가능 속성 정의
  - 비밀번호 정책 검증 속성: 임의의 비밀번호가 PasswordPolicy 복잡도 조건을 만족하거나 불만족할 때의 동작 일관성.
  - 적응형 해싱 속성: 해싱된 값은 평문 복원이 불가능하며, 동일 자격증명에 대해 `verifyCredential`이 항상 동일하고 멱등적인 결과를 반환함 (상수시간 비교 보장).
- [ ] **추적성 매트릭스** — U3 컴포넌트/규칙/속성 → 요구사항 ID 역추적 (FR-7, SEC-3, SEC-8, SEC-11, SEC-12, SEC-15).

---

## 3. 가정 (Assumptions)

- **AS-1**: 본 단계에서는 코드를 생성하지 않으며 구체 기술(예: Redis vs PostgreSQL)은 NFR 단계로 위임합니다.
- **AS-2**: IP 기반 레이트 리미팅 강제화는 U6 미들웨어/게이트웨이에서 물리적으로 처리하며, U3는 가입/로그인 실패에 따른 도메인 레벨 신호(`SignupAbuseSignal`, `AuthFailureSignal`) 및 비즈니스 정책 판정만 담당합니다.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그로 답변)

> 각 질문의 `[Answer]:` 뒤에 A/B/C/D 등 선택지를 입력해 주세요. 모든 질문은 마지막 옵션인 '기타(Other)'를 선택하고 직접 기재할 수 있습니다.

### Q1 — 비밀번호 복잡도 및 유출 검사 정책 (SEC-12 / PasswordPolicy)
가입 시 사용자가 입력하는 비밀번호의 강도 정책 및 유출 검사 방식은 어떻게 구성합니까?

A) **최소 8자 이상, 영문/숫자/특수문자 중 2가지 이상 조합** + 외부 유출 비밀번호 조회 API(예: HaveIBeenPwned API)를 실시간 연동하여 알려진 유출 비밀번호 사용을 즉시 차단함.

B) **최소 10자 이상, 영문 대소문자/숫자/특수문자 필수 포함** + 로컬 블랙리스트(상위 1만 개 취약 패스워드 등) 기반의 오프라인 검증만 수행하여 외부 API 의존성을 제거함.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 외부 API 의존성(HaveIBeenPwned 등)은 외부 서비스 장애 시 가입 프로세스가 전체 중단되는 위험(Availability Risk)을 초래할 수 있으므로, 초기에는 최소 10자 이상, 영문 대소문자/숫자/특수문자 필수 포함 규칙과 로컬 최다 취약 패스워드 블랙리스트 검증을 통해 도메인 자급력을 확보한다.


### Q2 — 비밀번호 적응형 해싱 KDF 선정 (SEC-12 / CredentialStore)
CredentialStore에서 비밀번호를 저장 및 검증할 때 사용할 메모리/CPU 하드 적응형 해싱 알고리즘은 무엇입니까?

A) **Argon2id** (현재 OWASP가 권장하는 최신 표준 해싱 알고리즘, 메모리 하드 KDF)

B) **bcrypt** (검증되고 널리 사용되는 전통적인 CPU 하드 적응형 해싱 알고리즘)

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. OWASP 권장 표준이자 메모리 하드(Memory-Hard) 특성을 지녀 GPU 기반 대규모 병렬 무차별 대입 공격을 효과적으로 방어할 수 있는 Argon2id를 사용한다.


### Q3 — 세션 수명 및 만료 정책 (US-A2 / SessionManager)
발급되는 사용자 세션의 만료 및 갱신 방식은 어떻게 구성합니까?

A) **절대 만료 시간만 적용**: 발급 후 14일이 경과하면 무조건 만료 (Sliding Expiration 배제하여 단순하고 예측 가능한 세션 관리 제공).

B) **Sliding Expiration + 절대 만료 시간 복합 적용**: 마지막 활동(Request) 후 2시간 동안 요청이 없으면 만료되나, 활동이 지속되더라도 최초 발급 후 최대 30일이 지나면 강제 로그아웃.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 보안과 사용자 편의성의 균형을 맞추기 위해 **Sliding Expiration(마지막 활동 후 2시간 만료)과 절대 만료 시간(최초 발급 후 최대 30일 경과 시 강제 만료)**을 결합하여 탈취된 세션 토큰의 유효 기간을 최소화한다.


### Q4 — 무차별 대입 공격(Brute Force) 방어 전략 (US-A2 / SEC-12 / AuthenticationService)
로그인 시 반복적으로 자격증명 검증에 실패할 경우, 무차별 대입을 차단하기 위한 계정 보호 전략은 무엇입니까?

A) **임시 계정 잠금(Temporary Lockout)**: 동일 이메일로 5회 연속 로그인 실패 시, 해당 계정을 15분간 잠금 처리함.

B) **점진적 시간 지연(Exponential Backoff Delay) + CAPTCHA**: 3회 실패 시부터 로그인 응답 대기 시간을 기하급수적으로 늘리고(1초 -> 2초 -> 4초...), 10회 연속 실패 시 CAPTCHA 입력을 필수화함 (계정이 완전히 차단되어 유발되는 DoS 공격 예방).

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 임시 계정 잠금(A안)은 악의적인 공격자가 특정 사용자의 이메일만으로 계정을 고의 잠금하여 정상 사용자의 서비스 이용을 방해하는 Account Lockout DoS 공격에 취약하다. 따라서 계정을 잠그지 않는 대신 3회 실패 시부터 실패 횟수에 비례해 응답 대기 시간을 기하급수적으로 늘리고(Exponential Backoff), 10회 실패 시 도메인 레이어에서 CAPTCHA 검증 신호를 강제하는 방식을 채택한다.


### Q5 — 가입 남용 방어(Signup Abuse) 및 봇 완화 전략 (SEC-11 / SignupService)
공개 셀프 가입(US-A1)을 노린 악의적인 대량 계정 생성 봇 및 남용을 방지하기 위한 방어 정책은 무엇입니까?

A) IP 및 이메일 도메인별 단위 시간당 가입 요청 횟수를 엄격히 제한(Rate Limiting)하고, **가입 API 호출 시 프런트엔드에서 획득한 CAPTCHA 토큰 검증을 항상 강제**함.

B) 가입 요청 시 계정을 즉시 활성화하지 않고 `PENDING` 상태로 둔 뒤, **이메일 인증 링크(인증 토큰)를 발송하여 24시간 내에 클릭하여 인증해야만 계정을 활성화**하고 서비스를 허용함.

C) 가입 시 복잡한 인증/CAPTCHA 없이 IP/이메일 기준 레이트 리미팅만 단순 적용함 (초기 단계 및 단일 랩 규모 고려).

D) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 가입 시 즉시 활성화하지 않고 AccountStatus.PENDING 상태로 생성한 후, 이메일 인증 링크(Token) 검증을 거쳐야만 ACTIVE로 전환되는 흐름을 비즈니스 규칙으로 강제한다. 이를 통해 무분별한 유령 계정 양산을 방지하고 허위 이메일을 차단한다. (U6 게이트웨이의 IP 레이트 리미팅과 상호 보완 작동)


### Q6 — 객체 단위 소유권 인가(Object-Level Authorization) 구현 모델 (SEC-8 / AuthorizationGuard)
`AuthorizationGuard`가 U4(Saved Searches/Library)나 U6(Gateway)로부터 인가 결정을 위임받아 소유권을 확인할 때, 소유자 정보 조회 책임을 어떻게 분배합니까?

A) **Stateless 인가**: `AuthorizationGuard`는 전달받은 주체(Principal)의 `userId`와 리소스 소유자(`resourceOwnerId`)가 일치하는지만 판정하는 순수 Stateless 함수로 동작합니다. DB에서 대상 객체의 소유자 식별자를 조회하는 책임은 호출 측(예: U4 Controller)이 부담합니다.

B) **Stateful 인가**: `AuthorizationGuard`가 직접 객체 식별자(ResourceId)를 매개변수로 받아 내부 저장소(DB/Repository)를 조회하여 소유자를 판별한 후 인가 여부를 결정합니다.

C) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: A. AuthorizationGuard를 완전한 Stateless 인가 함수로 유지한다. 데이터를 보관하는 각 유닛의 비즈니스 레이어가 리소스 소유자 식별자를 직접 조회하여 Guard에 주체와 함께 넘기도록 설계함으로써 U3가 타 도메인의 엔티티 구조나 DB에 직접 의존하여 결합도가 높아지는 아키텍처 오염을 방지한다.


### Q7 — 관리자(Admin) 역할 및 MFA 구성 (SEC-12 / AuthorizationGuard)
시스템 운영자(OP) 등 특수 권한을 가진 관리자 계정의 식별 및 다요소 인증(MFA) 요건은 어떻게 구성합니까?

A) DB 내 `role` 속성이 `ADMIN`인 계정으로 식별하며, 관리자 로그인 시 일반 세션 발급 외에 추가로 **TOTP(Google Authenticator 등) 기반 MFA 인증이 완료되어야만 관리자용 API(예: U6 대시보드/지표 조회) 접근을 허용**함.

B) 일반 가입 API를 통한 관리자 생성은 완전히 차단하며, DB 시딩(DB Seeding) 또는 환경 변수로 사전에 등록된 관리자 자격증명만 허용함 + 로그인 시 TOTP MFA 강제 적용.

C) 본 프로젝트의 타깃 범위(v1)에서는 관리자 전용 기능을 독립된 API 수준에서 격리할 필요가 없으므로 관리자 역할 및 MFA는 비활성 상태(N/A)로 둠.

D) Other (아래 [Answer]: 뒤에 상세 내용을 기재해 주세요.)

[Answer]: B. 공개 API를 통한 관리자 가입은 원천 차단(Fail-Closed 보장)하며, 인프라 시딩 등을 통해서만 계정 생성이 가능하도록 제한한다. 또한, 관리자 권한(role: ADMIN)이 감지되면 일반 세션 검증 외에 TOTP 기반 다요소 인증(MFA)을 비즈니스 규칙 상 필수 조건으로 검증한다.