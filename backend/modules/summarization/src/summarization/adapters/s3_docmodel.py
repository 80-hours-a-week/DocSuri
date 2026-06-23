"""S3DocModelReader — real ``DocModelReadPort`` (BR-30). Reads U1's cached doc-model.

The object layout mirrors U1's ``S3DocModelStore`` writer (``doc-model/{paperId}/v{ver}.json``);
a miss (NoSuchKey — not yet lazily built) or a license-disallowed object returns None so the
router surfaces ``source_unavailable``. Read-only: building/caching is U1's role (D6).
"""

from __future__ import annotations

from typing import Any

from docsuri_shared.dtos import DocModel

# Mirrors U1's doc-model object layout (read-only capability).
_DOCMODEL_PREFIX = "doc-model"


class S3DocModelReader:
    def __init__(
        self,
        *,
        bucket: str,
        region_name: str | None = None,
        client: Any | None = None,
        prefix: str = _DOCMODEL_PREFIX,
    ) -> None:
        if client is None:
            import boto3  # lazy

            client = boto3.client("s3", region_name=region_name)
        self._s3 = client
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def get_doc_model(self, paper_id: str, version: int) -> DocModel | None:
        key = f"{self._prefix}/{paper_id}/v{version}.json"
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            return DocModel.model_validate_json(obj["Body"].read())
        except Exception:  # noqa: BLE001 — miss / not-yet-built / disallowed → source_unavailable
            return None
