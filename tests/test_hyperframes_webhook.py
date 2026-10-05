"""Integration tests for HyperFrames webhook handler."""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.routes.hyperframes_webhook import router, verify_webhook_signature


@pytest.fixture
def test_app():
    """Create a test FastAPI app with the webhook router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/webhooks")
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.fixture
def webhook_secret():
    return "whsec_test_secret_key"


@pytest.fixture
def sample_webhook_payload():
    return {
        "event": "render.complete",
        "data": {
            "id": "render_abc123",
            "asset_id": "asset_xyz789",
            "status": "complete",
            "progress": 100,
            "output_url": "https://cdn.hyperframes.io/renders/render_abc123.mp4",
            "duration_seconds": 120,
            "cost": 0.20,
            "quality": {"resolution": "1080p", "fps": 30},
        },
        "timestamp": "2024-01-01T00:00:00Z",
    }


def sign_payload(payload: dict, secret: str) -> str:
    """Create HMAC signature for webhook payload."""
    body = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(
        secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


class TestWebhookSignatureVerification:
    """Tests for webhook signature verification."""

    def test_verify_valid_signature(self, sample_webhook_payload, webhook_secret):
        """Valid signature passes verification."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)
        assert verify_webhook_signature(sample_webhook_payload, signature, webhook_secret) is True

    def test_verify_invalid_signature(self, sample_webhook_payload, webhook_secret):
        """Invalid signature fails verification."""
        assert verify_webhook_signature(sample_webhook_payload, "sha256=invalid", webhook_secret) is False

    def test_verify_missing_signature(self, sample_webhook_payload, webhook_secret):
        """Missing signature fails verification."""
        assert verify_webhook_signature(sample_webhook_payload, "", webhook_secret) is False

    def test_verify_tampered_payload(self, sample_webhook_payload, webhook_secret):
        """Tampered payload fails verification."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)
        sample_webhook_payload["data"]["status"] = "failed"
        assert verify_webhook_signature(sample_webhook_payload, signature, webhook_secret) is False


class TestWebhookEndpoint:
    """Tests for the webhook endpoint."""

    def test_render_complete_webhook(self, client, sample_webhook_payload, webhook_secret):
        """Handle render.complete webhook event."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)
        response = client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_render_failed_webhook(self, client, webhook_secret):
        """Handle render.failed webhook event."""
        payload = {
            "event": "render.failed",
            "data": {
                "id": "render_failed_001",
                "asset_id": "asset_xyz789",
                "status": "failed",
                "error": "Out of memory",
            },
            "timestamp": "2024-01-01T00:00:00Z",
        }
        signature = sign_payload(payload, webhook_secret)
        response = client.post(
            "/webhooks/hyperframes",
            json=payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response.status_code == 200

    def test_webhook_invalid_signature(self, client, sample_webhook_payload):
        """Reject webhook with invalid signature."""
        response = client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": "sha256=invalid"},
        )
        assert response.status_code == 401

    def test_webhook_missing_signature(self, client, sample_webhook_payload):
        """Reject webhook with missing signature."""
        response = client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
        )
        assert response.status_code == 401

    def test_webhook_unknown_event(self, client, webhook_secret):
        """Handle unknown webhook event types gracefully."""
        payload = {
            "event": "render.unknown_event",
            "data": {"id": "render_123"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        signature = sign_payload(payload, webhook_secret)
        response = client.post(
            "/webhooks/hyperframes",
            json=payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response.status_code == 200

    def test_webhook_malformed_payload(self, client, webhook_secret):
        """Reject malformed webhook payload."""
        payload = {"invalid": "data"}
        signature = sign_payload(payload, webhook_secret)
        response = client.post(
            "/webhooks/hyperframes",
            json=payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response.status_code == 400


class TestWebhookIdempotency:
    """Tests for webhook idempotency."""

    def test_duplicate_webhook_ignored(self, client, sample_webhook_payload, webhook_secret):
        """Duplicate webhook events are handled idempotently."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)

        response1 = client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response1.status_code == 200

        response2 = client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response2.status_code == 200
