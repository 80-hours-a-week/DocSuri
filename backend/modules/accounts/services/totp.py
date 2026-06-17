"""TOTP (RFC 6238) MFA service for the admin control plane (BR-A7).

Admins enroll a TOTP secret (returned as an ``otpauth://`` provisioning URI for a QR code), then
prove possession via /auth/mfa/verify to elevate their session (mfa_verified=True). The plaintext
secret is persisted on the account row and MUST NOT be logged or returned in any response (SEC-3)."""

from __future__ import annotations

import pyotp

from ..repository.credential import AccountTable, CredentialRepository

_ISSUER = "DocSuri"


class TotpService:
    def __init__(self, credential_repo: CredentialRepository):
        self._repo = credential_repo

    def enroll(self, account: AccountTable) -> str:
        """새 TOTP 시크릿을 생성·저장하고 otpauth:// 프로비저닝 URI(QR용)를 반환한다.
        재등록 시 기존 시크릿을 교체한다(분실 복구). 평문 시크릿 자체는 응답/로그에 노출하지 않는다."""
        secret = pyotp.random_base32()
        account.totp_secret = secret
        self._repo.update_account(account)
        return pyotp.totp.TOTP(secret).provisioning_uri(name=account.email, issuer_name=_ISSUER)

    def verify(self, account: AccountTable, code: str) -> bool:
        """제출된 코드를 계정의 TOTP 시크릿으로 검증한다. 미등록 계정/빈 코드는 항상 False(Fail-Closed).
        valid_window=1로 ±1 타임스텝(30초) 시계 오차를 허용한다."""
        if not account.totp_secret or not code:
            return False
        return pyotp.TOTP(account.totp_secret).verify(code, valid_window=1)
