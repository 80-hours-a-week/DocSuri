"""Dependency container.

Resolves which LLM implementation, glossary store, verifier, and storage
backend to inject — switched by env. AGENTS.md §5.2 forbids domain↔domain
imports, but a *composition root* like this is the canonical place to
wire concrete implementations to ports.
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.crosscutting.glossary.protocol import GlossaryPort
from app.crosscutting.ratelimit.circuit_breaker import CircuitBreaker
from app.crosscutting.verifier.port import AlwaysSupportedVerifier, VerifierPort
from app.infra.llm.protocol import LLMPort


@lru_cache
def llm() -> LLMPort:
    """LLM 구현 선택 순서: Bedrock → Anthropic 직접 → MockLLM."""
    if os.getenv("AWS_BEDROCK_REGION"):
        from app.infra.llm.bedrock import BedrockAdapter

        return BedrockAdapter()
    if os.getenv("ANTHROPIC_API_KEY"):
        from app.infra.llm.claude import ClaudeAdapter

        return ClaudeAdapter()
    from app.infra.llm.mock import MockLLM

    return MockLLM()


@lru_cache
def glossary() -> GlossaryPort:
    from app.crosscutting.glossary.store import InMemoryGlossary

    return InMemoryGlossary()


@lru_cache
def verifier() -> VerifierPort:
    # Sprint 1 stub. Sprint 2 will swap in Claude-Haiku entailment.
    return AlwaysSupportedVerifier()


@lru_cache
def embedding() -> "OpenAIEmbeddingAdapter":
    """OpenAI text-embedding-3-large adapter (lazy import; needs OPENAI_API_KEY)."""
    from app.infra.embedding.openai import OpenAIEmbeddingAdapter

    return OpenAIEmbeddingAdapter()


@lru_cache
def pgvector() -> "PgVectorClient":
    """asyncpg-backed pgvector client (lazy import; needs DATABASE_URL)."""
    from app.infra.storage.pgvector import PgVectorClient

    return PgVectorClient()


@lru_cache
def cache() -> "RedisCache":
    """Redis cache client (lazy import; needs REDIS_URL; gracefully no-ops if absent)."""
    from app.infra.storage.redis_cache import RedisCache

    return RedisCache()


@lru_cache
def arxiv_client() -> "ArxivClient":
    from app.infra.http.arxiv import ArxivClient
    return ArxivClient()


@lru_cache
def s2_client() -> "SemanticScholarClient":
    from app.infra.http.semantic_scholar import SemanticScholarClient
    return SemanticScholarClient()


@lru_cache
def openalex_client() -> "OpenAlexClient":
    from app.infra.http.openalex import OpenAlexClient
    return OpenAlexClient()


@lru_cache
def crossref_client() -> "CrossRefClient":
    from app.infra.http.crossref import CrossRefClient
    return CrossRefClient()


@lru_cache
def pubmed_client() -> "PubMedClient":
    from app.infra.http.pubmed import PubMedClient
    return PubMedClient()


@lru_cache
def arxiv_cb() -> CircuitBreaker:
    return CircuitBreaker(fail_max=5, reset_timeout=30)


@lru_cache
def semantic_cb() -> CircuitBreaker:
    return CircuitBreaker(fail_max=5, reset_timeout=30)


@lru_cache
def openalex_cb() -> CircuitBreaker:
    return CircuitBreaker(fail_max=5, reset_timeout=30)


@lru_cache
def pubmed_cb() -> CircuitBreaker:
    return CircuitBreaker(fail_max=5, reset_timeout=30)


@lru_cache
def crossref_cb() -> CircuitBreaker:
    return CircuitBreaker(fail_max=5, reset_timeout=30)


def mode_label() -> str:
    return "live (Claude)" if os.getenv("ANTHROPIC_API_KEY") else "mock"
