"""SNS+SQS messaging infra (AGENTS.md §5.3).

This is the *inter-process* counterpart to ``crosscutting/events/bus.py``
(which stays in-process). A domain publishes an Event through the in-process
bus; a bridge subscriber forwards it to ``SnsPublisher`` so worker fleets
running in other replicas / Celery workers receive it via their own SQS
queue.

Phase 0 ships the publisher + a simple long-poll consumer; queue creation
+ topic subscription is handled by Terraform / Helm later. For local dev,
LocalStack honours the same API surface.
"""

from app.infra.messaging.sns import SnsPublisher
from app.infra.messaging.sqs import SqsConsumer
from app.infra.messaging.topics import DomainTopic

__all__ = ["DomainTopic", "SnsPublisher", "SqsConsumer"]
