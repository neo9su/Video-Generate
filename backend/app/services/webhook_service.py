"""Webhook notification service — sends events to registered webhooks."""
import hashlib
import hmac
import json
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.webhook import Webhook


class WebhookService:
    """Dispatches webhook events to all active webhooks matching the event type."""

    async def send_webhook(
        self,
        user_id: int,
        event: str,
        payload: dict,
        db: AsyncSession,
    ):
        """Send webhook notification for all active webhooks matching event."""
        result = await db.execute(
            select(Webhook).where(
                Webhook.user_id == user_id,
                Webhook.is_active == True,
            )
        )
        webhooks = result.scalars().all()

        for webhook in webhooks:
            if webhook.events and event not in webhook.events:
                continue

            body = json.dumps({
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload,
            }).encode()

            headers = {"Content-Type": "application/json"}
            if webhook.secret:
                signature = self._compute_signature(body, webhook.secret)
                headers["X-Webhook-Signature"] = signature

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        webhook.url,
                        content=body,
                        headers=headers,
                    )
            except Exception:
                # TODO: Add retry logic / mark webhook as failed
                pass

    def verify_signature(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify HMAC-SHA256 webhook signature."""
        expected = self._compute_signature(payload, secret)
        return hmac.compare_digest(expected, signature)

    def _compute_signature(self, payload: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature for a payload."""
        return hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()


# Singleton
webhook_service = WebhookService()
