"""Credit Transaction model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # positive = add, negative = spend
    balance_after = Column(Integer, nullable=False)
    description = Column(String(255))
    reference_type = Column(String(50))  # "task", "purchase", "bonus"
    reference_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
