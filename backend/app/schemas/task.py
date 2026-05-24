"""Pydantic schemas for tasks."""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class TaskCreate(BaseModel):
    title: str
    input_data: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None


class TaskStartRequest(BaseModel):
    """Optional parameters when starting a task."""
    pass


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    status: str
    progress: int = 0
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
