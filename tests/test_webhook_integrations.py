"""Comprehensive webhook integration tests."""
import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.routes.hyperframes_webhook import router, verify_webhook_signature, reset_processed_webhooks


@pytest.fixture
def webhook_app():
    """Create test app with webhook router."""
    app = FastAPI()
    app.include_router(router, prefix="/webhooks")
    return app


@pytest.fixture
def webhook_client(webhook_app):
    return TestClient(webhook_app)


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
    """Tests for webhook signature verification function."""

    def test_valid_signature(self, sample_webhook_payload, webhook_secret):
        """Valid signature passes verification."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)
        assert verify_webhook_signature(sample_webhook_payload, signature, webhook_secret) is True

    def test_invalid_signature(self, sample_webhook_payload, webhook_secret):
        """Invalid signature fails verification."""
        assert verify_webhook_signature(sample_webhook_payload, "sha256=invalid", webhook_secret) is False

    def test_missing_signature(self, sample_webhook_payload, webhook_secret):
        """Empty signature fails verification."""
        assert verify_webhook_signature(sample_webhook_payload, "", webhook_secret) is False

    def test_tampered_payload(self, sample_webhook_payload, webhook_secret):
        """Tampered payload fails verification."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)
        sample_webhook_payload["data"]["status"] = "failed"
        assert verify_webhook_signature(sample_webhook_payload, signature, webhook_secret) is False

    def test_wrong_secret(self, sample_webhook_payload):
        """Wrong secret fails verification."""
        signature = sign_payload(sample_webhook_payload, "wrong_secret")
        assert verify_webhook_signature(sample_webhook_payload, signature, "correct_secret") is False

    def test_signature_without_prefix(self, sample_webhook_payload, webhook_secret):
        """Signature without sha256= prefix fails."""
        body = json.dumps(sample_webhook_payload, separators=(",", ":"))
        signature = hmac.new(
            webhook_secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        assert verify_webhook_signature(sample_webhook_payload, signature, webhook_secret) is False

    def test_none_signature(self, sample_webhook_payload, webhook_secret):
        """None signature fails verification."""
        assert verify_webhook_signature(sample_webhook_payload, None, webhook_secret) is False

    def test_none_secret(self, sample_webhook_payload):
        """None secret fails verification."""
        signature = sign_payload(sample_webhook_payload, "secret")
        assert verify_webhook_signature(sample_webhook_payload, signature, None) is False


class TestWebhookEndpoint:
    """Tests for the webhook endpoint."""

    def test_render_complete_webhook(self, webhook_client, sample_webhook_payload, webhook_secret):
        """Handle render.complete webhook event."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)
        response = webhook_client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_render_failed_webhook(self, webhook_client, webhook_secret):
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
        response = webhook_client.post(
            "/webhooks/hyperframes",
            json=payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response.status_code == 200

    def test_webhook_invalid_signature(self, webhook_client, sample_webhook_payload):
        """Reject webhook with invalid signature."""
        response = webhook_client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": "sha256=invalid"},
        )
        assert response.status_code == 401

    def test_webhook_missing_signature(self, webhook_client, sample_webhook_payload):
        """Reject webhook with missing signature."""
        response = webhook_client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
        )
        assert response.status_code == 401

    def test_webhook_unknown_event(self, webhook_client, webhook_secret):
        """Handle unknown webhook event types gracefully."""
        payload = {
            "event": "render.unknown_event",
            "data": {"id": "render_123"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        signature = sign_payload(payload, webhook_secret)
        response = webhook_client.post(
            "/webhooks/hyperframes",
            json=payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response.status_code == 200

    def test_webhook_malformed_payload(self, webhook_client):
        """Reject malformed webhook payload."""
        response = webhook_client.post(
            "/webhooks/hyperframes",
            json={"invalid": "data"},
            headers={"X-HyperFrames-Signature": "sha256=abc"},
        )
        assert response.status_code == 400

    def test_webhook_invalid_json(self, webhook_client):
        """Reject invalid JSON payload."""
        response = webhook_client.post(
            "/webhooks/hyperframes",
            content="not json",
            headers={
                "X-HyperFrames-Signature": "sha256=abc",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400


class TestWebhookIdempotency:
    """Tests for webhook idempotency."""

    def setup_method(self):
        """Reset processed webhooks before each test."""
        reset_processed_webhooks()

    def test_duplicate_webhook_ignored(self, webhook_client, sample_webhook_payload, webhook_secret):
        """Duplicate webhook events are handled idempotently."""
        signature = sign_payload(sample_webhook_payload, webhook_secret)
        response1 = webhook_client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response1.status_code == 200
        response2 = webhook_client.post(
            "/webhooks/hyperframes",
            json=sample_webhook_payload,
            headers={"X-HyperFrames-Signature": signature},
        )
        assert response2.status_code == 200

    def test_different_render_ids_not_duplicate(self, webhook_client, webhook_secret):
        """Different render IDs are not duplicates."""
        payload1 = {
            "event": "render.complete",
            "data": {"id": "render_001"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        payload2 = {
            "event": "render.complete",
            "data": {"id": "render_002"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        sig1 = sign_payload(payload1, webhook_secret)
        sig2 = sign_payload(payload2, webhook_secret)
        response1 = webhook_client.post(
            "/webhooks/hyperframes",
            json=payload1,
            headers={"X-HyperFrames-Signature": sig1},
        )
        response2 = webhook_client.post(
            "/webhooks/hyperframes",
            json=payload2,
            headers={"X-HyperFrames-Signature": sig2},
        )
        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_same_id_different_event_not_duplicate(self, webhook_client, webhook_secret):
        """Same render ID with different event type is not duplicate."""
        payload1 = {
            "event": "render.complete",
            "data": {"id": "render_001"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        payload2 = {
            "event": "render.failed",
            "data": {"id": "render_001"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        sig1 = sign_payload(payload1, webhook_secret)
        sig2 = sign_payload(payload2, webhook_secret)
        response1 = webhook_client.post(
            "/webhooks/hyperframes",
            json=payload1,
            headers={"X-HyperFrames-Signature": sig1},
        )
        response2 = webhook_client.post(
            "/webhooks/hyperframes",
            json=payload2,
            headers={"X-HyperFrames-Signature": sig2},
        )
        assert response1.status_code == 200
        assert response2.status_code == 200
