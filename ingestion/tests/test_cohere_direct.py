"""AWS-free unit tests for CohereDirectEmbeddingPort (fake httpx client, no network)."""

from __future__ import annotations

import httpx
import pytest

from docsuri_ingestion.adapters.cohere_direct import CohereDirectEmbeddingPort
from docsuri_ingestion.domain.errors import RetriableIngestionError, ValidationViolationError
from docsuri_ingestion.resilience import is_retriable


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Records POST bodies and replays scripted responses (one per call)."""

    def __init__(self, responder) -> None:
        self._responder = responder
        self.calls: list[dict] = []

    def post(self, url, *, headers, json):  # noqa: A002 - mirror httpx.Client.post kwarg name
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self._responder(json)


def _vectors(n: int, dim: int) -> list[list[float]]:
    return [[float(i)] * dim for i in range(n)]


def _ok_responder(dim: int):
    """A 200 response returning one dim-wide float vector per input text."""

    def _resp(body):
        return _FakeResponse(200, {"embeddings": {"float": _vectors(len(body["texts"]), dim)}})

    return _resp


def test_embed_documents_builds_v4_request_and_returns_vectors():
    dim = 4
    client = _FakeClient(_ok_responder(dim))
    port = CohereDirectEmbeddingPort(
        api_key="test-key", model="embed-v4.0", output_dimension=dim, client=client
    )

    out = port.embed_documents(["alpha", "beta"])

    assert len(out) == 2
    assert all(len(v) == dim for v in out)
    sent = client.calls[0]["json"]
    assert sent["model"] == "embed-v4.0"
    assert sent["input_type"] == "search_document"  # writer role (vector-spec §1)
    assert sent["embedding_types"] == ["float"]
    assert sent["output_dimension"] == dim
    assert sent["texts"] == ["alpha", "beta"]
    assert client.calls[0]["headers"]["Authorization"] == "Bearer test-key"


def test_sub_batches_over_96_and_preserves_order():
    client = _FakeClient(_ok_responder(4))
    port = CohereDirectEmbeddingPort(api_key="k", output_dimension=4, client=client)

    texts = [f"t{i}" for i in range(200)]
    out = port.embed_documents(texts)

    assert len(out) == 200  # 96 + 96 + 8, concatenated in order
    assert [len(c["json"]["texts"]) for c in client.calls] == [96, 96, 8]


def test_429_raises_retriable_so_backoff_wrapper_retries():
    client = _FakeClient(lambda body: _FakeResponse(429, text="rate limited"))
    port = CohereDirectEmbeddingPort(api_key="k", output_dimension=4, client=client)

    with pytest.raises(RetriableIngestionError) as exc:
        port.embed_documents(["x"])
    assert is_retriable(exc.value) is True  # _embed_with_retry will back off, not abort the shard


def test_transport_error_is_retriable():
    def _boom(_body):
        raise httpx.ConnectError("connection refused")

    port = CohereDirectEmbeddingPort(api_key="k", output_dimension=4, client=_FakeClient(_boom))

    with pytest.raises(RetriableIngestionError) as exc:
        port.embed_documents(["x"])
    assert is_retriable(exc.value) is True


def test_4xx_config_error_fails_fast():
    client = _FakeClient(lambda body: _FakeResponse(401, text="invalid api token"))
    port = CohereDirectEmbeddingPort(api_key="bad", output_dimension=4, client=client)

    with pytest.raises(ValidationViolationError):  # permanent — do not retry-storm a bad key
        port.embed_documents(["x"])
    assert not is_retriable(ValidationViolationError("x", stage="embed"))


def test_dimension_mismatch_raises_validation():
    # Fake returns 8-dim vectors but the port expects 4 → same-space guard must fire.
    client = _FakeClient(_ok_responder(8))
    port = CohereDirectEmbeddingPort(api_key="k", output_dimension=4, client=client)

    with pytest.raises(ValidationViolationError):
        port.embed_documents(["x"])


def test_missing_api_key_raises():
    with pytest.raises(ValueError):
        CohereDirectEmbeddingPort(api_key="", output_dimension=4)
