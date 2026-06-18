"""U7-owned capability ports (logical-components.md §2). Real adapters (Bedrock/S3/Redis/RDS)
implement them; unit tests use test-only Fixtures/Stubs (real-first, no Production Mock).

Cross-cutting U6 hooks (CostGuardCircuitBreaker, ObservabilityHub) are NOT redefined here —
import them from ``docsuri_shared.ports`` (single authority = U6, INV-2).
"""
