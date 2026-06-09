"""SNS publisher — single domain-event topic.

Message attributes ``domain`` + ``event`` drive SQS subscription filter
policies (per-queue routing without per-event-topic explosion).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

from app.infra.messaging.topics import DomainTopic

logger = logging.getLogger(__name__)


class SnsPublisher:
    def __init__(self, topic_arn: str | None = None, *, client: Any | None = None) -> None:
        self._topic_arn = topic_arn or os.environ["EVENT_TOPIC_ARN"]
        self._client = client or boto3.client(
            "sns",
            endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )

    def publish(
        self,
        event: DomainTopic,
        payload: dict[str, Any],
        *,
        domain: str,
        correlation_id: str | None = None,
    ) -> str:
        """Publish ``payload`` under ``event``. Returns the SNS MessageId."""
        attrs: dict[str, Any] = {
            "domain": {"DataType": "String", "StringValue": domain},
            "event": {"DataType": "String", "StringValue": str(event)},
        }
        if correlation_id:
            attrs["correlationId"] = {"DataType": "String", "StringValue": correlation_id}

        response = self._client.publish(
            TopicArn=self._topic_arn,
            Message=json.dumps(payload),
            MessageAttributes=attrs,
        )
        message_id = response["MessageId"]
        logger.info(
            "sns.publish ok",
            extra={"event": str(event), "domain": domain, "message_id": message_id},
        )
        return message_id
