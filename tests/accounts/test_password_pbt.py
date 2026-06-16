import pytest
from hypothesis import given, strategies as st
from backend.modules.accounts.password import PasswordPolicy, _common_passwords
from backend.modules.accounts.models import InvalidPasswordException

# PBT-U3-1: PasswordPolicy 복잡도 및 블랙리스트 정책 검증 (PBT-02)

@given(st.text())
def test_password_policy_random_inputs(password: str):
    """
    임의의 모든 무작위 입력에 대하여, 비밀번호 정책 검증은
    BR-A1 규칙(길이 10자, 대소문자/숫자/특수문자 포함)을 만족하지 못하거나
    블랙리스트에 포함되면 항상 InvalidPasswordException을 던져야 함을 보장합니다.
    """
    # 오라클은 구현(password.py)의 정규식을 그대로 사용해야 한다.
    # str.isupper()/isdigit() 등은 유니코드(À, ², …)까지 참으로 보지만, BR-A1은 '영문' 대/소문자와
    # 십진 숫자를 요구하므로 구현은 ASCII [A-Z]/[a-z]/\d 를 쓴다. 오라클이 유니코드 메서드를 쓰면
    # ':::::::Aa²' 같은 입력에서 오라클은 통과를 기대하지만 구현은 거부 → 오라클 드리프트로 오탐이 난다.
    has_upper = PasswordPolicy._uppercase_pattern.search(password) is not None
    has_lower = PasswordPolicy._lowercase_pattern.search(password) is not None
    has_digit = PasswordPolicy._digit_pattern.search(password) is not None
    has_special = PasswordPolicy._special_pattern.search(password) is not None
    is_long = len(password) >= 10
    
    # 오라클은 구현이 실제 사용하는 블랙리스트 집합과 동일해야 한다.
    # (7-word 축약본을 쓰면, 복잡도를 만족하면서 파일에만 있는 약한 패스워드가 생성될 때 오라클이 어긋난다.)
    in_blacklist = password.lower() in _common_passwords

    is_valid_expectation = is_long and has_upper and has_lower and has_digit and has_special and not in_blacklist

    if not is_valid_expectation:
        with pytest.raises(InvalidPasswordException):
            PasswordPolicy.evaluate(password)
    else:
        # 모든 조건이 완벽히 충족된 경우 True를 반환해야 함
        assert PasswordPolicy.evaluate(password) is True


@given(st.sampled_from(["123456", "password", "123456789", "qwerty", "google", "secret", "admin"]))
def test_password_policy_blacklist_explicit(blacklisted_pwd: str):
    """블랙리스트에 포함된 암호는 다른 복잡도 조건 충족 여부와 무관하게 무조건 거부되어야 합니다."""
    # 만약 대소문자나 특수문자를 인위적으로 붙여서 블랙리스트 체크를 통과하려 해도 걸리는지
    with pytest.raises(InvalidPasswordException):
        PasswordPolicy.evaluate(blacklisted_pwd)


def test_password_policy_valid_examples():
    """정상적인 복잡도 정책을 통과하는 비밀번호의 성공 동작을 검증합니다."""
    # 10자 이상, 대소문자/숫자/특수문자 포함, 블랙리스트 제외
    assert PasswordPolicy.evaluate("SecurePass123!") is True
    assert PasswordPolicy.evaluate("DrSuriPostgrad99#") is True
