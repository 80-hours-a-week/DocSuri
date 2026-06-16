import pytest
from hypothesis import given, settings, strategies as st
from argon2.exceptions import VerificationError

# 애플리케이션의 실제 해셔 팩토리를 테스트한다 (라이브러리 동어반복 X).
# signup/auth 서비스가 이 팩토리를 공유하므로, 여기서 검증하는 불변식이 곧 서비스의 불변식이다.
from backend.modules.accounts.password import get_password_hasher

# PBT-U3-2: Argon2id 자격증명 해싱 및 검증 일관성 속성 검증 (PBT-03)


def test_password_hasher_uses_owasp_parameters():
    """애플리케이션 해셔가 BR-A2의 OWASP 권장 파라미터(m=65536, t=3, p=4)를 사용하는지 검증한다."""
    hasher = get_password_hasher()
    assert hasher.time_cost == 3
    assert hasher.memory_cost == 65536
    assert hasher.parallelism == 4
    assert hasher.hash_len == 32
    assert hasher.salt_len == 16


# Argon2id는 의도적으로 느린 KDF(m=64MB)라 예제당 수십~수백 ms가 걸린다.
# Hypothesis 기본 per-example 데드라인(200ms)은 이 비용 때문에 머신 부하에 따라 오탐(flaky)을 내므로
# 데드라인을 끄고, 예제 수는 KDF 비용을 고려해 합리적으로 제한한다.
@settings(deadline=None, max_examples=20)
@given(st.text(min_size=10, max_size=50))
def test_argon2id_hashing_consistency(password: str):
    """
    애플리케이션 해셔 get_password_hasher() 로 해싱한 결과 H에 대해:
    1. 동일 비밀번호 P로 검증 시 verify() 결과는 항상 True이다.
    2. P와 다른 비밀번호 P'로 검증 시 항상 VerificationError가 발생한다.
    3. 해시는 Argon2id 포맷이어야 한다.
    """
    hasher = get_password_hasher()

    # 1. 해시 생성 — Argon2id 포맷 검증
    hash_value = hasher.hash(password)
    assert hash_value.startswith("$argon2id$")

    # 2. 동일한 비밀번호로 인증 성공 보장
    assert hasher.verify(hash_value, password) is True

    # 3. 다른 비밀번호로 시도 시 인증 실패 보장
    different_password = password + "_diff"
    with pytest.raises(VerificationError):
        hasher.verify(hash_value, different_password)
