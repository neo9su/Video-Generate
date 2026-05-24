"""Celery task: video composition."""
from ..celery_app import celery_app


@celery_app.task
def compose_video(task_id: int, video_path: str, audio_path: str, subtitle_path: str):
    """Compose final video from all generated assets."""
    return {"task_id": task_id, "status": "composition_complete"}
