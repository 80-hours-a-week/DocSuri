import os
import re
import logging
from argon2 import PasswordHasher
from .models import InvalidPasswordException

logger = logging.getLogger(__name__)

# Resources 디렉터리 경로 계산 (모듈 위치 기준)
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "resources")
BLACKLIST_PATH = os.path.join(RESOURCES_DIR, "common_passwords.txt")

# 피드백 ① 반영: 모듈 로딩 시점에 단 1회 1만개 최다 취약 패스워드 블랙리스트를 메모리 set에 캐싱
_common_passwords = set()
if os.path.exists(BLACKLIST_PATH):
    try:
        with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                pwd = line.strip()
                if pwd:
                    _common_passwords.add(pwd.lower())
    except Exception as e:
        # Fail-open 방지: 블랙리스트 로딩 실패를 조용히 삼키면 BR-A1 취약 패스워드 차단이
        # 무력화된다(약한 공통 패스워드가 통과). 운영이 즉시 인지하도록 ERROR로 크게 남긴다.
        logger.error(
            "Weak-password blacklist load FAILED from %s (%s) — BR-A1 blacklist check is DEGRADED (fail-open).",
            BLACKLIST_PATH, e,
        )
else:
    # 파일 자체가 배포되지 않은 경우도 fail-open이므로 명시적으로 경보를 남긴다.
    logger.error(
        "Weak-password blacklist file MISSING at %s — BR-A1 blacklist check DISABLED (fail-open). "
        "Ensure resources/common_passwords.txt is deployed.",
        BLACKLIST_PATH,
    )


def get_password_hasher() -> PasswordHasher:
    """
    OWASP 권장 Argon2id KDF 파라미터(m=65536, t=3, p=4)를 적용한 PasswordHasher를 반환한다 (BR-A2).
    signup/auth 서비스 및 PBT가 이 단일 팩토리를 공유해, 보안 파라미터가 여러 곳에 복제되어
    한 곳만 누락 수정되는(해시 비호환) 사고를 방지하는 SSOT 역할을 한다.
    """
    return PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
    )

class PasswordPolicy:
    # 복잡도 정규식 필터
    _uppercase_pattern = re.compile(r"[A-Z]")
    _lowercase_pattern = re.compile(r"[a-z]")
    _digit_pattern = re.compile(r"\d")
    # 일반적인 키보드 특수문자 집합
    _special_pattern = re.compile(r"[!@#$%^&*(),.?\":{}|<>\-_=+\\\/\[\]~`';]")

    @classmethod
    def evaluate(cls, password: str) -> bool:
        """
        비밀번호가 최소 10자 이상 및 대/소문자, 숫자, 특수문자를 포함하고
        취약 패스워드 블랙리스트에 걸리지 않는지 검증합니다.
        불일치 시 InvalidPasswordException을 발생시키고, 통과 시 True를 반환합니다.
        """
        if len(password) < 10:
            raise InvalidPasswordException("비밀번호는 최소 10자 이상이어야 합니다. (BR-A1)")

        if not cls._uppercase_pattern.search(password):
            raise InvalidPasswordException("비밀번호는 영문 대문자를 최소 1개 이상 포함해야 합니다. (BR-A1)")

        if not cls._lowercase_pattern.search(password):
            raise InvalidPasswordException("비밀번호는 영문 소문자를 최소 1개 이상 포함해야 합니다. (BR-A1)")

        if not cls._digit_pattern.search(password):
            raise InvalidPasswordException("비밀번호는 숫자를 최소 1개 이상 포함해야 합니다. (BR-A1)")

        if not cls._special_pattern.search(password):
            raise InvalidPasswordException("비밀번호는 특수문자를 최소 1개 이상 포함해야 합니다. (BR-A1)")

        # 피드백 ① 반영: 메모리 set을 이용한 O(1) 초고속 블랙리스트 룩업 (대소문자 구분 없음)
        if password.lower() in _common_passwords:
            raise InvalidPasswordException("사용이 금지된 너무 취약한 비밀번호입니다. (BR-A1 블랙리스트 매칭)")

        return True
