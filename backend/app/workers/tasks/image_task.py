"""Celery task: image generation."""
from ..celery_app import celery_app


@celery_app.task
def generate_image(task_id: int, prompt: str):
    """Generate images for a video task."""
    return {"task_id": task_id, "status": "images_generated"}
