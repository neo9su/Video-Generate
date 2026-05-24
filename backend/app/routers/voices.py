"""Voice / TTS management routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_voices():
    return {"voices": []}


@router.post("/")
async def create_voice():
    return {"message": "voice created"}


@router.delete("/{voice_id}")
async def delete_voice(voice_id: int):
    return {"voice_id": voice_id, "deleted": True}
