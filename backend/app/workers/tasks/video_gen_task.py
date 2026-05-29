"""Celery task: AI video generation via ComfyUI + Sulphur 2."""
import asyncio
from ..celery_app import celery_app


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=1, time_limit=1800, soft_time_limit=1740)
def generate_video_clips(self, task_id: int, user_id: int = 1):
    """Generate AI video clips for all scenes using SiliconFlow API.
    
    Time limit: 30 minutes (6 scenes × 4 min each + buffer).
    Called after image generation step completes.
    """
    return _run_async(_video_gen_async(self, task_id, user_id))


async def _video_gen_async(self, task_id: int, user_id: int):
    from sqlalchemy import select
    from ...database import AsyncSessionLocal
    from ...models.task import Task, TaskStatus
    from ...config import settings
    from ...services.video_generation_service import video_gen_service
    import os

    async with AsyncSessionLocal() as db:
        q = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        result = await db.execute(q)
        task = result.scalar_one_or_none()
        if not task:
            return {"error": f"Task {task_id} not found"}

        od = dict(task.output_data or {})
        storyboard = od.get("storyboard", [])
        generated_images = od.get("generated_images", [])

        if not storyboard:
            return {"error": "No storyboard found"}

        try:
            video_paths = await video_gen_service.generate_scenes_video(
                scenes=storyboard,
                output_dir=f"{settings.output_dir}/tasks/{task_id}",
                task_id=str(task_id),
                image_paths=generated_images if generated_images else None,
            )

            video_clips = []
            for i, vid_path in enumerate(video_paths):
                if i < len(storyboard) and vid_path:
                    storyboard[i]["video_path"] = vid_path
                    video_clips.append(vid_path)

            od["video_clips"] = video_clips
            od["storyboard"] = storyboard
            task.output_data = od
            task.progress = 75
            await db.commit()

            return {"task_id": task_id, "video_clips": len(video_clips)}

        except Exception as e:
            od["video_gen_error"] = str(e)[:300]
            task.output_data = od
            await db.commit()
            return {"error": str(e)[:300]}
