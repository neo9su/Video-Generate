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

    count_q = select(func.count(Task.id)).where(*conditions)
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

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

    Pipeline:
    1. Generate marketing copy (LLM)
    2. Generate storyboard (LLM)
    2b. Generate highlight subtitles
    2c. Generate scene images (SD API)
    3. Generate narration audio (TTS)
    4. Compose final video (FFmpeg)
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

    task.status = TaskStatus.PROCESSING
    task.progress = 5
    await db.flush()

    # Dispatch to Celery worker for async processing
    from ..workers.tasks.pipeline_task import run_video_pipeline
    run_video_pipeline.delay(task_id, user_id)

    await db.commit()
    await db.refresh(task)

    return task
