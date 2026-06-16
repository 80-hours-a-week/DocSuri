# Unit Test Execution — U3 Accounts 단위 테스트 실행 지침서

**단계**: CONSTRUCTION → Build and Test · **유닛**: U3 Accounts · **일자**: 2026-06-16
**문서 언어**: 한국어

본 문서는 U3 Accounts 모듈의 핵심 단위 테스트 및 속성 기반 테스트(PBT)의 실행 방법과 품질 관리 요건을 수립합니다.

---

## 1. 테스트 실행 도구 (Testing Tools)

- **테스트 프레임워크**: `pytest`
- **비동기 테스트 지원**: `pytest-asyncio` (FastAPI 및 aioredis 비동기 I/O 매핑 검증)
- **속성 기반 테스트 (PBT)**: `hypothesis`

---

## 2. 테스트 실행 절차

가상 환경이 활성화된 상태에서 아래 명령어를 실행하여 단위 테스트를 전체 수행합니다.

### 2.1. 전체 단위 테스트 실행
```bash
# tests/accounts 디렉터리 내의 모든 테스트 코드를 수행합니다.
pytest tests/accounts -v
```

### 2.2. 속성 기반 테스트 (PBT) 단독 실행
비밀번호 강도 정책 및 해싱 연산의 멱등/상수시간 성질을 검증하는 PBT 스펙만 독립적으로 실행합니다.

```bash
# 1. 비밀번호 정책 PBT 실행 (PBT-U3-1)
pytest tests/accounts/test_password_pbt.py -v

# 2. Argon2id 해싱 일관성 PBT 실행 (PBT-U3-2)
pytest tests/accounts/test_hash_pbt.py -v
```

---

## 3. 테스트 성공 기준 및 보고 (Success Criteria)

- **성공률**: **100% Pass** (실패 테스트 0건)
- **테스트 커버리지 요건**: U3 Accounts 핵심 서비스 및 도메인 레이어 커버리지 **85% 이상** 권장.
- **Hypothesis 기본 설정**:
  - 각 PBT 함수는 기본적으로 `100`가지의 임의 무작위 시나리오 케이스를 생성하여 평가합니다.
  - 만약 반례(Counter-example)가 발견되면, Hypothesis가 입력을 최소화(Shrinking)하여 콘솔 터미널에 실패 원인 입력 패턴을 상세 출력합니다. 이 패턴을 참조하여 `password.py` 또는 `models.py`를 보정해야 합니다.
