"""U7 Summarization — on-demand summary/translation of a single searched paper.

Real-first: ports + real adapters (Bedrock/S3/Redis/RDS), no Production Mock Adapter.
Grounding is a U7-owned deterministic gate (NOT the search-shaped U6 ``enforce``);
cost/observability are consumed from ``docsuri_shared.ports`` (U6 single authority).
"""
