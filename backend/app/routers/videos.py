"""Video management routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_videos():
    return {"videos": []}


@router.get("/{video_id}")
async def get_video(video_id: int):
    return {"video_id": video_id}


@router.delete("/{video_id}")
async def delete_video(video_id: int):
    return {"video_id": video_id, "deleted": True}
