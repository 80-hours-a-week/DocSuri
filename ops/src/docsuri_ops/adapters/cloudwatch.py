"""CloudWatch EventStore adapter — ships telemetry to AWS CloudWatch Logs + Metrics.

Implements the EventStore protocol so ObservabilityHub can write to CloudWatch without
code changes. Metric events → CloudWatch Metrics (PutMetricData); log/audit events →
CloudWatch Logs (PutLogEvents). Batching and retry are handled by boto3's built-in
retry configuration — this adapter is intentionally simple (no local buffer/flush thread)
because the ingestion worker and backend are single-threaded per request.

Usage:
    store = CloudWatchEventStore(namespace="DocSuri/Prod", log_group="/docsuri/ops")
    hub = ObservabilityHub(store)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from docsuri_ops.domain.enums import SignalKind
from docsuri_ops.domain.models import TelemetryEvent

log = logging.getLogger("docsuri.ops.cloudwatch")


@dataclass(slots=True)
class CloudWatchEventStore:
    namespace: str = "DocSuri/Production"
    log_group: str = "/docsuri/ops"
    log_stream: str = "telemetry"
    region_name: str | None = None
    _cw_client: Any = field(default=None, repr=False)
    _logs_client: Any = field(default=None, repr=False)
    _sequence_token: str | None = field(default=None, repr=False)
    _seen: set[str] = field(default_factory=set)

    def _get_cw(self):
        if self._cw_client is None:
            import boto3

            self._cw_client = boto3.client("cloudwatch", region_name=self.region_name)
        return self._cw_client

    def _get_logs(self):
        if self._logs_client is None:
            import boto3

            self._logs_client = boto3.client("logs", region_name=self.region_name)
            self._ensure_log_group()
        return self._logs_client

    def _ensure_log_group(self) -> None:
        try:
            self._logs_client.create_log_group(logGroupName=self.log_group)
        except self._logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        try:
            self._logs_client.create_log_stream(
                logGroupName=self.log_group, logStreamName=self.log_stream
            )
        except self._logs_client.exceptions.ResourceAlreadyExistsException:
            pass

    def append(self, event: TelemetryEvent) -> bool:
        if event.dedup_key in self._seen:
            return False
        self._seen.add(event.dedup_key)

        try:
            if event.kind is SignalKind.METRIC:
                self._put_metric(event)
            else:
                self._put_log(event)
        except Exception:
            log.warning("cloudwatch: failed to ship event %s", event.event_id, exc_info=True)
            return False
        return True

    def list_events(self) -> list[TelemetryEvent]:
        return []

    def _put_metric(self, event: TelemetryEvent) -> None:
        dimensions = [
            {"Name": k, "Value": v} for k, v in (event.tags or {}).items()
        ][:10]
        self._get_cw().put_metric_data(
            Namespace=self.namespace,
            MetricData=[
                {
                    "MetricName": event.name or "unnamed",
                    "Value": event.value if event.value is not None else 1.0,
                    "Unit": "Count",
                    "Dimensions": dimensions,
                }
            ],
        )

    def _put_log(self, event: TelemetryEvent) -> None:
        message = json.dumps(
            {
                "eventId": event.event_id,
                "kind": event.kind.value if event.kind else "log",
                "requestId": event.request_id,
                "payload": event.payload,
            },
            default=str,
            ensure_ascii=False,
        )
        kwargs: dict[str, Any] = {
            "logGroupName": self.log_group,
            "logStreamName": self.log_stream,
            "logEvents": [{"timestamp": int(time.time() * 1000), "message": message}],
        }
        if self._sequence_token:
            kwargs["sequenceToken"] = self._sequence_token
        try:
            resp = self._get_logs().put_log_events(**kwargs)
            self._sequence_token = resp.get("nextSequenceToken")
        except Exception as exc:
            if "InvalidSequenceTokenException" in type(exc).__name__:
                self._sequence_token = getattr(exc, "response", {}).get(
                    "expectedSequenceToken"
                )
            raise
