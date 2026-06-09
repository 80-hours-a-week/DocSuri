from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import Settings


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed_query(self, text: str) -> list[float] | None:
        raise NotImplementedError


class DisabledEmbeddingClient(EmbeddingClient):
    async def embed_query(self, text: str) -> list[float] | None:
        return None


class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self, settings: Settings):
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required when EMBEDDING_PROVIDER=openai") from exc

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed_query(self, text: str) -> list[float] | None:
        normalized = " ".join(text.split())
        if not normalized:
            return None
        trimmed = normalized[: self.settings.retrieval_query_max_chars]
        response = await self.client.embeddings.create(model=self.settings.embedding_model, input=trimmed)
        return response.data[0].embedding


def build_embedding_client(settings: Settings) -> EmbeddingClient:
    if settings.use_embeddings:
        return OpenAIEmbeddingClient(settings)
    return DisabledEmbeddingClient()
