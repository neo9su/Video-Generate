"""Task management routes — full CRUD for video generation tasks."""
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models.task import Task, TaskStatus
from ..schemas.task import TaskCreate, TaskResponse, TaskListResponse, TaskStartRequest
from ..services.llm_service import llm_service
from ..services.tts_service import tts_service
from ..services.composition_service import composition_service

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    user_id: int = Query(1, description="User ID (placeholder until auth is integrated)"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new video generation task."""
    task = Task(
        user_id=user_id,
        title=task_data.title,
        status=TaskStatus.PENDING,
        progress=0,
        input_data=task_data.input_data,
        config=task_data.config,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    user_id: int = Query(1, description="User ID (placeholder)"),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's tasks with optional status filter."""
    conditions = [Task.user_id == user_id]
    if status:
        try:
            status_enum = TaskStatus(status)
            conditions.append(Task.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Count total
    count_q = select(func.count(Task.id)).where(*conditions)
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    # Fetch tasks
    q = select(Task).where(*conditions).order_by(Task.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    tasks = list(result.scalars().all())

    return TaskListResponse(tasks=tasks, total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    user_id: int = Query(1, description="User ID (placeholder)"),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific task."""
    q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(q)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    user_id: int = Query(1, description="User ID (placeholder)"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task by ID."""
    q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(q)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    return None


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: int,
    start_data: Optional[TaskStartRequest] = None,
    user_id: int = Query(1, description="User ID (placeholder)"),
    db: AsyncSession = Depends(get_db),
):
    """Start processing a video generation task.

    This transitions the task from 'pending' to 'processing' and kicks off
    the LLM workflow (marketing copy → storyboard → TTS → composition).
    """
    q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(q)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start task with status '{task.status.value}'. Only 'pending' tasks can be started.",
        )

    # Transition to processing
    task.status = TaskStatus.PROCESSING
    task.progress = 5
    await db.flush()

    try:
        input_data = task.input_data or {}
        product_description = input_data.get("product_description", "")
        product_images = input_data.get("product_images", [])
        task_config = task.config or {}
        style = task_config.get("style", "professional")
        platform = task_config.get("platform", "tiktok")
        voice_id = task_config.get("voice_id", "default")

        task.progress = 10
        await db.flush()

        # --- Step 1: Generate marketing copy ---
        marketing_copy = await llm_service.generate_marketing_copy(
            product_description=product_description,
            style=style,
            platform=platform,
        )
        task.progress = 30
        if task.input_data is None:
            task.input_data = {}
        task.input_data["marketing_copy"] = marketing_copy
        await db.flush()

        # --- Step 2: Generate storyboard ---
        storyboard = await llm_service.generate_storyboard(marketing_copy)
        task.progress = 50
        if task.output_data is None:
            task.output_data = {}
        task.output_data["storyboard"] = storyboard
        await db.flush()

        # --- Step 3: Generate narration audio via TTS ---
        narration_text = " ".join(
            scene.get("narration", "") for scene in storyboard
        )
        audio_path = ""
        if narration_text.strip():
            audio_bytes = await tts_service.generate_voice(narration_text, voice_id=voice_id)
            audio_path = f"{settings.output_dir}/tasks/{task_id}/narration.wav"
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            if task.output_data is None:
                task.output_data = {}
            task.output_data["audio_path"] = audio_path

        task.progress = 70
        await db.flush()

        # --- Step 4: Compose final video ---
        output_video_path = f"{settings.output_dir}/tasks/{task_id}/final_video.mp4"
        composed_path = await composition_service.compose_video(
            scenes=storyboard,
            audio_path=audio_path if audio_path else "",
            subtitles=None,
            output_path=output_video_path,
            aspect_ratio="9:16" if platform in ("tiktok", "shorts", "reels") else "16:9",
        )

        task.progress = 90
        if task.output_data is None:
            task.output_data = {}
        task.output_data["video_path"] = composed_path
        await db.flush()

        # --- Step 5: Mark completed ---
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        await db.flush()
        await db.refresh(task)

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        await db.flush()
        await db.refresh(task)

    return task
