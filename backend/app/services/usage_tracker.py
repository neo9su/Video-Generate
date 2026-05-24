"""Usage tracking service — quota checks, credit deduction, rate limiting."""
from datetime import datetime, timedelta
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..models.credit_transaction import CreditTransaction


class UsageTracker:
    """Tracks user credits, usage stats, and rate limits."""

    async def check_quota(self, user_id: int, db: AsyncSession) -> bool:
        """Check if user has credits to run a task."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False
        return user.credits > 0

    async def deduct_credits(
        self, user_id: int, amount: int, db: AsyncSession
    ):
        """Deduct credits and record transaction."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User {user_id} not found")

        if user.credits < amount:
            raise ValueError(f"Insufficient credits: have {user.credits}, need {amount}")

        user.credits -= amount
        user.credits_used += amount

        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            balance_after=user.credits,
            description=f"Task usage: {amount} credits",
            reference_type="task",
        )
        db.add(transaction)

    async def get_usage_stats(
        self, user_id: int, db: AsyncSession
    ) -> dict:
        """Get usage statistics for a user."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return {}

        # Count transactions in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        count_result = await db.execute(
            select(sa_func.count(CreditTransaction.id)).where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.created_at >= thirty_days_ago,
            )
        )
        recent_transactions = count_result.scalar() or 0

        return {
            "plan": user.plan,
            "credits_remaining": user.credits,
            "credits_used_total": user.credits_used,
            "credits_used_30d": recent_transactions,
            "api_rate_limit": user.api_rate_limit,
        }

    async def check_rate_limit(
        self, user_id: int, db: AsyncSession
    ) -> bool:
        """Check if user is within API rate limit."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False
        # TODO: Implement actual rate limit tracking (e.g. via Redis)
        return True


# Singleton
usage_tracker = UsageTracker()
