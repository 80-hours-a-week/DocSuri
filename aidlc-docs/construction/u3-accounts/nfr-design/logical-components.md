# logical-components.md — U3 Accounts NFR 논리 컴포넌트 명세서

**단계**: CONSTRUCTION → NFR Design (유닛별 루프, Track 2 첫 유닛) · **유닛**: U3 Accounts · **일자**: 2026-06-16
**근거(SSOT)**: `construction/plans/u3-accounts-nfr-design-plan.md` (Q1~Q5 답변 반영)

---

## 1. 데이터베이스 커넥션 풀 관리 (Q3 반영)

동기식 컨테이너 런타임 환경에서 리소스를 효율적으로 제어하기 위해 RDBMS 및 Redis 커넥션 풀 설정을 다음과 같이 제약합니다.

### 1.1. PostgreSQL 커넥션 풀 (RDBMS)
- **컴포넌트**: SQLAlchemy `QueuePool` (또는 드라이버 내장 풀러)
- **설정 수치**:
  - `pool_size`: **10** (기본 유지할 커넥션 수)
  - `max_overflow`: **20** (부하 스파이크 시 추가 생성 허용 범위, 총 최대 30개)
  - `pool_timeout`: **3.0초** (풀에서 커넥션을 획득하기 위해 대기하는 최대 시간, 초과 시 즉시 에러)
  - `pool_recycle`: **1800초** (30분 경과한 커넥션을 자동으로 폐기 및 재연결하여 고스트 커넥션 방지)

### 1.2. Redis 커넥션 풀 (인메모리 세션)
- **컴포넌트**: `redis-py` `ConnectionPool`
- **설정 수치**:
  - `max_connections`: **50** (동기 검증 최전방용 여유 있는 소켓 확보)
  - `socket_timeout`: **1.0초** (연결 및 통신 타임아웃)
  - `socket_connect_timeout`: **1.0초**

---

## 2. 환경변수 및 시크릿(Secret) 키 주입 설계 (Q4 반영)

컨테이너의 수평적 확장(Scale-out) 시 AWS Secrets Manager API의 속도 제한(Rate Limit)에 걸려 기동이 지연되거나 실패하는 상황을 방지하기 위해 **12-Factor App 및 OS 환경변수 주입 패턴**을 디자인합니다.

```
+-------------------------------------------------------+
|                 AWS Secrets Manager                   |
+-------------------------------------------------------+
                           |
            (배포 단계에서 안전하게 인출)
                           v
+-------------------------------------------------------+
|  AWS ECS / EKS 배포 작업 정의 (Task Definition Env)    |
+-------------------------------------------------------+
                           |
            (컨테이너 기동 시 OS 환경변수로 주입)
                           v
+-------------------------------------------------------+
|        U3 Accounts Python App (os.environ)            |
+-------------------------------------------------------+
```

### 2.1. 주입되는 핵심 환경변수 목록
- `DATABASE_URL`: RDS PostgreSQL 연결 엔드포인트 및 자격증명 문자열
- `REDIS_URL`: ElastiCache Redis 연결 엔드포인트 주소
- `RECAPTCHA_SECRET_KEY`: Google reCAPTCHA v3 API 비밀 키
- `COOKIE_SIGNING_KEY`: HTTP 세션 토큰 무결성 검증용 HMAC 대칭 키
- `FRONTEND_ORIGIN`: CORS 통제를 위한 신뢰할 수 있는 프런트엔드 도메인 URL

---

## 3. CORS 및 HTTP 인그레스 보안 헤더 구성 (Q5 반영)

세션 쿠키의 전송 안전성 확보와 악의적인 동일 출처 위반 공격을 차단하기 위한 CORS 헤더 구체 바인딩 규칙입니다.

### 3.1. CORS 설정 헤더
- `Access-Control-Allow-Origin`: **`FRONTEND_ORIGIN`** (OS 환경변수에 등록된 단일 Origin 주소를 정확히 일치시켜 바인딩하며, 와일드카드 `*`는 절대 반환하지 않음)
- `Access-Control-Allow-Credentials`: **`true`** (쿠키 전송 수락)
- `Access-Control-Allow-Headers`: `Content-Type, Authorization, X-Requested-With`

### 3.2. HTTP 보안 헤더 (CORS 연동 및 frame-ancestors 예외 규칙)
- `X-Frame-Options`: **`SAMEORIGIN`** (데스크톱 환경의 폰 목업 프레임 내 iframe 임베딩 지원을 위한 예외 카브아웃 반영, Deny 제외)
- `Content-Security-Policy`: **`frame-ancestors 'self' FRONTEND_ORIGIN;`** (동일 출처 및 지정된 프런트엔드 오리진에서의 프레이밍만 허용하여 Clickjacking 방지 - SEC-4 규칙 정합)

---

## 4. PBT 및 CI 파이프라인 통합 명세

- **단위 테스트 실행**:
  - `Hypothesis`를 활용해 정의한 속성 검증(PBT-U3-1/2)을 로컬 및 CI 환경에서 항상 자동 검증합니다.
- **의존성 취약점 스캔 (SCA)**:
  - Github Actions CI 파이프라인에서 `pip-audit`을 가동하여 `argon2-cffi` 및 연동 패키지의 취약점을 커밋마다 분석합니다 (SEC-10).
  - `git-secrets` 또는 Trufflehog 스캐너를 통해 시크릿 키가 레포지토리에 실수로 하드코딩되어 푸시되는 시도를 차단합니다.
