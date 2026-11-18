"""Celery app — Redis broker, eager in tests."""
from __future__ import annotations

import os

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "docintel",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    task_always_eager=os.getenv("CELERY_EAGER", "0") == "1",
    task_eager_propagates=True,
)

# autodiscover tasks
celery_app.autodiscover_tasks(["worker"], force=True)

# explicitly import to register
from worker import tasks  # noqa: E402,F401
