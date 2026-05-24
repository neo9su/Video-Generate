"""Task management routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_tasks():
    return {"tasks": []}


@router.post("/")
async def create_task():
    return {"message": "task created"}


@router.get("/{task_id}")
async def get_task(task_id: int):
    return {"task_id": task_id}


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    return {"task_id": task_id, "deleted": True}
