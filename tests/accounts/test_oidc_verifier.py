"""FR-27 — GoogleOidcVerifier id_token verification (tokeninfo delegation).

Patches the two network calls (_exchange_code, _fetch_tokeninfo) so the security-critical
validation (aud / iss / nonce / required claims / email_verified coercion) is tested without
real HTTP. The reconcile logic that consumes OidcClaims is covered by test_social_login.
"""

from unittest.mock import AsyncMock

import pytest

from backend.modules.accounts.integrations.oidc import GoogleOidcVerifier
from backend.modules.accounts.models import DomainException

CLIENT_ID = "cid.apps.googleusercontent.com"


def _verifier():
    return GoogleOidcVerifier(client_id=CLIENT_ID, client_secret="secret")


def _info(**over):
    info = {
        "aud": CLIENT_ID,
        "iss": "https://accounts.google.com",
        "nonce": "n1",
        "sub": "google-123",
        "email": "u@docsuri.org",
        "email_verified": "true",
    }
    info.update(over)
    return info


def _with_tokeninfo(info):
    v = _verifier()
    v._exchange_code = AsyncMock(return_value="id.jwt.token")
    v._fetch_tokeninfo = AsyncMock(return_value=info)
    return v


def test_build_authorization_url_has_required_params():
    url = _verifier().build_authorization_url("https://app/cb", "st", "no")
    for fragment in ("client_id=cid", "response_type=code", "state=st", "nonce=no", "scope=openid"):
        assert fragment in url


@pytest.mark.asyncio
async def test_exchange_and_verify_success():
    v = _with_tokeninfo(_info())
    claims = await v.exchange_and_verify("code", "https://app/cb", "n1")
    assert claims.subject == "google-123"
    assert claims.email == "u@docsuri.org"
    assert claims.email_verified is True


@pytest.mark.asyncio
async def test_email_verified_false_string_coerced():
    v = _with_tokeninfo(_info(email_verified="false"))
    claims = await v.exchange_and_verify("code", "https://app/cb", "n1")
    assert claims.email_verified is False  # reconcile will then reject (BR-A9)


@pytest.mark.asyncio
async def test_aud_mismatch_rejected():
    v = _with_tokeninfo(_info(aud="someone-else.apps.googleusercontent.com"))
    with pytest.raises(DomainException):
        await v.exchange_and_verify("code", "https://app/cb", "n1")


@pytest.mark.asyncio
async def test_iss_invalid_rejected():
    v = _with_tokeninfo(_info(iss="https://evil.example"))
    with pytest.raises(DomainException):
        await v.exchange_and_verify("code", "https://app/cb", "n1")


@pytest.mark.asyncio
async def test_nonce_mismatch_rejected():
    v = _with_tokeninfo(_info(nonce="attacker"))
    with pytest.raises(DomainException):
        await v.exchange_and_verify("code", "https://app/cb", "n1")


@pytest.mark.asyncio
async def test_missing_required_claim_rejected():
    v = _with_tokeninfo(_info(sub=None))
    with pytest.raises(DomainException):
        await v.exchange_and_verify("code", "https://app/cb", "n1")
