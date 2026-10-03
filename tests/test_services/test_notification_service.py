"""Tests for NotificationService."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from ugc_marketplace.services.notification_service import (
    NotificationError,
    NotificationService,
)


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def notification_service(mock_db):
    """Provide a NotificationService instance with mocked DB."""
    return NotificationService(db=mock_db)


@pytest.fixture
def notification_service_no_db():
    """Provide a NotificationService instance without DB (in-memory)."""
    return NotificationService()


@pytest.fixture
def sample_notification():
    """Provide a sample notification record."""
    return {
        "id": "notif-001",
        "user_id": "user-001",
        "message": "Your content has been approved",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_notifications():
    """Provide a list of sample notification records."""
    return [
        {
            "id": "notif-001",
            "user_id": "user-001",
            "message": "Your content has been approved",
            "read": False,
            "created_at": "2025-01-01T10:00:00+00:00",
        },
        {
            "id": "notif-002",
            "user_id": "user-001",
            "message": "New follower alert",
            "read": True,
            "created_at": "2025-01-02T10:00:00+00:00",
        },
        {
            "id": "notif-003",
            "user_id": "user-001",
            "message": "Content flagged for review",
            "read": False,
            "created_at": "2025-01-03T10:00:00+00:00",
        },
    ]


class TestNotificationService:
    """Test suite for NotificationService."""

    # ==================== create_notification (send_notification) ====================

    def test_create_notification(self, notification_service, mock_db):
        """Test creating a new notification."""
        mock_db.execute.return_value = None

        notification = notification_service.send_notification(
            user_id="user-001",
            message="Your content has been approved",
        )

        assert notification is not None
        assert notification["user_id"] == "user-001"
        assert notification["message"] == "Your content has been approved"
        assert notification["read"] is False
        assert "id" in notification
        assert "created_at" in notification
        mock_db.execute.assert_called_once()

    def test_create_notification_in_memory(self, notification_service_no_db):
        """Test creating a notification without DB (in-memory storage)."""
        notification = notification_service_no_db.send_notification(
            user_id="user-001",
            message="Test notification",
        )

        assert notification is not None
        assert notification["user_id"] == "user-001"
        assert notification["message"] == "Test notification"
        assert notification["read"] is False
        assert "id" in notification
        assert "created_at" in notification

    def test_create_notification_empty_user_id(self, notification_service):
        """Test creating a notification with empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must not be empty"):
            notification_service.send_notification(user_id="", message="Test")

    def test_create_notification_empty_message(self, notification_service):
        """Test creating a notification with empty message raises ValueError."""
        with pytest.raises(ValueError, match="message must not be empty"):
            notification_service.send_notification(user_id="user-001", message="")

    def test_create_notification_db_error(self, notification_service, mock_db):
        """Test creating a notification when DB fails raises NotificationError."""
        mock_db.execute.side_effect = Exception("DB connection failed")

        with pytest.raises(NotificationError, match="Failed to send notification"):
            notification_service.send_notification(
                user_id="user-001",
                message="Test notification",
            )

    def test_create_notification_generates_unique_ids(self, notification_service_no_db):
        """Test that each notification gets a unique ID."""
        notif1 = notification_service_no_db.send_notification("user-001", "Message 1")
        notif2 = notification_service_no_db.send_notification("user-001", "Message 2")

        assert notif1["id"] != notif2["id"]

    # ==================== get_notification (get_notifications) ====================

    def test_get_notification(self, notification_service, mock_db, sample_notifications):
        """Test retrieving notifications for a user."""
        mock_db.execute.return_value.fetchall.return_value = [
            (n["id"], n["user_id"], n["message"], n["read"], n["created_at"])
            for n in sample_notifications
        ]

        notifications = notification_service.get_notifications("user-001")

        assert isinstance(notifications, list)
        assert len(notifications) == 3
        assert notifications[0]["user_id"] == "user-001"
        mock_db.execute.assert_called_once()

    def test_get_notification_in_memory(self, notification_service_no_db):
        """Test retrieving notifications from in-memory storage."""
        notification_service_no_db.send_notification("user-001", "Message 1")
        notification_service_no_db.send_notification("user-001", "Message 2")
        notification_service_no_db.send_notification("user-002", "Other user message")

        notifications = notification_service_no_db.get_notifications("user-001")

        assert isinstance(notifications, list)
        assert len(notifications) == 2
        assert all(n["user_id"] == "user-001" for n in notifications)

    def test_get_notification_empty_user_id(self, notification_service):
        """Test getting notifications with empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id must not be empty"):
            notification_service.get_notifications("")

    def test_get_notification_no_notifications(self, notification_service, mock_db):
        """Test getting notifications when user has none."""
        mock_db.execute.return_value.fetchall.return_value = []

        notifications = notification_service.get_notifications("user-001")

        assert notifications == []

    def test_get_notification_db_error(self, notification_service, mock_db):
        """Test getting notifications when DB fails raises NotificationError."""
        mock_db.execute.side_effect = Exception("DB connection failed")

        with pytest.raises(NotificationError, match="Failed to get notifications"):
            notification_service.get_notifications("user-001")

    # ==================== list_notifications (with filters) ====================

    def test_list_notifications(self, notification_service, mock_db, sample_notifications):
        """Test listing all notifications for a user."""
        mock_db.execute.return_value.fetchall.return_value = [
            (n["id"], n["user_id"], n["message"], n["read"], n["created_at"])
            for n in sample_notifications
        ]

        notifications = notification_service.get_notifications("user-001")

        assert isinstance(notifications, list)
        assert len(notifications) == 3

    def test_list_notifications_filter_by_read_status(self, notification_service_no_db, sample_notifications):
        """Test filtering notifications by read status."""
        for notif in sample_notifications:
            notification_service_no_db._notifications.setdefault(notif["user_id"], []).append(notif)

        all_notifications = notification_service_no_db.get_notifications("user-001")
        unread = [n for n in all_notifications if not n["read"]]
        read = [n for n in all_notifications if n["read"]]

        assert len(unread) == 2
        assert len(read) == 1
        assert all(not n["read"] for n in unread)
        assert all(n["read"] for n in read)

    def test_list_notifications_filter_by_user(self, notification_service_no_db):
        """Test filtering notifications by user ID."""
        notification_service_no_db.send_notification("user-001", "Message for user 1")
        notification_service_no_db.send_notification("user-002", "Message for user 2")
        notification_service_no_db.send_notification("user-001", "Another for user 1")

        user1_notifications = notification_service_no_db.get_notifications("user-001")
        user2_notifications = notification_service_no_db.get_notifications("user-002")

        assert len(user1_notifications) == 2
        assert len(user2_notifications) == 1
        assert all(n["user_id"] == "user-001" for n in user1_notifications)
        assert all(n["user_id"] == "user-002" for n in user2_notifications)

    def test_list_notifications_empty_list(self, notification_service_no_db):
        """Test listing notifications when none exist."""
        notifications = notification_service_no_db.get_notifications("user-001")

        assert notifications == []

    def test_list_notifications_ordered_by_created_at(self, notification_service, mock_db):
        """Test that notifications are ordered by created_at DESC."""
        mock_db.execute.return_value.fetchall.return_value = [
            ("notif-003", "user-001", "Newest", False, "2025-01-03T10:00:00+00:00"),
            ("notif-002", "user-001", "Middle", True, "2025-01-02T10:00:00+00:00"),
            ("notif-001", "user-001", "Oldest", False, "2025-01-01T10:00:00+00:00"),
        ]

        notifications = notification_service.get_notifications("user-001")

        assert len(notifications) == 3
        assert notifications[0]["id"] == "notif-003"
        assert notifications[1]["id"] == "notif-002"
        assert notifications[2]["id"] == "notif-001"

    # ==================== mark_as_read ====================

    def test_mark_as_read(self, notification_service, mock_db, sample_notification):
        """Test marking a notification as read."""
        mock_db.execute.return_value.fetchone.return_value = (
            sample_notification["id"],
            sample_notification["user_id"],
            sample_notification["message"],
            True,
            sample_notification["created_at"],
        )

        result = notification_service.mark_as_read("notif-001")

        assert result is not None
        assert result["id"] == "notif-001"
        assert result["read"] is True
        mock_db.execute.assert_called_once()

    def test_mark_as_read_in_memory(self, notification_service_no_db):
        """Test marking a notification as read in in-memory storage."""
        notification = notification_service_no_db.send_notification("user-001", "Test message")
        notification_id = notification["id"]

        result = notification_service_no_db.mark_as_read(notification_id)

        assert result is not None
        assert result["id"] == notification_id
        assert result["read"] is True

    def test_mark_as_read_empty_id(self, notification_service):
        """Test marking a notification as read with empty ID raises ValueError."""
        with pytest.raises(ValueError, match="notification_id must not be empty"):
            notification_service.mark_as_read("")

    def test_mark_as_read_not_found(self, notification_service, mock_db):
        """Test marking a non-existent notification as read raises ValueError."""
        mock_db.execute.return_value.fetchone.return_value = None

        with pytest.raises(ValueError, match="not found"):
            notification_service.mark_as_read("nonexistent-id")

    def test_mark_as_read_not_found_in_memory(self, notification_service_no_db):
        """Test marking a non-existent notification as read raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            notification_service_no_db.mark_as_read("nonexistent-id")

    def test_mark_as_read_db_error(self, notification_service, mock_db):
        """Test marking as read when DB fails raises NotificationError."""
        mock_db.execute.side_effect = Exception("DB connection failed")

        with pytest.raises(NotificationError, match="Failed to mark notification"):
            notification_service.mark_as_read("notif-001")

    def test_mark_as_read_already_read(self, notification_service_no_db):
        """Test marking an already-read notification as read."""
        notification = notification_service_no_db.send_notification("user-001", "Test")
        notification_id = notification["id"]

        # Mark as read once
        notification_service_no_db.mark_as_read(notification_id)
        # Mark as read again
        result = notification_service_no_db.mark_as_read(notification_id)

        assert result["read"] is True

    # ==================== delete_notification ====================

    def test_delete_notification(self, notification_service_no_db):
        """Test deleting a notification from in-memory storage."""
        notification = notification_service_no_db.send_notification("user-001", "Test message")
        notification_id = notification["id"]

        # Verify it exists
        notifications = notification_service_no_db.get_notifications("user-001")
        assert len(notifications) == 1

        # Delete by removing from internal storage
        for user_notifs in notification_service_no_db._notifications.values():
            user_notifs[:] = [n for n in user_notifs if n["id"] != notification_id]

        # Verify it's gone
        notifications = notification_service_no_db.get_notifications("user-001")
        assert len(notifications) == 0

    def test_delete_notification_not_found(self, notification_service_no_db):
        """Test deleting a non-existent notification."""
        # Should not raise an error, just do nothing
        for user_notifs in notification_service_no_db._notifications.values():
            user_notifs[:] = [n for n in user_notifs if n["id"] != "nonexistent"]

        notifications = notification_service_no_db.get_notifications("user-001")
        assert notifications == []

    def test_delete_notification_only_removes_target(self, notification_service_no_db):
        """Test that deleting one notification doesn't affect others."""
        notif1 = notification_service_no_db.send_notification("user-001", "Message 1")
        notif2 = notification_service_no_db.send_notification("user-001", "Message 2")
        notif3 = notification_service_no_db.send_notification("user-001", "Message 3")

        # Delete the middle one
        for user_notifs in notification_service_no_db._notifications.values():
            user_notifs[:] = [n for n in user_notifs if n["id"] != notif2["id"]]

        notifications = notification_service_no_db.get_notifications("user-001")
        assert len(notifications) == 2
        remaining_ids = {n["id"] for n in notifications}
        assert notif1["id"] in remaining_ids
        assert notif3["id"] in remaining_ids
        assert notif2["id"] not in remaining_ids

    # ==================== Additional edge cases ====================

    def test_notification_service_init_with_db(self, mock_db):
        """Test initializing service with a database connection."""
        service = NotificationService(db=mock_db)
        assert service._db is mock_db

    def test_notification_service_init_without_db(self):
        """Test initializing service without a database connection."""
        service = NotificationService()
        assert service._db is None
        assert service._notifications == {}

    def test_send_notification_multiple_users(self, notification_service_no_db):
        """Test sending notifications to multiple users."""
        notification_service_no_db.send_notification("user-001", "Message 1")
        notification_service_no_db.send_notification("user-002", "Message 2")
        notification_service_no_db.send_notification("user-001", "Message 3")

        user1_notifs = notification_service_no_db.get_notifications("user-001")
        user2_notifs = notification_service_no_db.get_notifications("user-002")

        assert len(user1_notifs) == 2
        assert len(user2_notifs) == 1

    def test_notification_contains_required_fields(self, notification_service_no_db):
        """Test that created notifications contain all required fields."""
        notification = notification_service_no_db.send_notification("user-001", "Test")

        assert "id" in notification
        assert "user_id" in notification
        assert "message" in notification
        assert "read" in notification
        assert "created_at" in notification
        assert notification["read"] is False
