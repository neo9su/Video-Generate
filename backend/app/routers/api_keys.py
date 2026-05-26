"""API Key management routes."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..auth_deps import get_current_user
from ..models.user import User
from ..models.api_key import ApiKey

router = APIRouter(tags=["api-keys"])


class CreateApiKeyRequest(BaseModel):
    name: str


@router.post("")
async def create_api_key(
    req: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new API key."""
    key_value = f"vg_{secrets.token_hex(24)}"

    api_key = ApiKey(
        user_id=current_user.id,
        key=key_value,
        name=req.name,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": key_value,  # Only returned once at creation
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
    }


@router.get("")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the current user."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == current_user.id,
            ApiKey.is_active == True,
        )
    )
    keys = result.scalars().all()
    return {
        "total": len(keys),
        "api_keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_preview": k.key[:12] + "...",
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ],
    }


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (deactivate) an API key."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    return {"message": "API key revoked", "id": key_id}
