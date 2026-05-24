"""Celery task: script generation."""
from ..celery_app import celery_app


@celery_app.task
def generate_script(task_id: int):
    """Generate video script for a given task."""
    return {"task_id": task_id, "status": "script_generated"}
