# Integration Test Instructions — U3 Accounts 통합 테스트 지침서

**단계**: CONSTRUCTION → Build and Test · **유닛**: U3 Accounts · **일자**: 2026-06-16
**문서 언어**: 한국어

본 문서는 U3 Accounts 모듈 내의 컴포넌트(Controller, Service, Repository) 간의 유기적인 결합과 외부 인프라스트럭처와의 통합 작용을 검증하기 위한 지침입니다.

---

## 1. 테스트 목적 및 시나리오

### 1.1. 시나리오 1: 회원가입-인증-활성화 통합 워크플로우 (US-A1, BR-A5)
- **검증 내용**: 가입 시 `PENDING` 계정 생성 → 인증 토큰 메일 발송(Mock SES) → 활성화 엔드포인트 호출 → `ACTIVE` 전환 프로세스가 롤백 없이 안전하게 완결되는가.
- **수행 방식**: SQLAlchemy `sqlite:///:memory:` 인메모리 데이터베이스 및 `MockEmailClient` 기반 결선 수행.

### 1.2. 시나리오 2: 실패 누적 브루트포스 백오프 및 reCAPTCHA (US-A2, BR-A4)
- **검증 내용**: 로그인 3회 이상 실패 시 비동기 지연(`asyncio.sleep`)이 워커 리소스를 점유하지 않고 정확히 지연되는가, 10회 이상 실패 시 reCAPTCHA 검증 게이트가 Fail-Closed로 올바르게 차단하는가.
- **수행 방식**: `unittest.mock`을 활용한 `asyncio.sleep` 호출 감지 및 `RecaptchaClient.verify_token` 모킹 분기 검증.

### 1.3. 시나리오 3: Redis 연결 유실 시 Fail-Closed 차단 (US-R1, BR-A3)
- **검증 내용**: Redis 장애(ConnectionError 등) 발생 시 데이터베이스 등으로 비정상 폴백하지 않고, 안전하게 예외를 격리 래핑하여 인증 요청을 차단하는가.
- **수행 방식**: `redis.asyncio` 세션 레포지토리에 임의의 커넥션 예외를 강제 주입하여 가드의 차단 동작 확인.

---

## 2. 통합 테스트 실행 방법

통합 테스트는 `tests/accounts/test_services.py` 및 `tests/accounts/test_session.py`, `tests/accounts/test_guard.py`에 수록되어 있습니다.

```bash
# 1. 서비스 비즈니스 흐름 통합 테스트 실행
pytest tests/accounts/test_services.py -v

# 2. Redis 세션 장애 및 만료 통합 테스트 실행
pytest tests/accounts/test_session.py -v

# 3. Stateless 인가 가드 통합 테스트 실행
pytest tests/accounts/test_guard.py -v
```

---

## 3. 로컬 독립 서버 연동 통합 테스트 (Optional)
로컬에 실제 PostgreSQL 및 Redis 컨테이너를 가동하여 테스트하고 싶은 경우의 절차입니다.

```bash
# 1. 로컬 개발용 인프라 기동 (Docker Compose 활용 예시)
docker run -d --name docsuri-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
docker run -d --name docsuri-redis -p 6379:6379 redis:7

# 2. 로컬 모킹 비활성화 및 환경변수 주입 실행
export ENV=production
export SES_MOCK=false
export RECAPTCHA_SECRET_KEY=real_recaptcha_key

# 3. DDL 마이그레이션 적용
psql -h localhost -U postgres -d postgres -f backend/modules/accounts/migrations/001_create_accounts_table.sql

# 4. 통합 API 테스트 수행
# (App shell 결선 이후 HTTP API 클라이언트 테스트 도구 활용 가능)
```
