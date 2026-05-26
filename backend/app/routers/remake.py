"""路径B: Face swap + voice clone pipeline.

This router handles the "video remake" workflow:
  1. User uploads original video + face reference + voice sample
  2. System generates a new face (or uses user-provided one)
  3. FaceFusion swaps the face in the original video
  4. Whisper extracts the original narration text
  5. CosyVoice2 re-narrates with cloned voice
  6. FFmpeg replaces audio track
"""
import os
import subprocess
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models.task import Task, TaskStatus
from ..services.face_swap_service import face_swap_service
from ..services.voice_clone_service import voice_clone_service

router = APIRouter()


@router.post("/remake")
async def remake_video(
    original_video: UploadFile = File(..., description="Original video to remake"),
    source_face: Optional[UploadFile] = File(None, description="New face image (optional, will generate if not provided)"),
    voice_sample: Optional[UploadFile] = File(None, description="Voice sample for cloning"),
    face_prompt: str = Form("", description="Text prompt for face generation (if no source_face)"),
    narration_text: str = Form("", description="Narration text (if empty, will use Whisper to extract from video)"),
    enhance_face: bool = Form(True, description="Apply face enhancement after swap"),
    user_id: int = Form(1, description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """Full path B pipeline: face swap + voice clone remake.

    Returns task info with progress tracking.
    """
    # Create task
    task = Task(
        user_id=user_id,
        title=f"Video Remake - {original_video.filename}",
        status=TaskStatus.PROCESSING,
        progress=5,
        input_data={"pipeline": "path_b", "original_filename": original_video.filename},
        config={"enhance_face": enhance_face, "face_prompt": face_prompt},
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    task_id = task.id

    task_dir = f"{settings.output_dir}/tasks/{task_id}"
    os.makedirs(task_dir, exist_ok=True)

    try:
        # Save uploaded files
        video_path = f"{task_dir}/original_video.mp4"
        with open(video_path, "wb") as f:
            content = await original_video.read()
            f.write(content)

        task.progress = 10
        await db.flush()

        # Step 1: Get or generate source face
        face_path = f"{task_dir}/source_face.png"
        if source_face:
            with open(face_path, "wb") as f:
                f.write(await source_face.read())
        else:
            # Generate synthetic face
            face_path = await face_swap_service.generate_synthetic_face(
                prompt=face_prompt or None,
                output_path=face_path,
            )

        task.progress = 20
        _set_od(task, "source_face", face_path)
        await db.flush()

        # Step 2: Face swap
        swapped_path = f"{task_dir}/swapped_video.mp4"
        await face_swap_service.swap_face(
            source_face_path=face_path,
            target_video_path=video_path,
            output_path=swapped_path,
            enhancer=enhance_face,
        )

        task.progress = 60
        _set_od(task, "swapped_video", swapped_path)
        await db.flush()

        # Step 3: Get narration text (Whisper or user-provided)
        if not narration_text:
            narration_text = await _extract_narration(video_path, task_dir)

        _set_od(task, "narration_text", narration_text)
        task.progress = 70
        await db.flush()

        # Step 4: Voice clone narration
        voice_path = f"{task_dir}/cloned_narration.wav"
        ref_audio = f"{task_dir}/voice_sample.wav"

        if voice_sample:
            with open(ref_audio, "wb") as f:
                f.write(await voice_sample.read())
        else:
            # Use default voice sample
            ref_audio = voice_clone_service.default_ref_audio

        # Get video duration for speed matching
        video_duration = await _get_video_duration(swapped_path)

        await voice_clone_service.clone_voice_narration(
            text=narration_text,
            ref_audio_path=ref_audio,
            output_path=voice_path,
            target_duration=video_duration,
        )

        task.progress = 85
        _set_od(task, "cloned_audio", voice_path)
        await db.flush()

        # Step 5: Replace audio
        final_path = f"{task_dir}/final_video.mp4"
        await _replace_audio(swapped_path, voice_path, final_path)

        task.progress = 100
        task.status = TaskStatus.COMPLETED
        _set_od(task, "video_path", final_path)
        await db.flush()
        await db.refresh(task)

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        await db.flush()
        await db.refresh(task)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "task_id": task_id,
        "status": task.status.value,
        "progress": task.progress,
        "output_data": task.output_data,
    }


@router.get("/remake/{task_id}")
async def get_remake_status(
    task_id: int,
    user_id: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Get status of a remake task."""
    from sqlalchemy import select
    q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(q)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task_id,
        "status": task.status.value,
        "progress": task.progress,
        "output_data": task.output_data,
        "error_message": task.error_message,
    }


def _set_od(task, key, value):
    """Set output_data key with SQLAlchemy change detection."""
    od = task.output_data
    if od is None:
        od = {}
    od = dict(od)
    od[key] = value
    task.output_data = od


async def _extract_narration(video_path: str, task_dir: str) -> str:
    """Extract narration from video using Whisper (via comfyui env on GPU server)."""
    # Upload video to server for Whisper processing
    remote_path = "/tmp/whisper_input.mp4"
    proc = await asyncio.create_subprocess_shell(
        f'cat "{video_path}" | ssh neo@10.190.0.222 "cat > {remote_path}"',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()

    # Run Whisper
    cmd = (
        'export PATH="$HOME/miniconda3/bin:$PATH" && '
        'eval "$(conda shell.bash hook)" && '
        "conda activate comfyui && "
        f"python -c \""
        "import whisper; "
        "model = whisper.load_model('base'); "
        f"result = model.transcribe('{remote_path}', language='zh'); "
        "print(result['text'])"
        "\""
    )
    proc = await asyncio.create_subprocess_exec(
        "ssh", "neo@10.190.0.222", cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    text = stdout.decode().strip()

    if not text:
        raise RuntimeError(f"Whisper extraction failed: {stderr.decode()[-300:]}")

    return text


async def _get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet", "-show_format", "-print_format", "json",
        video_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    import json
    data = json.loads(stdout.decode())
    return float(data["format"]["duration"])


async def _replace_audio(
    video_path: str, audio_path: str, output_path: str
):
    """Replace video audio track with new audio."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()
    if not os.path.exists(output_path):
        raise RuntimeError("FFmpeg audio replacement failed")


import asyncio  # noqa: E402 (needed for _extract_narration)
