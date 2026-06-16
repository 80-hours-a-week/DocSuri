from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from docsuri_shared.vector_spec import DIMENSIONS, EMBEDDING_SPEC

from docsuri_ingestion.domain.enums import FailureReason
from docsuri_ingestion.domain.errors import RetriableIngestionError, ValidationViolationError
from docsuri_ingestion.domain.models import IndexRecordBatch, IndexStats, ParsedPaper, Tombstone
from docsuri_ingestion.ports import QueueMessage


class S3FullTextStore:
    def __init__(
        self, *, bucket: str, prefix: str = "full-text", kms_key_id: str | None = None
    ) -> None:
        import boto3

        self._client = boto3.client("s3")
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._kms_key_id = kms_key_id

    def put_full_text(self, paper: ParsedPaper) -> str:
        key = f"{self._prefix}/{paper.paper_id}/v{paper.version}.txt"
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": paper.full_text.encode("utf-8"),
            "ContentType": "text/plain; charset=utf-8",
            "ServerSideEncryption": "aws:kms" if self._kms_key_id else "AES256",
            "Metadata": {
                "paper-id": paper.paper_id,
                "version": str(paper.version),
                "license": paper.license_url,
            },
        }
        if self._kms_key_id:
            kwargs["SSEKMSKeyId"] = self._kms_key_id
        self._client.put_object(**kwargs)
        return f"s3://{self._bucket}/{key}"


class BedrockCohereEmbeddingPort:
    def __init__(self, *, model_id: str, region_name: str | None = None) -> None:
        import boto3

        self._client = boto3.client("bedrock-runtime", region_name=region_name)
        self._model_id = model_id

    def embed_documents(
        self,
        texts: list[str] | tuple[str, ...],
        *,
        correlation_id: str | None = None,
    ) -> list[list[float]]:
        del correlation_id
        if EMBEDDING_SPEC.input_type_writer != "search_document":
            raise RuntimeError("Bedrock writer must use search_document input type")
        body = {
            "texts": list(texts),
            "input_type": EMBEDDING_SPEC.input_type_writer,
            "embedding_types": ["float"],
        }
        response = self._client.invoke_model(
            modelId=self._model_id,
            body=json.dumps(body).encode("utf-8"),
            accept="application/json",
            contentType="application/json",
        )
        payload = json.loads(response["body"].read().decode("utf-8"))
        vectors = payload.get("embeddings", [])
        if isinstance(vectors, dict):
            vectors = vectors.get("float", [])
        for vector in vectors:
            if len(vector) != DIMENSIONS:
                raise ValidationViolationError(
                    f"Bedrock returned vector dimension {len(vector)}, expected {DIMENSIONS}",
                    stage="embed",
                )
        return vectors


