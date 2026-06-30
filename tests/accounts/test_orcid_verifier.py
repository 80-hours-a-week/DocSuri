"""FR-27 / BR-A13 — OrcidOidcVerifier (local id_token claim verification) + Public API parsing.

ORCID는 tokeninfo가 없고 이메일을 제공하지 않는다. 서버 대 서버로 직접 받은 id_token을 디코드해
aud/iss/nonce/exp를 강제하는 보안 핵심 경로와, 공개 레코드 파싱(소속·works)을 네트워크 없이 검증한다.
"""

import base64
import json
import time
from unittest.mock import AsyncMock

import pytest

from backend.modules.accounts.integrations import oidc as oidc_mod
from backend.modules.accounts.integrations.oidc import OrcidOidcVerifier, fetch_orcid_public_record
from backend.modules.accounts.models import DomainException

CLIENT_ID = "APP-ORCIDCLIENT123"
ISS = "https://orcid.org"


def _verifier():
    return OrcidOidcVerifier(client_id=CLIENT_ID, client_secret="secret")


def _id_token(**over):
    payload = {
        "aud": CLIENT_ID,
        "iss": ISS,
        "nonce": "n1",
        "exp": int(time.time()) + 3600,
        "sub": "0000-0002-1825-0097",
        "given_name": "Josiah",
        "family_name": "Carberry",
    }
    payload.update(over)
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{body}.sig"  # 서명은 검증하지 않음(서버 대 서버 수신, JWKS는 후속)


def _with_token(**over):
    v = _verifier()
    v._exchange_code = AsyncMock(return_value=_id_token(**over))
    return v


def test_build_authorization_url_scope_openid_only():
    url = _verifier().build_authorization_url("https://app/cb", "st", "no", "chal")
    assert "orcid.org/oauth/authorize" in url
    assert "scope=openid" in url
    for frag in ("state=st", "nonce=no", "code_challenge=chal", "code_challenge_method=S256"):
        assert frag in url


@pytest.mark.asyncio
async def test_exchange_and_verify_success_no_email():
    claims = await _with_token().exchange_and_verify("code", "https://app/cb", "n1", "v1")
    assert claims.subject == "0000-0002-1825-0097"
    assert claims.email is None  # BR-A13: ORCID는 이메일 없음
    assert claims.name == "Josiah Carberry"


@pytest.mark.asyncio
async def test_name_falls_back_to_name_claim():
    v = _with_token(given_name=None, family_name=None, name="J. Carberry")
    claims = await v.exchange_and_verify("code", "https://app/cb", "n1", "v1")
    assert claims.name == "J. Carberry"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "over",
    [{"aud": "APP-OTHER"}, {"iss": "https://evil.example"}, {"nonce": "attacker"}, {"sub": None}],
)
async def test_rejects_bad_claims(over):
    with pytest.raises(DomainException):
        await _with_token(**over).exchange_and_verify("code", "https://app/cb", "n1", "v1")


@pytest.mark.asyncio
async def test_rejects_expired_token():
    v = _with_token(exp=int(time.time()) - 10)
    with pytest.raises(DomainException):
        await v.exchange_and_verify("code", "https://app/cb", "n1", "v1")


@pytest.mark.asyncio
async def test_rejects_missing_code_verifier():
    with pytest.raises(DomainException):
        await _verifier().exchange_and_verify("code", "https://app/cb", "n1", None)


# ── Public API 파싱 (best-effort) ────────────────────────────────────────────────
class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        return _FakeResp(self._payload)


_RECORD = {
    "activities-summary": {
        "employments": {
            "affiliation-group": [
                {"summaries": [{"employment-summary": {"organization": {"name": "Brown University"}}}]}
            ]
        },
        "works": {
            "group": [
                {
                    "work-summary": [
                        {
                            "title": {"title": {"value": "On the Nature of Things"}},
                            "publication-date": {"year": {"value": "2021"}},
                        }
                    ]
                }
            ]
        },
    }
}


@pytest.mark.asyncio
async def test_fetch_orcid_public_record_parses_affiliation_and_works(monkeypatch):
    monkeypatch.setattr(oidc_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient(_RECORD))
    out = await fetch_orcid_public_record("0000-0002-1825-0097")
    assert out["affiliation"] == "Brown University"
    assert out["works"] == [{"title": "On the Nature of Things", "year": 2021}]


@pytest.mark.asyncio
async def test_fetch_orcid_public_record_degrades_on_error(monkeypatch):
    def _boom(*a, **k):
        raise oidc_mod.httpx.HTTPError("network down")

    monkeypatch.setattr(oidc_mod.httpx, "AsyncClient", _boom)
    out = await fetch_orcid_public_record("0000-0002-1825-0097")
    assert out == {"affiliation": None, "works": []}
