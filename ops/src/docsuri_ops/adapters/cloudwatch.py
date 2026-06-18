"""CloudWatch EventStore adapter — ships telemetry to AWS CloudWatch Logs + Metrics.

Implements the EventStore protocol so ObservabilityHub can write to CloudWatch without
code changes. Metric events → CloudWatch Metrics (PutMetricData); log/audit events →
CloudWatch Logs (PutLogEvents).

``append`` is NON-BLOCKING: it enqueues the event and a single background daemon thread does
the boto3 calls. This matters because the U6 gateway emits per-request from the async event
loop — a synchronous PutMetricData there would block the loop and serialize all requests.
The worker drains a burst of queued events and ships metrics **batched** (one PutMetricData
call per ~100 datums) so per-request latency/throughput don't cost one API call each.
Shipping on one worker also means ``_seen`` / ``_sequence_token`` are mutated by exactly one
thread, so concurrent producers (gateway loop thread + FastAPI sync-route worker threads)
don't race. retry is boto3's; loss is bounded to whatever is queued at an abrupt exit. (US-R4)

Usage:
    store = CloudWatchEventStore(namespace="DocSuri/Prod", log_group="/docsuri/ops")
    hub = ObservabilityHub(store)
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, ClassVar

from docsuri_ops.domain.enums import SignalKind
from docsuri_ops.domain.models import TelemetryEvent

log = logging.getLogger("docsuri.ops.cloudwatch")

# Bounded dedup window (LRU): preserves idempotency for redelivered events while capping memory.
# Per-request metric emission carries random event_ids, so an unbounded set would grow for the
# whole process lifetime — a production memory leak. (US-R4)
_MAX_SEEN = 100_000
# Cap the in-flight buffer; drop on backpressure rather than block a producer (best-effort).
_MAX_QUEUE = 10_000
# Drain up to this many queued events per worker iteration, then ship them together so a burst
# of per-request metrics collapses into few PutMetricData calls instead of one per metric.
_DRAIN_MAX = 1_000
# MetricData entries per PutMetricData call — well under the API's 1000-metric / 1MB ceiling.
_METRIC_BATCH = 100
_SENTINEL: Any = object()  # close() signal for the worker loop


@dataclass(slots=True)
class CloudWatchEventStore:
    # Write-only store: append() ships to CloudWatch but list_events() can't read it back
    # (returns []). Signals the dashboard to report None — not fabricated zeros — for
    # event-derived metrics; read those from the CloudWatch console / GetMetricData. (US-R4)
    supports_readback: ClassVar[bool] = False
    namespace: str = "DocSuri/Production"
    log_group: str = "/docsuri/ops"
    log_stream: str = "telemetry"
    region_name: str | None = None
    _cw_client: Any = field(default=None, repr=False)
    _logs_client: Any = field(default=None, repr=False)
    _sequence_token: str | None = field(default=None, repr=False)
    _seen: OrderedDict[str, None] = field(default_factory=OrderedDict, repr=False)
    _queue: queue.Queue = field(
        default_factory=lambda: queue.Queue(maxsize=_MAX_QUEUE), repr=False
    )
    _worker: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # One daemon worker ships everything off the request path (see module docstring).
        self._worker = threading.Thread(target=self._run, name="cw-telemetry", daemon=True)
        self._worker.start()

    def append(self, event: TelemetryEvent) -> bool:
        # Non-blocking: enqueue and return; the worker dedups + ships. Drop on a full queue
        # rather than block a request (telemetry is best-effort, cf. discovery BR-14). (US-R4)
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            log.warning("cloudwatch: telemetry queue full — dropping %s", event.event_id)
            return False

    def _run(self) -> None:
        while True:
            first = self._queue.get()  # block for at least one
            gets, stop = 1, False
            if first is _SENTINEL:
                self._queue.task_done()
                return
            batch = [first]
            while len(batch) < _DRAIN_MAX:  # then drain whatever else is already queued
                try:
                    nxt = self._queue.get_nowait()
                except queue.Empty:
                    break
                gets += 1
                if nxt is _SENTINEL:
                    stop = True
                    break
                batch.append(nxt)
            try:
                self._ship_batch(batch)
            finally:
                for _ in range(gets):  # one task_done per get()/get_nowait() so flush() unblocks
                    self._queue.task_done()
            if stop:
                return

    def _ship_batch(self, events: list[TelemetryEvent]) -> None:
        # Worker-thread-only: dedup state is single-writer here, so no lock is needed.
        fresh: list[TelemetryEvent] = []
        for event in events:
            if event.dedup_key in self._seen:
                continue
            self._seen[event.dedup_key] = None
            if len(self._seen) > _MAX_SEEN:
                self._seen.popitem(last=False)  # evict oldest — bound the dedup window (US-R4)
            fresh.append(event)

        metrics = [e for e in fresh if e.kind is SignalKind.METRIC]
        if metrics:
            try:
                self._put_metrics(metrics)
            except Exception:
                log.warning("cloudwatch: failed to ship %d metrics", len(metrics), exc_info=True)
        # Logs/audits stay one-by-one — lower volume, and PutLogEvents carries sequence-token state.
        for event in fresh:
            if event.kind is SignalKind.METRIC:
                continue
            try:
                self._put_log(event)
            except Exception:
                log.warning("cloudwatch: failed to ship event %s", event.event_id, exc_info=True)

    def flush(self) -> None:
        """Block until all queued events have been shipped (graceful shutdown / tests)."""
        self._queue.join()

    def close(self) -> None:
        """Stop the worker after draining the queue (graceful shutdown)."""
        self._queue.put(_SENTINEL)
        self._queue.join()

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

    def list_events(self) -> list[TelemetryEvent]:
        return []

    def _metric_datum(self, event: TelemetryEvent) -> dict[str, Any]:
        dimensions = [{"Name": k, "Value": v} for k, v in (event.tags or {}).items()][:10]
        return {
            "MetricName": event.name or "unnamed",
            "Value": event.value if event.value is not None else 1.0,
            "Unit": "Count",
            "Dimensions": dimensions,
        }

    def _put_metrics(self, events: list[TelemetryEvent]) -> None:
        # One PutMetricData call per chunk (same namespace) instead of one call per metric.
        client = self._get_cw()
        for i in range(0, len(events), _METRIC_BATCH):
            client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[self._metric_datum(e) for e in events[i : i + _METRIC_BATCH]],
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
