"""Celery application factory."""

from __future__ import annotations

import os

from celery import Celery

app = Celery(
    "docsuri",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=[
        "app.infra.celery.tasks_papers",
    ],
)

# Sensible defaults aligned with §4.6 ops conventions.
app.conf.update(
    task_acks_late=True,                 # at-least-once: ack after success
    task_reject_on_worker_lost=True,     # don't lose visibility on OOM kill
    task_track_started=True,
    task_time_limit=15 * 60,             # hard kill at 15min
    task_soft_time_limit=10 * 60,
    worker_prefetch_multiplier=1,        # fair scheduling for long tasks
    worker_max_tasks_per_child=200,      # recycle to bound memory creep
    timezone="UTC",
    enable_utc=True,
)
