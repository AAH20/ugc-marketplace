"""
Comprehensive API tests for the Notifications endpoints.

Tests cover:
- GET    /api/v1/notifications          — paginated list with filtering
- POST   /api/v1/notifications          — create a notification
- GET    /api/v1/notifications/{id}     — retrieve a single notification
- PUT    /api/v1/notifications/{id}     — update read status
- DELETE /api/v1/notifications/{id}     — delete a notification
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Return a TestClient bound to the FastAPI application."""
    from ugc_marketplace.main import app  # type: ignore
    return TestClient(app)


@pytest.fixture
def sample_notification_payload():
    """Return a valid payload for creating a notification."""
    return {
        "user_id": "user-101",
        "title": "Test Notification",
        "message": "This is a test notification message.",
        "type": "system_alert",
        "priority": "normal",
        "link": "/test/resource",
        "metadata": {"key": "value"},
    }


@pytest.fixture
def created_notification(client, sample_notification_payload):
    """Create a notification and return the response JSON."""
    response = client.post("/api/v1/notifications", json=sample_notification_payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def reset_notifications():
    """Reset the mock notifications store to its initial state before each test."""
    from ugc_marketplace.api.notifications import MOCK_NOTIFICATIONS
    original = [n.copy() for n in MOCK_NOTIFICATIONS]
    yield
    MOCK_NOTIFICATIONS.clear()
    MOCK_NOTIFICATIONS.extend(original)


# ---------------------------------------------------------------------------
# GET /api/v1/notifications — List with pagination
# ---------------------------------------------------------------------------

class TestListNotifications:
    """Tests for the GET /api/v1/notifications endpoint."""

    def test_list_notifications_success(self, client, reset_notifications):
        """GET /api/v1/notifications returns 200 with paginated data."""
        response = client.get("/api/v1/notifications")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_next" in data
        assert "has_prev" in data
        assert isinstance(data["data"], list)
        assert data["total"] == 8
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_notifications_default_pagination(self, client, reset_notifications):
        """Default pagination returns all 8 mock notifications on one page."""
        response = client.get("/api/v1/notifications")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 8
        assert data["has_next"] is False
        assert data["has_prev"] is False

    def test_list_notifications_custom_page_size(self, client, reset_notifications):
        """GET /api/v1/notifications?page_size=3 returns at most 3 items."""
        response = client.get("/api/v1/notifications", params={"page_size": 3})

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["total"] == 8
        assert data["page_size"] == 3
        assert data["has_next"] is True
        assert data["has_prev"] is False

    def test_list_notifications_page_2(self, client, reset_notifications):
        """GET /api/v1/notifications?page=2&page_size=3 returns the second page."""
        response = client.get(
            "/api/v1/notifications",
            params={"page": 2, "page_size": 3},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["page"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is True

    def test_list_notifications_last_page(self, client, reset_notifications):
        """Last page has has_next=False."""
        response = client.get(
            "/api/v1/notifications",
            params={"page": 3, "page_size": 3},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2  # 8 total, 3+3+2
        assert data["has_next"] is False
        assert data["has_prev"] is True

    def test_list_notifications_empty_page(self, client, reset_notifications):
        """Requesting a page beyond available data returns empty list."""
        response = client.get(
            "/api/v1/notifications",
            params={"page": 100, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0
        assert data["total"] == 8
        assert data["has_next"] is False
        assert data["has_prev"] is True

    def test_list_notifications_filter_unread(self, client, reset_notifications):
        """GET /api/v1/notifications?is_read=false returns only unread notifications."""
        response = client.get("/api/v1/notifications", params={"is_read": False})

        assert response.status_code == 200
        data = response.json()
        # Mock data has 6 unread notifications (n-001, n-003, n-004, n-006, n-007, n-008)
        assert data["total"] == 6
        for item in data["data"]:
            assert item["is_read"] is False

    def test_list_notifications_filter_read(self, client, reset_notifications):
        """GET /api/v1/notifications?is_read=true returns only read notifications."""
        response = client.get("/api/v1/notifications", params={"is_read": True})

        assert response.status_code == 200
        data = response.json()
        # Mock data has 2 read notifications (n-002, n-005)
        assert data["total"] == 2
        for item in data["data"]:
            assert item["is_read"] is True

    def test_list_notifications_filter_by_user_id(self, client, reset_notifications):
        """GET /api/v1/notifications?user_id=user-101 filters by user."""
        response = client.get(
            "/api/v1/notifications",
            params={"user_id": "user-101"},
        )

        assert response.status_code == 200
        data = response.json()
        # Mock data has 4 notifications for user-101 (n-001, n-002, n-004, n-007)
        assert data["total"] == 4
        for item in data["data"]:
            assert item["user_id"] == "user-101"

    def test_list_notifications_filter_combined(self, client, reset_notifications):
        """Combining is_read and user_id filters works correctly."""
        response = client.get(
            "/api/v1/notifications",
            params={"user_id": "user-101", "is_read": False},
        )

        assert response.status_code == 200
        data = response.json()
        # user-101 unread: n-001, n-004, n-007
        assert data["total"] == 3
        for item in data["data"]:
            assert item["user_id"] == "user-101"
            assert item["is_read"] is False

    def test_list_notifications_invalid_page(self, client, reset_notifications):
        """GET /api/v1/notifications?page=0 returns 422 (page must be >= 1)."""
        response = client.get("/api/v1/notifications", params={"page": 0})

        assert response.status_code == 422

    def test_list_notifications_invalid_page_size(self, client, reset_notifications):
        """GET /api/v1/notifications?page_size=0 returns 422."""
        response = client.get("/api/v1/notifications", params={"page_size": 0})

        assert response.status_code == 422

    def test_list_notifications_page_size_too_large(self, client, reset_notifications):
        """GET /api/v1/notifications?page_size=101 returns 422 (max 100)."""
        response = client.get("/api/v1/notifications", params={"page_size": 101})

        assert response.status_code == 422

    def test_list_notifications_response_structure(self, client, reset_notifications):
        """Each notification in the list has the expected keys."""
        response = client.get("/api/v1/notifications")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0

        item = data["data"][0]
        expected_keys = {
            "id",
            "user_id",
            "title",
            "message",
            "type",
            "priority",
            "link",
            "metadata",
            "is_read",
            "created_at",
            "read_at",
        }
        assert expected_keys.issubset(item.keys())

    def test_list_notifications_response_content_type(self, client, reset_notifications):
        """Response Content-Type is application/json."""
        response = client.get("/api/v1/notifications")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# POST /api/v1/notifications — Create
# ---------------------------------------------------------------------------

class TestCreateNotification:
    """Tests for the POST /api/v1/notifications endpoint."""

    def test_create_notification_success(self, client, sample_notification_payload, reset_notifications):
        """POST /api/v1/notifications with valid payload returns 201."""
        response = client.post("/api/v1/notifications", json=sample_notification_payload)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["user_id"] == sample_notification_payload["user_id"]
        assert data["title"] == sample_notification_payload["title"]
        assert data["message"] == sample_notification_payload["message"]
        assert data["type"] == sample_notification_payload["type"]
        assert data["priority"] == sample_notification_payload["priority"]
        assert data["link"] == sample_notification_payload["link"]
        assert data["metadata"] == sample_notification_payload["metadata"]
        assert data["is_read"] is False
        assert "created_at" in data
        assert data["read_at"] is None

    def test_create_notification_minimal_payload(self, client, reset_notifications):
        """POST with only required fields succeeds."""
        payload = {
            "user_id": "user-200",
            "title": "Minimal Notification",
            "message": "Just the basics.",
            "type": "message_received",
        }
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "user-200"
        assert data["priority"] == "normal"  # default
        assert data["link"] is None
        assert data["metadata"] is None
        assert data["is_read"] is False

    def test_create_notification_all_types(self, client, reset_notifications):
        """POST succeeds for every valid notification type."""
        types = [
            "order_placed",
            "order_shipped",
            "order_delivered",
            "payment_received",
            "review_received",
            "message_received",
            "system_alert",
            "promotion",
        ]
        for notif_type in types:
            payload = {
                "user_id": "user-300",
                "title": f"Type test: {notif_type}",
                "message": "Testing type.",
                "type": notif_type,
            }
            response = client.post("/api/v1/notifications", json=payload)
            assert response.status_code == 201, f"Failed for type {notif_type}"
            assert response.json()["type"] == notif_type

    def test_create_notification_all_priorities(self, client, reset_notifications):
        """POST succeeds for every valid priority level."""
        priorities = ["low", "normal", "high", "urgent"]
        for priority in priorities:
            payload = {
                "user_id": "user-300",
                "title": f"Priority test: {priority}",
                "message": "Testing priority.",
                "type": "system_alert",
                "priority": priority,
            }
            response = client.post("/api/v1/notifications", json=payload)
            assert response.status_code == 201, f"Failed for priority {priority}"
            assert response.json()["priority"] == priority

    def test_create_notification_missing_user_id(self, client, sample_notification_payload, reset_notifications):
        """POST without user_id returns 422."""
        payload = {k: v for k, v in sample_notification_payload.items() if k != "user_id"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_missing_title(self, client, sample_notification_payload, reset_notifications):
        """POST without title returns 422."""
        payload = {k: v for k, v in sample_notification_payload.items() if k != "title"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_missing_message(self, client, sample_notification_payload, reset_notifications):
        """POST without message returns 422."""
        payload = {k: v for k, v in sample_notification_payload.items() if k != "message"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_missing_type(self, client, sample_notification_payload, reset_notifications):
        """POST without type returns 422."""
        payload = {k: v for k, v in sample_notification_payload.items() if k != "type"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_empty_title(self, client, sample_notification_payload, reset_notifications):
        """POST with empty title returns 422."""
        payload = {**sample_notification_payload, "title": ""}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_empty_message(self, client, sample_notification_payload, reset_notifications):
        """POST with empty message returns 422."""
        payload = {**sample_notification_payload, "message": ""}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_title_too_long(self, client, sample_notification_payload, reset_notifications):
        """POST with title exceeding 200 chars returns 422."""
        payload = {**sample_notification_payload, "title": "x" * 201}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_message_too_long(self, client, sample_notification_payload, reset_notifications):
        """POST with message exceeding 2000 chars returns 422."""
        payload = {**sample_notification_payload, "message": "x" * 2001}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_invalid_type(self, client, sample_notification_payload, reset_notifications):
        """POST with invalid notification type returns 422."""
        payload = {**sample_notification_payload, "type": "invalid_type"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_invalid_priority(self, client, sample_notification_payload, reset_notifications):
        """POST with invalid priority returns 422."""
        payload = {**sample_notification_payload, "priority": "super_urgent"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_invalid_link(self, client, sample_notification_payload, reset_notifications):
        """POST with invalid link format returns 422."""
        payload = {**sample_notification_payload, "link": "not-a-valid-url"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 422

    def test_create_notification_valid_relative_link(self, client, sample_notification_payload, reset_notifications):
        """POST with a valid relative link succeeds."""
        payload = {**sample_notification_payload, "link": "/dashboard"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 201
        assert response.json()["link"] == "/dashboard"

    def test_create_notification_valid_https_link(self, client, sample_notification_payload, reset_notifications):
        """POST with a valid https link succeeds."""
        payload = {**sample_notification_payload, "link": "https://example.com/page"}
        response = client.post("/api/v1/notifications", json=payload)

        assert response.status_code == 201
        assert response.json()["link"] == "https://example.com/page"

    def test_create_notification_empty_body(self, client, reset_notifications):
        """POST with empty JSON body returns 422."""
        response = client.post("/api/v1/notifications", json={})

        assert response.status_code == 422

    def test_create_notification_no_body(self, client, reset_notifications):
        """POST with no body returns 422."""
        response = client.post("/api/v1/notifications")

        assert response.status_code == 422

    def test_create_notification_returns_unique_ids(self, client, sample_notification_payload, reset_notifications):
        """Each POST returns a distinct notification ID."""
        resp1 = client.post("/api/v1/notifications", json=sample_notification_payload)
        resp2 = client.post("/api/v1/notifications", json=sample_notification_payload)

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_create_notification_appears_in_list(self, client, sample_notification_payload, reset_notifications):
        """A newly created notification appears in the list endpoint."""
        create_resp = client.post("/api/v1/notifications", json=sample_notification_payload)
        assert create_resp.status_code == 201
        new_id = create_resp.json()["id"]

        list_resp = client.get("/api/v1/notifications")
        assert list_resp.status_code == 200
        ids = [n["id"] for n in list_resp.json()["data"]]
        assert new_id in ids

    def test_create_notification_response_content_type(self, client, sample_notification_payload, reset_notifications):
        """Response Content-Type is application/json."""
        response = client.post("/api/v1/notifications", json=sample_notification_payload)

        assert response.status_code == 201
        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# GET /api/v1/notifications/{id} — Get single
# ---------------------------------------------------------------------------

class TestGetNotification:
    """Tests for the GET /api/v1/notifications/{id} endpoint."""

    def test_get_notification_success(self, client, created_notification, reset_notifications):
        """GET /api/v1/notifications/{id} returns the matching notification."""
        notification_id = created_notification["id"]
        response = client.get(f"/api/v1/notifications/{notification_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == notification_id
        assert data["user_id"] == created_notification["user_id"]
        assert data["title"] == created_notification["title"]
        assert data["message"] == created_notification["message"]
        assert data["type"] == created_notification["type"]
        assert data["priority"] == created_notification["priority"]
        assert data["is_read"] == created_notification["is_read"]

    def test_get_notification_not_found(self, client, reset_notifications):
        """GET /api/v1/notifications/{id} with non-existent ID returns 404."""
        response = client.get("/api/v1/notifications/nonexistent-id-99999")

        assert response.status_code == 404

    def test_get_notification_from_mock_data(self, client, reset_notifications):
        """GET retrieves a known mock notification by ID."""
        response = client.get("/api/v1/notifications/n-001")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "n-001"
        assert data["user_id"] == "user-101"
        assert data["title"] == "Order #UGC-2024-0892 Shipped"
        assert data["type"] == "order_shipped"
        assert data["is_read"] is False

    def test_get_notification_response_structure(self, client, created_notification, reset_notifications):
        """Response contains all expected notification fields."""
        notification_id = created_notification["id"]
        response = client.get(f"/api/v1/notifications/{notification_id}")

        assert response.status_code == 200
        data = response.json()
        expected_keys = {
            "id",
            "user_id",
            "title",
            "message",
            "type",
            "priority",
            "link",
            "metadata",
            "is_read",
            "created_at",
            "read_at",
        }
        assert expected_keys.issubset(data.keys())

    def test_get_notification_response_content_type(self, client, created_notification, reset_notifications):
        """Response Content-Type is application/json."""
        notification_id = created_notification["id"]
        response = client.get(f"/api/v1/notifications/{notification_id}")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_notification_does_not_return_others(self, client, created_notification, reset_notifications):
        """GET /api/v1/notifications/{id} only returns the requested notification."""
        notification_id = created_notification["id"]
        response = client.get(f"/api/v1/notifications/{notification_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == notification_id
        # Ensure it's a single object, not a list
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# PUT /api/v1/notifications/{id} — Update (mark as read)
# ---------------------------------------------------------------------------

class TestMarkAsRead:
    """Tests for the PUT /api/v1/notifications/{id} endpoint."""

    def test_mark_as_read_success(self, client, created_notification, reset_notifications):
        """PUT /api/v1/notifications/{id}?is_read=true marks the notification as read."""
        notification_id = created_notification["id"]
        response = client.put(
            f"/api/v1/notifications/{notification_id}",
            params={"is_read": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == notification_id
        assert data["is_read"] is True
        assert data["read_at"] is not None

    def test_mark_as_unread_success(self, client, reset_notifications):
        """PUT /api/v1/notifications/{id}?is_read=false marks the notification as unread."""
        # n-002 is already read in mock data
        response = client.put(
            "/api/v1/notifications/n-002",
            params={"is_read": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "n-002"
        assert data["is_read"] is False
        assert data["read_at"] is None

    def test_mark_as_read_not_found(self, client, reset_notifications):
        """PUT on a non-existent notification returns 404."""
        response = client.put(
            "/api/v1/notifications/nonexistent-id-99999",
            params={"is_read": True},
        )

        assert response.status_code == 404

    def test_mark_as_read_missing_is_read_param(self, client, created_notification, reset_notifications):
        """PUT without is_read query parameter returns 422."""
        notification_id = created_notification["id"]
        response = client.put(f"/api/v1/notifications/{notification_id}")

        assert response.status_code == 422

    def test_mark_as_read_persists_in_list(self, client, created_notification, reset_notifications):
        """After marking as read, the list endpoint reflects the change."""
        notification_id = created_notification["id"]

        # Mark as read
        client.put(
            f"/api/v1/notifications/{notification_id}",
            params={"is_read": True},
        )

        # Check list
        list_resp = client.get(
            "/api/v1/notifications",
            params={"is_read": True},
        )
        assert list_resp.status_code == 200
        ids = [n["id"] for n in list_resp.json()["data"]]
        assert notification_id in ids

    def test_mark_as_read_updates_read_at(self, client, created_notification, reset_notifications):
        """Marking as read sets read_at to a non-null timestamp."""
        notification_id = created_notification["id"]
        response = client.put(
            f"/api/v1/notifications/{notification_id}",
            params={"is_read": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["read_at"] is not None
        # Should be a valid ISO format string
        assert "T" in data["read_at"]

    def test_mark_as_unread_clears_read_at(self, client, reset_notifications):
        """Marking as unread clears read_at."""
        # n-002 is already read
        response = client.put(
            "/api/v1/notifications/n-002",
            params={"is_read": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["read_at"] is None

    def test_mark_as_read_response_content_type(self, client, created_notification, reset_notifications):
        """Response Content-Type is application/json."""
        notification_id = created_notification["id"]
        response = client.put(
            f"/api/v1/notifications/{notification_id}",
            params={"is_read": True},
        )

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_mark_as_read_idempotent(self, client, created_notification, reset_notifications):
        """Marking an already-read notification as read again succeeds."""
        notification_id = created_notification["id"]

        # Mark as read twice
        resp1 = client.put(
            f"/api/v1/notifications/{notification_id}",
            params={"is_read": True},
        )
        resp2 = client.put(
            f"/api/v1/notifications/{notification_id}",
            params={"is_read": True},
        )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp2.json()["is_read"] is True


# ---------------------------------------------------------------------------
# DELETE /api/v1/notifications/{id} — Delete
# ---------------------------------------------------------------------------

class TestDeleteNotification:
    """Tests for the DELETE /api/v1/notifications/{id} endpoint."""

    def test_delete_notification_success(self, client, created_notification, reset_notifications):
        """DELETE /api/v1/notifications/{id} returns 204 No Content."""
        notification_id = created_notification["id"]
        response = client.delete(f"/api/v1/notifications/{notification_id}")

        assert response.status_code == 204

    def test_delete_notification_removes_from_list(self, client, created_notification, reset_notifications):
        """After deletion, the notification no longer appears in the list."""
        notification_id = created_notification["id"]

        # Delete
        client.delete(f"/api/v1/notifications/{notification_id}")

        # Verify it's gone from the list
        list_resp = client.get("/api/v1/notifications")
        ids = [n["id"] for n in list_resp.json()["data"]]
        assert notification_id not in ids

    def test_delete_notification_not_found(self, client, reset_notifications):
        """DELETE on a non-existent notification returns 404."""
        response = client.delete("/api/v1/notifications/nonexistent-id-99999")

        assert response.status_code == 404

    def test_delete_notification_get_after_delete(self, client, created_notification, reset_notifications):
        """GET after DELETE returns 404."""
        notification_id = created_notification["id"]

        # Delete
        client.delete(f"/api/v1/notifications/{notification_id}")

        # Try to get
        get_resp = client.get(f"/api/v1/notifications/{notification_id}")
        assert get_resp.status_code == 404

    def test_delete_notification_from_mock_data(self, client, reset_notifications):
        """Deleting a known mock notification succeeds."""
        response = client.delete("/api/v1/notifications/n-001")

        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get("/api/v1/notifications/n-001")
        assert get_resp.status_code == 404

    def test_delete_notification_response_body_empty(self, client, created_notification, reset_notifications):
        """DELETE response has no body (204 No Content)."""
        notification_id = created_notification["id"]
        response = client.delete(f"/api/v1/notifications/{notification_id}")

        assert response.status_code == 204
        assert response.content == b""

    def test_delete_notification_total_decreases(self, client, reset_notifications):
        """After deletion, the total count in list decreases."""
        # Get initial total
        initial_resp = client.get("/api/v1/notifications")
        initial_total = initial_resp.json()["total"]

        # Delete one
        client.delete("/api/v1/notifications/n-001")

        # Check new total
        new_resp = client.get("/api/v1/notifications")
        new_total = new_resp.json()["total"]
        assert new_total == initial_total - 1

    def test_delete_notification_only_removes_target(self, client, reset_notifications):
        """Deleting one notification does not affect others."""
        # Delete n-001
        client.delete("/api/v1/notifications/n-001")

        # n-002 should still exist
        resp = client.get("/api/v1/notifications/n-002")
        assert resp.status_code == 200
        assert resp.json()["id"] == "n-002"
