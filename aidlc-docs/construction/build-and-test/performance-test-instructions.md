# Performance Test Instructions — U3 Accounts 성능 테스트 지침서

**단계**: CONSTRUCTION → Build and Test · **유닛**: U3 Accounts · **일자**: 2026-06-16
**문서 언어**: 한국어

본 문서는 U3 Accounts 모듈의 핵심 비기능적 요구사항(NFR)인 **세션 검증 초저지연 성능 예산(P50 < 5ms, P99 < 20ms)** 충족 여부를 객체적으로 검증하기 위한 성능 테스트 가이드입니다.

---

## 1. 성능 목표 (NFR Requirements)

| 성능 지표 | 목표 기준 | 대상 API 엔드포인트 | 비고 |
|---|---|---|---|
| **P50 레이턴시** | **< 5ms** | `GET /auth/session` | Redis 인메모리 lookup 보장 |
| **P99 레이턴시** | **< 20ms** | `GET /auth/session` | Redis 커넥션 풀 경합 제어 상태 |
| **동시 사용자 수** | 50 concurrent | `GET /auth/session` | 초당 트래픽(RPS) 500 이상 수용 |
| **에러율 (Error Rate)**| **< 0.1%** | 전체 인증 관련 API | 스레드 고갈/Redis 타임아웃 미발생 |

---

## 2. k6 기반 성능 테스트 구성 및 실행

본 가이드는 가볍고 고성능인 부하 테스트 도구인 **k6**를 기준으로 설명합니다.

### 2.1. k6 스크립트 작성 (`tests/performance/session_load_test.js`)
테스트용 k6 스크립트를 작성하여 특정 가상 사용자(VU) 규모로 `/auth/session` API에 부하를 전송합니다.

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 }, // 30초 동안 가상 사용자 50명까지 램프업
    { duration: '1m', target: 50 },  // 1분간 50명 유지 (피크 부하)
    { duration: '10s', target: 0 },  // 10초간 램프다운
  ],
  thresholds: {
    // NFR 요구사항: P50 < 5ms, P99 < 20ms 강제 검증
    'http_req_duration{name:session_verify}': ['p(50)<5', 'p(99)<20'],
    'http_req_failed': ['rate<0.001'], // 에러율 < 0.1%
  },
};

export default function () {
  const url = 'http://localhost:8000/auth/session';
  const params = {
    headers: {
      'Cookie': 'session_id=dummysessiontokenmaterialforperformancetests',
    },
    tags: { name: 'session_verify' }
  };

  const res = http.get(url, params);
  
  check(res, {
    'is status 200': (r) => r.status === 200,
  });
  
  sleep(0.01); // 10ms 대기 후 재요청 (고빈도 호출)
}
```

### 2.2. 로컬 부하 테스트 실행
실제 ECS Fargate 배포 전 로컬 또는 개발 컨테이너 환경에서 간이 확인을 수행합니다.

```bash
# 1. k6 설치 (macOS)
brew install k6

# 2. 로컬 API 서버 기동 (Uvicorn으로 백엔드 구동)
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4

# 3. k6 부하 테스트 실행
k6 run tests/performance/session_load_test.js
```

---

## 3. 모니터링 및 병목 지점 해소

성능 예산 미달 시 점검사항:
- **Redis ConnectionPool 모니터링**: 커넥션 풀 크기(50개)를 초과하여 대기 스레드/태스크 지연이 발생하지 않는지 로그 확인.
- **Garbage Collection**: Python 런타임의 GC 스파이크로 인해 일시적으로 P99 레이턴시가 튀지 않는지 확인.
- **비동기 이벤트 루프 차단**: 비즈니스 로직 중 비동기(async/await) 처리가 누락되어 동기식 디스크 I/O나 암호학적 해싱 연산이 메인 이벤트 루프를 블로킹하고 있는지 파악. (특히 password hashing은 CPU bound 작업이므로 로그인 API 호출 빈도를 적절히 격리 통제해야 함).
