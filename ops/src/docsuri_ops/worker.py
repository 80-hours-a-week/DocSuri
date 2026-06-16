from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass

from docsuri_ops.domain.models import BudgetState, TelemetryEvent
from docsuri_ops.incidents import AiIncidentDetectorSuite, IncidentEventPublisher


@dataclass(slots=True)
class WorkerResult:
    processed: int
    published: int


def run_once(
    events: Iterable[TelemetryEvent],
    suite: AiIncidentDetectorSuite,
    publisher: IncidentEventPublisher,
    *,
    budget_state: BudgetState | None = None,
) -> WorkerResult:
    processed = 0
    published = 0
    for event in events:
        processed += 1
        candidate = suite.evaluate(event, budget_state)
        if candidate is not None and publisher.publish_candidate(candidate):
            published += 1
    return WorkerResult(processed=processed, published=published)


def run_polling_loop(
    source,
    suite: AiIncidentDetectorSuite,
    publisher: IncidentEventPublisher,
    *,
    interval_seconds: float = 1.0,
    stop_after: int | None = None,
) -> WorkerResult:
    total = WorkerResult(processed=0, published=0)
    iterations = 0
    while stop_after is None or iterations < stop_after:
        events = source.poll()
        result = run_once(events, suite, publisher)
        total = WorkerResult(
            processed=total.processed + result.processed,
            published=total.published + result.published,
        )
        iterations += 1
        if stop_after is None or iterations < stop_after:
            time.sleep(interval_seconds)
    return total


def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
