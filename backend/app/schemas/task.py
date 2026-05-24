"""Pydantic schemas for tasks."""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class TaskCreate(BaseModel):
    title: str
    prompt_text: Optional[str] = None
    params: Optional[dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    status: str
    prompt_text: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
