import pytest

from backend.modules.accounts.controller import _InProcessOidcStateStore


@pytest.mark.asyncio
async def test_oidc_state_store_consumes_once_and_binds_provider():
    store = _InProcessOidcStateStore()
    await store.put("state-1", provider="ORCID", nonce="nonce-1", code_verifier="verifier-1")

    assert await store.consume("state-1", provider="GOOGLE") is None
    assert await store.consume("state-1", provider="ORCID") is None

    await store.put("state-2", provider="ORCID", nonce="nonce-2", code_verifier="verifier-2")
    assert await store.consume("state-2", provider="ORCID") == {
        "provider": "ORCID",
        "nonce": "nonce-2",
        "code_verifier": "verifier-2",
    }
    assert await store.consume("state-2", provider="ORCID") is None
