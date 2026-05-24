"""Task model for generation tasks."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, JSON
from sqlalchemy.sql import func
from ..database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    progress = Column(Integer, default=0)
    input_data = Column(JSON, nullable=True)       # product images, description, etc.
    output_data = Column(JSON, nullable=True)      # generated video URLs, etc.
    config = Column(JSON, nullable=True)            # style, platform, model settings
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
