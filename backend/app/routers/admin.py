"""Admin routes — system overview, user management, GPU/queue status."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..auth_deps import get_current_user
from ..models.user import User
from ..models.task import Task
from ..services.gpu_scheduler import gpu_scheduler

router = APIRouter(tags=["admin"])


async def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency that ensures the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """System overview: total users, tasks, GPU status."""
    user_count_result = await db.execute(sa_func.count(User.id))
    total_users = user_count_result.scalar() or 0

    task_count_result = await db.execute(sa_func.count(Task.id))
    total_tasks = task_count_result.scalar() or 0

    gpu_status = await gpu_scheduler.get_gpu_status()
    queue_status = await gpu_scheduler.get_queue_status()

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "gpu_status": gpu_status,
        "queue_status": queue_status,
    }


@router.get("/users")
async def list_admin_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List all users (admin only)."""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return {
        "total": len(users),
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "is_active": u.is_active,
                "plan": u.plan,
                "credits": u.credits,
                "credits_used": u.credits_used,
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.post("/users/{user_id}/credits")
async def adjust_user_credits(
    user_id: int,
    amount: int = Query(..., description="Positive to add, negative to deduct"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Adjust user credits (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.credits += amount
    if user.credits < 0:
        user.credits = 0

    return {
        "user_id": user.id,
        "credits_adjusted": amount,
        "credits_remaining": user.credits,
    }


@router.get("/gpu")
async def get_gpu_status(
    _admin: User = Depends(require_admin),
):
    """GPU cluster status (admin only)."""
    gpu_status = await gpu_scheduler.get_gpu_status()
    return {"gpu_status": gpu_status}


@router.get("/queue")
async def get_queue_status(
    _admin: User = Depends(require_admin),
):
    """Queue status (admin only)."""
    queue_status = await gpu_scheduler.get_queue_status()
    return {"queue_status": queue_status}
