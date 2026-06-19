"""SummarizationSettings — env-driven config (infrastructure-design).

``summarization_enabled`` gates the real read path: the app-shell mounts U7 only when the
required deps (Bedrock model ids + S3 bucket) are configured — otherwise it skips
(fail-closed, no silent mock fallback; real-first).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Concrete model bindings (TD-S3). modelVer is part of the immutable cache key.
DEFAULT_SUMMARY_MODEL = "anthropic.claude-sonnet-4-6"
DEFAULT_TRANSLATE_MODEL = "anthropic.claude-haiku-4-5"
MODEL_VER = "sonnet46-haiku45"


@dataclass(frozen=True, slots=True)
class SummarizationSettings:
    summary_model_id: str
    translate_model_id: str
    s3_bucket: str | None
    redis_url: str | None
    database_url: str | None
    region_name: str | None
    redis_ttl_seconds: int
    model_ver: str
    # Full-text viewer (Q5=C) gate. OFF by default: exposing arXiv full text requires a
    # confirmed OA-license signal, which the current source has no metadata for. Until
    # license gating is wired, the endpoint returns ``license_unavailable`` (arXiv link-out).
    fulltext_viewer_enabled: bool = False

    @property
    def summarization_enabled(self) -> bool:
        # Real path requires Bedrock (always) + a permanent store bucket.
        return bool(self.s3_bucket)

    @classmethod
    def from_env(cls) -> SummarizationSettings:
        return cls(
            summary_model_id=os.environ.get("DOCSURI_SUMMARY_MODEL_ID", DEFAULT_SUMMARY_MODEL),
            translate_model_id=os.environ.get(
                "DOCSURI_TRANSLATE_MODEL_ID", DEFAULT_TRANSLATE_MODEL
            ),
            s3_bucket=os.environ.get("DOCSURI_SUMMARY_BUCKET"),
            redis_url=os.environ.get("DOCSURI_REDIS_URL"),
            database_url=os.environ.get("DATABASE_URL"),
            region_name=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
            redis_ttl_seconds=int(os.environ.get("DOCSURI_SUMMARY_TTL", "86400")),  # 24h (§11)
            model_ver=MODEL_VER,
            fulltext_viewer_enabled=os.environ.get("DOCSURI_FULLTEXT_VIEWER_ENABLED", "").lower()
            in ("1", "true", "yes"),
        )
