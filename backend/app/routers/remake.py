"""路径B: Face swap + voice clone - async API.

Accepts uploads, creates a task, dispatches to Celery worker.
Returns immediately with task_id for polling.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models.task import Task, TaskStatus

router = APIRouter()


@router.post("/remake")
async def start_remake(
    original_video: UploadFile = File(..., description="Original video to remake"),
    source_face: Optional[UploadFile] = File(None, description="New face image"),
    voice_sample: Optional[UploadFile] = File(None, description="Voice sample for cloning"),
    face_prompt: str = Form("", description="Prompt for face generation"),
    narration_text: str = Form("", description="Narration text (empty=Whisper extract)"),
    enhance_face: bool = Form(True, description="Apply face enhancement"),
    watermark_data: str = Form("", description="Watermark annotation JSON"),
    user_id: int = Form(1, description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """Submit a video remake job (async).

    Returns task_id immediately. Poll GET /remake/{task_id} for status.
    """
    # Create task
    task = Task(
        user_id=user_id,
        title=f"Video Remake - {original_video.filename}",
        status=TaskStatus.PENDING,
        progress=0,
        input_data={"pipeline": "path_b", "original_filename": original_video.filename},
        config={"enhance_face": enhance_face, "face_prompt": face_prompt},
    )
    if watermark_data:
        try:
            import json
            parsed = json.loads(watermark_data)
            task.config["watermark"] = parsed
        except json.JSONDecodeError:
            pass
    db.add(task)
    await db.flush()
    await db.refresh(task)
    task_id = task.id

    # Save uploaded files
    task_dir = f"{settings.output_dir}/tasks/{task_id}"
    os.makedirs(task_dir, exist_ok=True)

    video_path = f"{task_dir}/original_video.mp4"
    with open(video_path, "wb") as f:
        f.write(await original_video.read())

    face_path = ""
    if source_face:
        face_path = f"{task_dir}/source_face.png"
        with open(face_path, "wb") as f:
            f.write(await source_face.read())

    voice_path = ""
    if voice_sample:
        voice_path = f"{task_dir}/voice_sample.wav"
        with open(voice_path, "wb") as f:
            f.write(await voice_sample.read())

    # Update task input_data with file paths
    inp = dict(task.input_data or {})
    inp["video_path"] = video_path
    inp["face_path"] = face_path
    inp["voice_sample_path"] = voice_path
    inp["narration_text"] = narration_text
    task.input_data = inp
    await db.commit()

    # Dispatch to Celery worker
    from ..workers.tasks.remake_task import run_video_remake
    run_video_remake.delay(task_id, user_id)

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Remake job submitted. Poll GET /remake/{task_id} for progress.",
    }


@router.get("/remake/{task_id}")
async def get_remake_status(
    request: Request,
    task_id: int,
    user_id: int = Query(1),
    db: AsyncSession = Depends(get_db),
):
    """Get status of a remake task."""
    q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(q)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    output_data = dict(task.output_data) if isinstance(task.output_data, dict) else {}
    if output_data.get("video_path") and os.path.exists(str(output_data["video_path"])):
        output_data["video_url"] = str(request.url_for("download_remake_video", task_id=task_id))
    else:
        fallback = os.path.join(settings.output_dir, "tasks", str(task_id), "swapped_video.mp4")
        if os.path.exists(fallback):
            output_data["video_url"] = str(request.url_for("download_remake_video", task_id=task_id))

    return {
        "task_id": task_id,
        "status": task.status.value,
        "progress": task.progress,
        "output_data": output_data,
        "error_message": task.error_message,
    }


@router.get("/remake/{task_id}/download")
async def download_remake_video(
    task_id: int,
    user_id: int = Query(1),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(q)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    video_path = (task.output_data or {}).get("video_path", "")
    raw_output = task.output_data
    video_path = raw_output.get("video_path", "") if isinstance(raw_output, dict) else ""
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(video_path, media_type="video/mp4", filename=os.path.basename(video_path))
