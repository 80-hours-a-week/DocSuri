"""Real-first adapters (TD-S12): Bedrock streaming, S3+Redis store, S3 full-text, RDS glossary.

No Production Mock Adapter ships. Heavy deps (boto3/redis/psycopg) are imported lazily so the
domain core and its unit tests (Fixtures/Stubs) need none of them.
"""
