"""U4 Library persistence adapters (port-based; in-memory default, SQL production scaffold)."""

from .memory import (
    InMemoryLibraryRepository,
    InMemorySavedSearchRepository,
    InMemorySearchHistoryRepository,
    InMemoryUserDataRepository,
)

__all__ = [
    "InMemoryUserDataRepository",
    "InMemorySavedSearchRepository",
    "InMemoryLibraryRepository",
    "InMemorySearchHistoryRepository",
]