class OpenSearchVectorIndex:
    def __init__(
        self,
        *,
        endpoint: str,
        index_name: str,
        username: str | None = None,
        password: str | None = None,
        stats_ttl_seconds: float = 60.0,
    ) -> None:
        from opensearchpy import OpenSearch

        http_auth = (username, password) if username and password else None
        self._client = OpenSearch(
            hosts=[endpoint], http_auth=http_auth, use_ssl=True, verify_certs=True
        )
        self._index_name = index_name
        self._stats_cache = IndexStatsTtlCache(ttl_seconds=stats_ttl_seconds)
        self._last_write_timestamp: datetime | None = None

    def bulk_upsert(self, batch: IndexRecordBatch) -> None:
        lines: list[str] = []
        for record in batch.records:
            lines.append(json.dumps({"index": {"_index": self._index_name, "_id": record.chunkId}}))
            lines.append(json.dumps(record.model_dump(mode="json")))
        body = "\n".join(lines) + "\n"
        response = self._client.bulk(body=body)
        failures = collect_bulk_failures(response)
        if failures:
            raise RetriableIngestionError(
                f"OpenSearch bulk had {len(failures)} failed item(s)",
                reason=FailureReason.BULK_INDEX_PARTIAL_FAILURE,
                stage="index",
            )
        self._record_write()
        self._stats_cache.invalidate()

    def tombstone_paper(self, tombstone: Tombstone) -> None:
        # Version ordering is guarded by ControlPlaneStore. The index operation deletes
        # all existing chunks for the paper that won that CAS.
        self._client.delete_by_query(
            index=self._index_name,
            body={"query": {"term": {"paperId": tombstone.paper_id}}},
            refresh=True,
            conflicts="proceed",
        )
        self._record_write()
        self._stats_cache.invalidate()

    def delete_stale_chunks(self, paper_id: str, keep_chunk_ids: set[str]) -> None:
        if not keep_chunk_ids:
            return
        self._client.delete_by_query(
            index=self._index_name,
            body={
                "query": {
                    "bool": {
                        "filter": [{"term": {"paperId": paper_id}}],
                        "must_not": [{"terms": {"chunkId": sorted(keep_chunk_ids)}}],
                    }
                }
            },
            refresh=True,
            conflicts="proceed",
        )
        self._record_write()
        self._stats_cache.invalidate()

    def index_stats(self) -> IndexStats:
        return self._stats_cache.get_or_refresh(self._index_name, self._fetch_stats)

    def _fetch_stats(self) -> IndexStats:
        count = int(self._client.count(index=self._index_name).get("count", 0))
        return IndexStats(
            status="HEALTHY",
            timestamp=datetime.now(UTC),
            index_name=self._index_name,
            total_documents=count,
            vector_count=count,
            last_write_timestamp=self._last_write_timestamp,
            dependencies={"opensearch": "UP"},
        )

    def _record_write(self) -> None:
        self._last_write_timestamp = datetime.now(UTC)


class IndexStatsTtlCache:
    def __init__(self, *, ttl_seconds: float) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._value: IndexStats | None = None
        self._expires_at = datetime.min.replace(tzinfo=UTC)

    def get_or_refresh(self, index_name: str, refresh: Any) -> IndexStats:
        now = datetime.now(UTC)
        if self._value is not None and now < self._expires_at:
            return self._value
        self._value = refresh()
        self._expires_at = now + self._ttl
        if self._value.index_name != index_name:
            raise RuntimeError("index stats cache returned mismatched index")
        return self._value

    def invalidate(self) -> None:
        self._expires_at = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class SqsMessage:
    message_id: str
    receipt_handle: str
    body: dict[str, Any]


class SqsQueue:
    def __init__(self, *, queue_url: str, dlq_url: str, region_name: str | None = None) -> None:
        import boto3

        self._client = boto3.client("sqs", region_name=region_name)
        self._queue_url = queue_url
        self._dlq_url = dlq_url

    def send_job(self, job) -> None:
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(
                {
                    "jobId": job.job_id,
                    "kind": job.kind.value,
                    "arxivRef": job.arxiv_ref,
                    "eventId": job.event_id,
                    "correlationId": job.correlation_id,
                }
            ),
        )

    def receive_messages(self, max_messages: int = 10) -> list[SqsMessage]:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20,
        )
        messages = []
        for message in response.get("Messages", []):
            messages.append(
                SqsMessage(
                    message_id=message["MessageId"],
                    receipt_handle=message["ReceiptHandle"],
                    body=json.loads(message["Body"]),
                )
            )
        return messages

    def ack(self, message: QueueMessage) -> None:
        self._client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=message.receipt_handle,
        )

    def send_to_dlq(self, payload: dict[str, Any], *, reason: str) -> None:
        self._client.send_message(
            QueueUrl=self._dlq_url,
            MessageBody=json.dumps({"reason": reason, "payload": payload}),
        )

    def parse_new_arxiv_event(self, payload: dict[str, Any]):
        from docsuri_shared.events import NewArxivEvent

        return NewArxivEvent.model_validate(payload)


def collect_bulk_failures(response: dict[str, Any]) -> list[dict[str, Any]]:
    if not response.get("errors"):
        return []
    failures: list[dict[str, Any]] = []
    for item in response.get("items", []):
        operation = next(iter(item.values()))
        status = int(operation.get("status", 500))
        if status >= 300:
            failures.append(operation)
    return failures
