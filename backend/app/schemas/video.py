"""Pydantic schemas for videos."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VideoResponse(BaseModel):
    id: int
    task_id: int
    file_path: str
    thumbnail_path: Optional[str] = None
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
