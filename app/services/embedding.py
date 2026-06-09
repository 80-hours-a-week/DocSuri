from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod

from app.config import Settings
from app.services.bedrock import build_bedrock_runtime_client


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed_query(self, text: str) -> list[float] | None:
        raise NotImplementedError


class BedrockMarengoEmbeddingClient(EmbeddingClient):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = build_bedrock_runtime_client(settings)

    async def embed_query(self, text: str) -> list[float] | None:
        normalized = " ".join(text.split())
        if not normalized:
            return None
        trimmed = normalized[: self.settings.retrieval_query_max_chars]
        payload = {
            "inputType": "text",
            "text": {
                "inputText": trimmed,
            },
        }
        response = await asyncio.to_thread(
            self.client.invoke_model,
            modelId=self.settings.embedding_model,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        body = json.loads(response["body"].read())
        return _extract_embedding(body)


def build_embedding_client(settings: Settings) -> EmbeddingClient:
    return BedrockMarengoEmbeddingClient(settings)


def _extract_embedding(payload: dict) -> list[float]:
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("embedding"), list):
        return data["embedding"]
    if isinstance(data, list) and data and isinstance(data[0], dict) and isinstance(data[0].get("embedding"), list):
        return data[0]["embedding"]
    if isinstance(payload.get("embedding"), list):
        return payload["embedding"]
    raise ValueError("Bedrock embedding response did not include an embedding vector.")
