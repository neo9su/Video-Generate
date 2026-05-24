"""User model."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Plan & billing
    plan = Column(String(20), default="free")  # free, pro, enterprise
    credits = Column(Integer, default=100)
    credits_used = Column(Integer, default=0)
    api_rate_limit = Column(Integer, default=60)
    is_admin = Column(Boolean, default=False)
    subscription_id = Column(String(255), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
