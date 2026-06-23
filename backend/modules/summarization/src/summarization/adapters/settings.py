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
    # FR-17 figure/table assets gate. OFF by default: the read path needs the `paper_asset`
    # manifest (written by U1) + S3 presign IAM provisioned. While off, the orchestrator gets
    # no asset_reader so the endpoint returns ``license_unavailable`` (no assets shown).
    assets_enabled: bool = False
    # Presigned GET URL lifetime for asset images (SEC-9 — short-lived).
    asset_url_ttl_seconds: int = 600
    # doc-model rich-view gate (BR-30). OFF by default, same OA-license rationale as the
    # full-text viewer: until a license signal is wired the endpoint returns
    # ``license_unavailable`` (arXiv link-out). Read-only — U1 builds/caches lazily (D6).
    docmodel_viewer_enabled: bool = False

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
            assets_enabled=os.environ.get("DOCSURI_MULTIMODAL_ASSETS_ENABLED", "").lower()
            in ("1", "true", "yes"),
            asset_url_ttl_seconds=int(os.environ.get("DOCSURI_ASSET_URL_TTL_SECONDS", "600")),
            docmodel_viewer_enabled=os.environ.get("DOCSURI_DOCMODEL_VIEWER_ENABLED", "").lower()
            in ("1", "true", "yes"),
        )
