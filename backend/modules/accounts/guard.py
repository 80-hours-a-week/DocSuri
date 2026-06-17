from enum import Enum

from .models import AccountId, Action, Principal, UserRole


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"

class AuthorizationGuard:
    """
    객체 단위 소유권 및 관리자 권한 인가 결정을 처리하는 단일 권위 가드 (BR-A6, BR-A7)
    피드백 ④ 반영: 타 도메인 데이터 스펙과의 완전한 분리를 위해 Stateless 인가로 설계
    """

    @classmethod
    def authorize(cls, principal: Principal | None, action: Action, resource_owner_id: AccountId | None) -> Decision:
        """
        사용자 데이터 관리 액션(READ, WRITE, DELETE, RERUN)에 대해 객체 소유권을 Stateless 검증합니다.
        피드백 ④ 반영: principal과 함께 타 서비스가 먼저 조회한 resource_owner_id를 명시적 인자로 받습니다.
        """
        # 1. 기본 거부 정책 (Default Deny - SEC-8)
        if not principal or not principal.user_id:
            return Decision.DENY

        if not resource_owner_id or not resource_owner_id.value:
            return Decision.DENY

        # 2. 소유권 일치 판단 (BR-A6)
        if principal.user_id == resource_owner_id.value:
            return Decision.ALLOW

        # 3. 소유자가 다르면 기본 거부
        return Decision.DENY

    @classmethod
    def authorize_admin(cls, principal: Principal | None, mfa_verified: bool = False) -> Decision:
        """
        관리자(ADMIN) 제어 평면에 대한 접근 및 TOTP MFA 검증을 강제합니다. (BR-A7)
        """
        if not principal:
            return Decision.DENY

        # 1. 역할 검증
        if principal.role != UserRole.ADMIN:
            return Decision.DENY

        # 2. TOTP MFA 인증 여부 검증 (BR-A7)
        if not mfa_verified:
            return Decision.DENY

        return Decision.ALLOW
