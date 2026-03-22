"""
Integration Tests – Notifications Module (Custom Module 2)
===========================================================
Tests the standalone Notifications module:
creation, delivery, filtering, and handler callbacks.
"""
import pytest
from integration.code import (
    NotificationType, NotificationCategory, NotificationPriority,
    NotificationsModule,
)


class TestNotificationsModule:
    """Notifications module creates, routes, and manages notifications."""

    def test_create_basic_notification(self, notifications):
        """A notification can be created with title, message, type, category."""
        notif = notifications.create_notification(
            "Test Alert", "Something happened",
            NotificationType.INFO,
            NotificationCategory.SYSTEM
        )
        assert notif.notification_id == 1
        assert notif.title == "Test Alert"
        assert notif.read is False

    def test_notification_ids_auto_increment(self, notifications):
        """Notification IDs increment sequentially."""
        n1 = notifications.create_notification(
            "N1", "msg", NotificationType.INFO, NotificationCategory.SYSTEM
        )
        n2 = notifications.create_notification(
            "N2", "msg", NotificationType.INFO, NotificationCategory.SYSTEM
        )
        assert n2.notification_id == n1.notification_id + 1

    def test_mark_as_read(self, notifications):
        """mark_as_read flips the read flag and records timestamp."""
        notif = notifications.create_notification(
            "Unread", "msg", NotificationType.INFO, NotificationCategory.SYSTEM
        )
        assert notif.read is False
        notifications.mark_as_read(notif.notification_id)
        assert notif.read is True
        assert notif.read_at is not None

    def test_handler_callback_is_called(self, notifications):
        """Registered handlers are called when a notification is created."""
        received = []

        def handler(n):
            received.append(n)

        notifications.register_handler(handler)
        notifications.create_notification(
            "CB Test", "message", NotificationType.INFO, NotificationCategory.SYSTEM
        )
        assert len(received) == 1

    def test_unregister_handler_stops_callbacks(self, notifications):
        """Unregistered handlers are not called."""
        received = []

        def handler(n):
            received.append(n)

        notifications.register_handler(handler)
        notifications.unregister_handler(handler)
        notifications.create_notification(
            "Silent", "msg", NotificationType.INFO, NotificationCategory.SYSTEM
        )
        assert len(received) == 0

    def test_broadcast_reaches_all_members(self, notifications):
        """A broadcast notification (no target_member_id) reaches all members."""
        notifications.create_notification(
            "Broadcast", "Everyone sees this",
            NotificationType.INFO, NotificationCategory.RACE
        )
        m1_notifs = notifications.get_notifications_for_member(1)
        m2_notifs = notifications.get_notifications_for_member(2)
        assert len(m1_notifs) == 1
        assert len(m2_notifs) == 1

    def test_targeted_notification_only_for_recipient(self, notifications):
        """A targeted notification only appears for the specified member."""
        notifications.create_notification(
            "Private", "Only for member 1",
            NotificationType.INFO, NotificationCategory.CREW,
            target_member_id=1
        )
        m1_notifs = notifications.get_notifications_for_member(1)
        m2_notifs = notifications.get_notifications_for_member(2)
        assert len(m1_notifs) == 1
        assert len(m2_notifs) == 0

    def test_convenience_race_starting_notification(self, notifications):
        """notify_race_starting creates a RACE category HIGH priority notification."""
        notif = notifications.notify_race_starting(race_id=5, race_name="Final")
        assert "Final" in notif.message
        assert notif.category == NotificationCategory.RACE
        assert notif.priority == NotificationPriority.HIGH

    def test_convenience_race_result_win(self, notifications):
        """notify_race_result for position 1 uses SUCCESS type and 'Victory' title."""
        notif = notifications.notify_race_result(
            race_id=1, position=1, member_id=10, earnings=5_000.0
        )
        assert notif.notification_type == NotificationType.SUCCESS
        assert "Victory" in notif.title

    def test_convenience_low_funds_notification(self, notifications):
        """notify_low_funds creates an URGENT FINANCIAL WARNING."""
        notif = notifications.notify_low_funds(balance=500.0, threshold=1_000.0)
        assert notif.priority == NotificationPriority.URGENT
        assert notif.category == NotificationCategory.FINANCIAL

    def test_unread_count(self, notifications):
        """get_unread_count returns the number of unread notifications."""
        notifications.create_notification(
            "N1", "msg", NotificationType.INFO,
            NotificationCategory.SYSTEM, target_member_id=3
        )
        notifications.create_notification(
            "N2", "msg", NotificationType.INFO,
            NotificationCategory.SYSTEM, target_member_id=3
        )
        assert notifications.get_unread_count(3) == 2
        notifications.mark_all_read(3)
        assert notifications.get_unread_count(3) == 0

    def test_delete_notification(self, notifications):
        """Deleted notifications are no longer retrievable."""
        notif = notifications.create_notification(
            "Delete Me", "msg", NotificationType.INFO, NotificationCategory.SYSTEM
        )
        nid = notif.notification_id
        assert notifications.delete_notification(nid) is True
        assert notifications.get_notification(nid) is None
