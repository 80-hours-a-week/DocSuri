"""SQS long-poll consumer.

One ``SqsConsumer`` per domain queue. The consumer is intentionally thin —
heavy lifting (idempotency, business logic) happens in the dispatched
Celery task; the consumer's job is just to land messages in the broker and
ack/nack SQS visibility.

DLQ: queues are provisioned with a redrive policy in Terraform, so failures
that exhaust ``maxReceiveCount`` flow there automatically. ``§5.3 DLQ 필수``.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from collections.abc import Callable
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class SqsConsumer:
    def __init__(
        self,
        queue_url: str,
        handler: Callable[[dict[str, Any], dict[str, Any]], None],
        *,
        client: Any | None = None,
        wait_seconds: int = 20,           # long-poll cap
        visibility_timeout: int = 60,
        max_messages: int = 5,
    ) -> None:
        self._queue_url = queue_url
        self._handler = handler
        self._client = client or boto3.client(
            "sqs",
            endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        self._wait_seconds = wait_seconds
        self._visibility_timeout = visibility_timeout
        self._max_messages = max_messages
        self._stop = False

    def run_forever(self) -> None:
        """Block-poll the queue. SIGTERM / SIGINT trigger a graceful exit."""
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)
        backoff = 1.0

        while not self._stop:
            try:
                resp = self._client.receive_message(
                    QueueUrl=self._queue_url,
                    MaxNumberOfMessages=self._max_messages,
                    WaitTimeSeconds=self._wait_seconds,
                    VisibilityTimeout=self._visibility_timeout,
                    MessageAttributeNames=["All"],
                    AttributeNames=["All"],
                )
                backoff = 1.0
            except Exception:  # pragma: no cover — network / AWS transient
                logger.exception("sqs.receive failed; backing off")
                time.sleep(min(backoff, 30))
                backoff *= 2
                continue

            for msg in resp.get("Messages", []):
                self._process(msg)

    def _process(self, msg: dict[str, Any]) -> None:
        body = msg.get("Body", "")
        try:
            payload = json.loads(body)
            # SNS-delivered messages wrap the original body in {"Message": "..."}.
            if isinstance(payload, dict) and "Message" in payload and "TopicArn" in payload:
                payload = json.loads(payload["Message"])
        except Exception:
            logger.exception("sqs.message: invalid JSON; leaving for DLQ")
            return

        attrs = {
            k: v.get("StringValue") for k, v in msg.get("MessageAttributes", {}).items()
        }
        try:
            self._handler(payload, attrs)
        except Exception:
            logger.exception("sqs.handler raised; message will be redelivered or DLQ'd")
            return

        self._client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=msg["ReceiptHandle"],
        )

    def _on_signal(self, *_: Any) -> None:
        logger.info("sqs.consumer: stop signal received")
        self._stop = True
