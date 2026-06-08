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
from app.crosscutting.verifier.port import AlwaysSupportedVerifier, VerifierPort
from app.infra.llm.protocol import LLMPort


@lru_cache
def llm() -> LLMPort:
    """Real Claude if ANTHROPIC_API_KEY set, else deterministic mock."""
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


def mode_label() -> str:
    return "live (Claude)" if os.getenv("ANTHROPIC_API_KEY") else "mock"
