"""Pydantic schemas for voices."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VoiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    voice_type: str = "tts"


class VoiceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    voice_type: str
    file_path: Optional[str] = None
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True
