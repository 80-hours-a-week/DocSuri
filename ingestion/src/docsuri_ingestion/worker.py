from __future__ import annotations

import sys
import time

from .domain.enums import FailureClass, FailureReason, JobKind
from .domain.errors import IngestionError, PermanentIngestionError
from .domain.models import IngestionJob
from .observability import configure_logging
from .runtime import build_production_runtime
from .settings import IngestionSettings


def main(argv: list[str] | None = None) -> int:
    del argv
    configure_logging()
    runtime = build_production_runtime(IngestionSettings.from_env())
    queue = runtime.queue
    while True:
        for message in queue.receive_messages(max_messages=10):
            process_message(runtime, message)
        time.sleep(1.0)


def process_message(runtime, message) -> None:
    queue = runtime.queue
    try:
        job = job_from_payload(message.body)
    except IngestionError as exc:
        runtime.observability.emit_failure_signal(
            getattr(message, "message_id", "unknown"),
            stage=exc.stage,
            error=exc.public_error(),
        )
        if exc.failure_class is FailureClass.PERMANENT:
            queue.send_to_dlq(message.body, reason=exc.public_error())
            queue.ack(message)
        return

    try:
        runtime.pipeline.ingest_one(job)
    except IngestionError as exc:
        if exc.failure_class is FailureClass.PERMANENT:
            queue.ack(message)
    else:
        queue.ack(message)


def job_from_payload(payload) -> IngestionJob:
    try:
        kind = JobKind(payload["kind"])
        job_id = payload["jobId"]
        arxiv_ref = payload.get("arxivRef")
    except (KeyError, ValueError, TypeError) as exc:
        raise PermanentIngestionError(
            "invalid queue payload",
            reason=FailureReason.POISON_EVENT,
            stage="queue",
        ) from exc
    return IngestionJob(
        job_id=job_id,
        kind=kind,
        arxiv_ref=arxiv_ref,
        event_id=payload.get("eventId"),
        correlation_id=payload.get("correlationId"),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
