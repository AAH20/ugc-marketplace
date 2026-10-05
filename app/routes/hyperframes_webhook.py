"""HyperFrames webhook handler for render completion events."""
import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class WebhookData(BaseModel):
    """Webhook payload data."""

    id: str
    asset_id: str | None = None
    status: str | None = None
    progress: int | None = None
    output_url: str | None = None
    duration_seconds: int | None = None
    cost: float | None = None
    error: str | None = None
    quality: dict[str, Any] | None = None


class WebhookPayload(BaseModel):
    """Webhook payload."""

    event: str
    data: WebhookData
    timestamp: str | None = None


# In-memory store for processed webhook IDs (idempotency)
_processed_webhooks: set[str] = set()


def verify_webhook_signature(
    payload: dict[str, Any],
    signature: str,
    secret: str,
) -> bool:
    """Verify HMAC-SHA256 signature of webhook payload.

    Args:
        payload: The webhook payload dict.
        signature: The signature from X-HyperFrames-Signature header.
        secret: The webhook secret key.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature or not secret:
        return False

    body = json.dumps(payload, separators=(",", ":"))
    expected = hmac.new(
        secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()
    expected_sig = f"sha256={expected}"

    return hmac.compare_digest(signature, expected_sig)


@router.post("/hyperframes")
async def handle_hyperframes_webhook(
    request: Request,
    x_hyperframes_signature: str = Header(None),
) -> dict[str, str]:
    """Handle incoming HyperFrames webhook.

    Events:
    - render.complete: Render finished successfully
    - render.failed: Render failed

    Returns:
        {"status": "ok"} on success.

    Raises:
        HTTPException: 401 on invalid signature, 400 on malformed payload.
    """
    # Get webhook secret from app state or use default for testing
    secret = getattr(request.app.state, "hyperframes_webhook_secret", "whsec_test_secret_key")

    # Parse payload first
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Validate payload structure before signature check
    try:
        webhook = WebhookPayload(**payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed webhook payload")

    # Verify signature
    if not x_hyperframes_signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    if not verify_webhook_signature(payload, x_hyperframes_signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Idempotency check
    webhook_id = f"{webhook.event}:{webhook.data.id}"
    if webhook_id in _processed_webhooks:
        logger.info(f"Duplicate webhook ignored: {webhook_id}")
        return {"status": "ok"}

    _processed_webhooks.add(webhook_id)

    # Process event
    if webhook.event == "render.complete":
        logger.info(
            f"Render complete: {webhook.data.id} -> {webhook.data.output_url}"
        )
    elif webhook.event == "render.failed":
        logger.error(
            f"Render failed: {webhook.data.id} - {webhook.data.error}"
        )
    else:
        logger.info(f"Unknown webhook event: {webhook.event}")

    return {"status": "ok"}


def reset_processed_webhooks() -> None:
    """Clear processed webhook IDs (for testing)."""
    _processed_webhooks.clear()
