"""Prompt management routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_prompts():
    return {"prompts": []}


@router.post("/")
async def create_prompt():
    return {"message": "prompt created"}


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: int):
    return {"prompt_id": prompt_id}


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: int):
    return {"prompt_id": prompt_id, "deleted": True}
