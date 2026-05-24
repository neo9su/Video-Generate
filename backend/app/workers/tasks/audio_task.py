"""Celery task: audio generation."""
from ..celery_app import celery_app


@celery_app.task
def generate_audio(task_id: int, script: str):
    """Generate audio narration from script."""
    return {"task_id": task_id, "status": "audio_generated"}
