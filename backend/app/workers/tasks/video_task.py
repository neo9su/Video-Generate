"""Celery task: video generation."""
from ..celery_app import celery_app


@celery_app.task
def generate_video(task_id: int, image_paths: list):
    """Generate video from images."""
    return {"task_id": task_id, "status": "video_generated"}
