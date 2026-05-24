"""Webhook model."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from ..database import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String(512), nullable=False)
    events = Column(JSON)  # ["task.completed", "task.failed", etc.]
    is_active = Column(Boolean, default=True)
    secret = Column(String(64))
    created_at = Column(DateTime, server_default=func.now())
