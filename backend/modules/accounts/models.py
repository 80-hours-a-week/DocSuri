import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class DomainException(Exception):
    """Base domain exception for Accounts module"""
    pass

class InvalidEmailException(DomainException):
    pass

class InvalidPasswordException(DomainException):
    pass

class SessionExpiredException(DomainException):
    pass

class UnauthorizedException(DomainException):
    pass

class SessionStoreUnavailableException(DomainException):
    """Fail-Closed error when ElastiCache Redis is down"""
    pass

class AccountStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class Action(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    RERUN = "RERUN"

@dataclass(frozen=True)
class AccountId:
    value: str

    def __post_init__(self):
        try:
            # Validate UUID v4 format
            UUID(self.value)
        except ValueError as e:
            raise DomainException(f"Invalid AccountId UUID format: {self.value}") from e

@dataclass(frozen=True)
class EmailAddress:
    value: str

    # RFC 5322 email regex pattern
    _pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    def __post_init__(self):
        if not self.value or "@" not in self.value:
            raise InvalidEmailException("Email must contain '@'")
        if len(self.value) > 254:
            raise InvalidEmailException("Email exceeds maximum allowed length of 254 characters")
        if not self._pattern.match(self.value):
            raise InvalidEmailException(f"Email violates RFC 5322 formatting: {self.value}")

@dataclass(frozen=True)
class PasswordHash:
    value: str

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: UserRole
    mfa_verified: bool = False

    def __post_init__(self):
        # Validate user_id has valid UUID format
        try:
            UUID(self.user_id)
        except ValueError as e:
            raise DomainException(f"Invalid Principal user_id format: {self.user_id}") from e

@dataclass
class SessionRecord:
    handle: str
    user_id: str
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime
    # 발급 시점의 역할을 세션에 보존해 verify() 가 실제 역할을 복원할 수 있게 한다 (하드코딩 USER 제거).
    role: str = UserRole.USER.value
    # BR-A7: TOTP MFA 통과 여부를 세션에 보존 — 관리자 제어 평면 인가(authorize_admin)가 이 값을 읽는다.
    mfa_verified: bool = False
