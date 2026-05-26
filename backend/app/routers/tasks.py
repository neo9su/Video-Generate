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
from ..services.highlight_service import highlight_service
from ..services.image_generation_service import image_gen_service
from ..services.video_generation_service import video_gen_service

router = APIRouter()


def _set_od(task, key, value):
    """Set a key on task.output_data with SQLAlchemy change detection."""
    od = task.output_data
    if od is None:
        od = {}
    od = dict(od)  # Create fresh dict to force SQLAlchemy change tracking
    od[key] = value
    task.output_data = od


def _get_od(task):
    """Get output_data dict, ensuring it's not None."""
    if task.output_data is None:
        task.output_data = {}
    return task.output_data


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

    try:
        input_data = task.input_data or {}
        product_name = input_data.get("product_name", task.title)
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
        inp = task.input_data or {}
        inp["marketing_copy"] = marketing_copy
        task.input_data = inp
        await db.flush()

        # --- Step 2: Generate storyboard ---
        storyboard = await llm_service.generate_storyboard(
            marketing_copy,
            product_name=product_name,
            product_images=product_images,
        )
        task.progress = 50
        _set_od(task, "storyboard", storyboard)
        await db.flush()

        # --- Step 2b: Generate highlight subtitles ---
        try:
            language = "zh" if any('\u4e00' <= c <= '\u9fff' for c in marketing_copy) else "en"
            highlight_words = highlight_service.detect_highlight_words(marketing_copy, language=language)

            srt_content = highlight_service.generate_srt(storyboard, language=language)
            srt_path = f"{settings.output_dir}/tasks/{task_id}/subtitles.srt"
            if srt_content:
                os.makedirs(os.path.dirname(srt_path), exist_ok=True)
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                _set_od(task, "subtitle_srt", srt_path)

            ass_content = highlight_service.generate_ass_with_highlights(
                storyboard, highlights=highlight_words, language=language,
            )
            ass_path = f"{settings.output_dir}/tasks/{task_id}/subtitles_highlight.ass"
            if ass_content:
                os.makedirs(os.path.dirname(ass_path), exist_ok=True)
                with open(ass_path, "w", encoding="utf-8") as f:
                    f.write(ass_content)
                _set_od(task, "subtitle_ass", ass_path)
                _set_od(task, "subtitle_highlights", highlight_words)

            if platform in ("tiktok", "shorts", "reels"):
                tiktok_ass = highlight_service.create_tiktok_style_subtitles(storyboard)
                tiktok_path = f"{settings.output_dir}/tasks/{task_id}/subtitles_tiktok.ass"
                if tiktok_ass:
                    os.makedirs(os.path.dirname(tiktok_path), exist_ok=True)
                    with open(tiktok_path, "w", encoding="utf-8") as f:
                        f.write(tiktok_ass)
                    _set_od(task, "subtitle_tiktok", tiktok_path)
        except Exception as e:
            _set_od(task, "subtitle_error", str(e))

        task.progress = 60
        await db.flush()

        # --- Step 2c: Generate scene images via SD API ---
        generated_images = []
        try:
            image_paths = await image_gen_service.generate_scenes_batch(
                scenes=storyboard,
                output_dir=f"{settings.output_dir}/tasks/{task_id}",
                task_id=str(task_id),
                product_images=product_images,
            )
            for i, img_path in enumerate(image_paths):
                if i < len(storyboard) and img_path:
                    storyboard[i]["image_path"] = img_path
                    generated_images.append(img_path)
            if generated_images:
                _set_od(task, "generated_images", generated_images)
                # Update storyboard with image paths
                _set_od(task, "storyboard", storyboard)
        except Exception as e:
            _set_od(task, "image_gen_error", str(e))

        await db.flush()

        # --- Step 2d: Generate AI video clips via SiliconFlow ---
        video_clips = []
        try:
            video_paths = await video_gen_service.generate_scenes_video(
                scenes=storyboard,
                output_dir=f"{settings.output_dir}/tasks/{task_id}",
                task_id=str(task_id),
                image_paths=generated_images if generated_images else None,
            )
            for i, vid_path in enumerate(video_paths):
                if i < len(storyboard) and vid_path:
                    storyboard[i]["video_path"] = vid_path
                    video_clips.append(vid_path)
            if video_clips:
                _set_od(task, "video_clips", video_clips)
                _set_od(task, "storyboard", storyboard)
        except Exception as e:
            _set_od(task, "video_gen_error", str(e))
            # Fallback: continue with images only (Ken Burns effect)

        task.progress = 65
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
            _set_od(task, "audio_path", audio_path)

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
        _set_od(task, "video_path", composed_path)
        if generated_images:
            _set_od(task, "generated_images", generated_images)
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
