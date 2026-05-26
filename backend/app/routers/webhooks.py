"""Webhook registration and management routes."""
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..auth_deps import get_current_user
from ..models.user import User
from ..models.webhook import Webhook
from ..services.webhook_service import webhook_service

router = APIRouter(tags=["webhooks"])


@router.post("")
async def register_webhook(
    url: str = Body(..., description="Webhook callback URL"),
    events: list[str] = Body(..., description="Event types to subscribe to"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new webhook."""
    secret = secrets.token_hex(32)

    webhook = Webhook(
        user_id=current_user.id,
        url=url,
        events=events,
        secret=secret,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)

    return {
        "id": webhook.id,
        "url": webhook.url,
        "events": webhook.events,
        "secret": secret,  # Only returned once at creation
        "is_active": webhook.is_active,
        "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
    }


@router.get("")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all webhooks for the current user."""
    result = await db.execute(
        select(Webhook).where(Webhook.user_id == current_user.id)
    )
    webhooks = result.scalars().all()
    return {
        "total": len(webhooks),
        "webhooks": [
            {
                "id": w.id,
                "url": w.url,
                "events": w.events,
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in webhooks
        ],
    }


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: int,
    url: str = Body(None, description="Webhook callback URL"),
    events: list[str] = Body(None, description="Event types to subscribe to"),
    is_active: bool = Body(None, description="Whether webhook is active"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing webhook."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.user_id == current_user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if url is not None:
        webhook.url = url
    if events is not None:
        webhook.events = events
    if is_active is not None:
        webhook.is_active = is_active

    return {
        "id": webhook.id,
        "url": webhook.url,
        "events": webhook.events,
        "is_active": webhook.is_active,
    }


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a webhook."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.user_id == current_user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.delete(webhook)
    return {"message": "Webhook deleted", "id": webhook_id}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test event to a webhook."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.user_id == current_user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "test": True,
        "message": "This is a test webhook event",
        "timestamp": datetime.utcnow().isoformat(),
    }

    await webhook_service.send_webhook(
        user_id=current_user.id,
        event="test",
        payload=test_payload,
        db=db,
    )

    return {"message": "Test event sent", "webhook_id": webhook_id, "url": webhook.url}
