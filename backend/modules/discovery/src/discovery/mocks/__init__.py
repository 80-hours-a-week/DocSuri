"""mock-first test doubles (MR-1~4): deterministic fixtures + mock capability adapters +
U6 port stubs + a wiring helper. Real adapters (OpenSearch/Bedrock) replace these after
Infra/U1 corpus without changing the SearchResponse contract or domain logic (MR-4)."""

from .wiring import build_mock_orchestrator

__all__ = ["build_mock_orchestrator"]
