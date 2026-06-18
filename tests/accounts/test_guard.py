from backend.modules.accounts.models import Principal, UserRole, Action, AccountId
from backend.modules.accounts.guard import AuthorizationGuard, Decision

def test_authorization_guard_stateless_ownership():
    """AuthorizationGuard의 Stateless 소유권 인가 동작 검증 (BR-A6, 피드백 ④ 반영)"""
    
    # 1. 일치하는 경우 ALLOW
    owner_id = AccountId("a0000000-0000-0000-0000-000000000000")
    principal = Principal(user_id=owner_id.value, role=UserRole.USER)
    
    result = AuthorizationGuard.authorize(principal, Action.READ, owner_id)
    assert result == Decision.ALLOW

    # 2. 불일치하는 경우 DENY
    other_owner_id = AccountId("b0000000-0000-0000-0000-000000000000")
    result = AuthorizationGuard.authorize(principal, Action.READ, other_owner_id)
    assert result == Decision.DENY

    # 3. 주체가 유효하지 않은 경우 (Default Deny - SEC-8)
    result = AuthorizationGuard.authorize(None, Action.READ, owner_id)
    assert result == Decision.DENY


def test_authorization_guard_admin_mfa():
    """ADMIN 역할 권한 및 TOTP MFA 통과 여부 검증 (BR-A7)"""
    
    admin_principal = Principal(user_id="a0000000-0000-0000-0000-000000000000", role=UserRole.ADMIN)
    user_principal = Principal(user_id="b0000000-0000-0000-0000-000000000000", role=UserRole.USER)

    # 1. ADMIN + MFA Verified -> ALLOW
    assert AuthorizationGuard.authorize_admin(admin_principal, mfa_verified=True) == Decision.ALLOW

    # 2. ADMIN + MFA Unverified -> DENY
    assert AuthorizationGuard.authorize_admin(admin_principal, mfa_verified=False) == Decision.DENY

    # 3. USER + MFA Verified -> DENY (Fail-Closed)
    assert AuthorizationGuard.authorize_admin(user_principal, mfa_verified=True) == Decision.DENY

    # 4. 주체가 유효하지 않은 경우 -> DENY
    assert AuthorizationGuard.authorize_admin(None, mfa_verified=True) == Decision.DENY
