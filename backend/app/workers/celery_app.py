"""Celery application configuration."""
from celery import Celery
from ..config import settings

celery_app = Celery(
    "video_generate",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.script_task",
        "app.workers.tasks.image_task",
        "app.workers.tasks.video_task",
        "app.workers.tasks.audio_task",
        "app.workers.tasks.compose_task",
    ],
)
