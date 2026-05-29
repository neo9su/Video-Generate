"""Celery task: full video generation pipeline."""
import os
import asyncio
from ..celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine in a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=1, time_limit=2400, soft_time_limit=2340)
def run_video_pipeline(self, task_id: int, user_id: int = 1):
    """Run the complete video generation pipeline asynchronously.

    Steps:
    1. Generate marketing copy (LLM)
    2. Generate storyboard (LLM)
    2b. Generate highlight subtitles
    2c. Generate scene images (SD API, 1024x1024)
    2d. Upscale images (ComfyUI RealESRGAN 4x)
    3. Generate narration audio (TTS, non-fatal)
    4. Compose final video (FFmpeg)
    """
    return _run_async(_pipeline_async(task_id, user_id))


async def _pipeline_async(task_id: int, user_id: int):
    """Async implementation of the full pipeline."""
    from sqlalchemy import select
    from ...database import AsyncSessionLocal
    from ...models.task import Task, TaskStatus
    from ...config import settings
    from ...services.llm_service import llm_service
    from ...services.tts_service import tts_service
    from ...services.composition_service import composition_service
    from ...services.highlight_service import highlight_service
    from ...services.image_generation_service import image_gen_service
    from ...services.upscale_service import upscale_service
    from ...services.video_generation_service import video_gen_service

    async with AsyncSessionLocal() as db:
        try:
            q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
            result = await db.execute(q)
            task = result.scalar_one_or_none()
            if not task:
                return {"error": f"Task {task_id} not found"}

            if task.status != TaskStatus.PENDING:
                if task.status == TaskStatus.PROCESSING:
                    pass  # Allow re-entry from API that already set processing
                else:
                    return {"error": f"Task {task_id} status is {task.status.value}, not pending"}

            task.status = TaskStatus.PROCESSING
            task.progress = 5
            await db.commit()

            def _set_od(key, value):
                od = task.output_data or {}
                od = dict(od)
                od[key] = value
                task.output_data = od

            input_data = task.input_data or {}
            product_name = input_data.get("product_name", task.title)
            product_description = input_data.get("product_description", "")
            product_images = input_data.get("product_images", [])
            task_config = task.config or {}
            style = task_config.get("style", "professional")
            platform = task_config.get("platform", "tiktok")
            voice_id = task_config.get("voice_id", "default")

            task.progress = 10
            await db.commit()

            # --- Step 1: Generate marketing copy ---
            marketing_copy = await llm_service.generate_marketing_copy(
                product_description=product_description,
                style=style,
                platform=platform,
            )
            task.progress = 30
            inp = dict(task.input_data or {})
            inp["marketing_copy"] = marketing_copy
            task.input_data = inp
            await db.commit()

            # --- Step 2: Generate storyboard ---
            storyboard = await llm_service.generate_storyboard(
                marketing_copy,
                product_name=product_name,
                product_images=product_images,
            )
            task.progress = 50
            _set_od("storyboard", storyboard)
            await db.commit()

            # --- Step 2b: Generate highlight subtitles ---
            try:
                language = "zh" if any("\u4e00" <= c <= "\u9fff" for c in marketing_copy) else "en"
                highlight_words = highlight_service.detect_highlight_words(marketing_copy, language=language)

                srt_content = highlight_service.generate_srt(storyboard, language=language)
                srt_path = f"{settings.output_dir}/tasks/{task_id}/subtitles.srt"
                if srt_content:
                    os.makedirs(os.path.dirname(srt_path), exist_ok=True)
                    with open(srt_path, "w", encoding="utf-8") as f:
                        f.write(srt_content)
                    _set_od("subtitle_srt", srt_path)

                ass_content = highlight_service.generate_ass_with_highlights(
                    storyboard, highlights=highlight_words, language=language,
                )
                ass_path = f"{settings.output_dir}/tasks/{task_id}/subtitles_highlight.ass"
                if ass_content:
                    os.makedirs(os.path.dirname(ass_path), exist_ok=True)
                    with open(ass_path, "w", encoding="utf-8") as f:
                        f.write(ass_content)
                    _set_od("subtitle_ass", ass_path)
                    _set_od("subtitle_highlights", highlight_words)

                if platform in ("tiktok", "shorts", "reels"):
                    tiktok_ass = highlight_service.create_tiktok_style_subtitles(storyboard)
                    tiktok_path = f"{settings.output_dir}/tasks/{task_id}/subtitles_tiktok.ass"
                    if tiktok_ass:
                        os.makedirs(os.path.dirname(tiktok_path), exist_ok=True)
                        with open(tiktok_path, "w", encoding="utf-8") as f:
                            f.write(tiktok_ass)
                        _set_od("subtitle_tiktok", tiktok_path)
            except Exception as e:
                _set_od("subtitle_error", str(e))

            task.progress = 60
            await db.commit()

            # --- Step 2c: Generate scene images (1024x1024) ---
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
                    _set_od("generated_images", generated_images)
                    _set_od("storyboard", storyboard)
            except Exception as e:
                _set_od("image_gen_error", str(e))

            # --- Step 2d: Upscale (4x RealESRGAN, non-fatal) ---
            if generated_images:
                try:
                    upscaled_images = []
                    for img_path in generated_images:
                        if img_path and os.path.exists(img_path):
                            upscaled_path = img_path.replace(".png", "_upscaled.png")
                            await upscale_service.upscale_image(img_path, upscaled_path)
                            upscaled_images.append(upscaled_path)
                            for scene in storyboard:
                                if scene.get("image_path") == img_path:
                                    scene["image_path"] = upscaled_path
                                    break
                    if upscaled_images:
                        _set_od("upscaled_images", upscaled_images)
                        _set_od("storyboard", storyboard)
                except Exception as upscale_err:
                    _set_od("upscale_warning", f"Upscale skipped: {str(upscale_err)}")

            await db.commit()

            # --- Step 2e: Generate AI video clips (SiliconFlow Wan2.2) ---
            video_clips = []
            use_video_gen = (task_config.get("video_gen", True) and
                             settings.siliconflow_api_key)
            if use_video_gen:
                try:
                    # Use generated images as reference for I2V, or T2V if no images
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
                        _set_od("video_clips", video_clips)
                        _set_od("storyboard", storyboard)
                except Exception as vg_err:
                    _set_od("video_gen_error", str(vg_err)[:300])
                    # Non-fatal: fallback to image-based composition

            task.progress = 65
            await db.commit()

            # --- Step 3: TTS (non-fatal) ---
            narration_text = " ".join(scene.get("narration", "") for scene in storyboard)
            audio_path = ""
            if narration_text.strip():
                try:
                    audio_bytes = await tts_service.generate_voice(narration_text, voice_id=voice_id)
                    audio_path = f"{settings.output_dir}/tasks/{task_id}/narration.wav"
                    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                    with open(audio_path, "wb") as f:
                        f.write(audio_bytes)
                    _set_od("audio_path", audio_path)
                except Exception as tts_err:
                    _set_od("tts_warning", f"TTS skipped: {str(tts_err)}")

            task.progress = 70
            await db.commit()

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
            _set_od("video_path", composed_path)
            if generated_images:
                _set_od("generated_images", generated_images)
            await db.commit()

            # --- Done ---
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            await db.commit()

            return {"task_id": task_id, "status": "completed", "video_path": composed_path}

        except Exception as e:
            try:
                # Re-fetch task to update status
                q2 = select(Task).where(Task.id == task_id)
                r2 = await db.execute(q2)
                task = r2.scalar_one_or_none()
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)[:500]
                    await db.commit()
            except Exception:
                pass
            return {"task_id": task_id, "status": "failed", "error": str(e)[:500]}
