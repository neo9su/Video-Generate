"""Celery task: Path B - face swap + voice clone video remake."""
import asyncio
import os
from ..celery_app import celery_app


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=1, time_limit=1800, soft_time_limit=1740)
def run_video_remake(self, task_id: int, user_id: int = 1):
    """Run Path B: face swap + TTS re-narration.
    
    Time limit: 30 minutes (full video face swap can take 10-15 min).
    """
    return _run_async(_remake_async(self, task_id, user_id))


async def _remake_async(self, task_id: int, user_id: int):
    from sqlalchemy import select
    from ...database import AsyncSessionLocal
    from ...models.task import Task, TaskStatus
    from ...config import settings
    from ...services.face_swap_service import face_swap_service
    from ...services.voice_clone_service import voice_clone_service, edge_tts_fallback
    import subprocess
    import json

    async with AsyncSessionLocal() as db:
        q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        result = await db.execute(q)
        task = result.scalar_one_or_none()
        if not task:
            return {"error": f"Task {task_id} not found"}

        try:
            task.status = TaskStatus.PROCESSING
            task.progress = 5
            await db.commit()

            od = dict(task.output_data or {})
            task_dir = f"{settings.output_dir}/tasks/{task_id}"
            os.makedirs(task_dir, exist_ok=True)

            input_data = task.input_data or {}
            video_path = input_data.get("video_path", f"{task_dir}/original_video.mp4")
            face_path = input_data.get("face_path", f"{task_dir}/source_face.png")
            narration_text = input_data.get("narration_text", "")
            ref_audio = input_data.get("voice_sample_path", "")
            enhance_face = (task.config or {}).get("enhance_face", True)

            # Step 1: Face swap
            task.progress = 10
            await db.commit()

            swapped_path = f"{task_dir}/swapped_video.mp4"
            await face_swap_service.swap_face(
                source_face_path=face_path,
                target_video_path=video_path,
                output_path=swapped_path,
                enhancer=enhance_face,
            )
            od["swapped_video"] = swapped_path
            task.progress = 60
            task.output_data = od
            await db.commit()

            # Step 2: TTS narration
            if narration_text:
                voice_path = f"{task_dir}/narration.wav"

                # Get video duration for speed matching
                proc = await asyncio.create_subprocess_exec(
                    "ffprobe", "-v", "quiet", "-show_format", "-print_format", "json", swapped_path,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                out, _ = await proc.communicate()
                video_duration = float(json.loads(out.decode())["format"]["duration"])

                try:
                    if await voice_clone_service.check_connectivity() and ref_audio:
                        await voice_clone_service.clone_voice_narration(
                            text=narration_text,
                            ref_audio_path=ref_audio,
                            output_path=voice_path,
                            target_duration=video_duration,
                        )
                    else:
                        await edge_tts_fallback(narration_text, voice_path, video_duration)
                except Exception:
                    await edge_tts_fallback(narration_text, voice_path, video_duration)

                od["narration_audio"] = voice_path
                task.progress = 85
                task.output_data = od
                await db.commit()

                # Step 3: Replace audio
                final_path = f"{task_dir}/final_video.mp4"
                cmd = [
                    "ffmpeg", "-y",
                    "-i", swapped_path, "-i", voice_path,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                    final_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
                od["video_path"] = final_path
            else:
                od["video_path"] = swapped_path

            # Done
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.output_data = od
            await db.commit()

            return {"task_id": task_id, "status": "completed", "video_path": od["video_path"]}

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)[:500]
            task.output_data = dict(task.output_data or {})
            await db.commit()
            return {"task_id": task_id, "status": "failed", "error": str(e)[:500]}
