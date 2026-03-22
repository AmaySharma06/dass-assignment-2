"""
Notifications Module (Custom Module 2)
======================================
Handles system notifications and alerts for crew activities.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
from datetime import datetime


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    SUCCESS = "success"
    ERROR = "error"


class NotificationCategory(Enum):
    """Categories of notifications."""
    RACE = "race"
    MISSION = "mission"
    INVENTORY = "inventory"
    CREW = "crew"
    FINANCIAL = "financial"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"


class NotificationPriority(Enum):
    """Priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Notification:
    """Represents a notification."""
    notification_id: int
    title: str
    message: str
    notification_type: NotificationType
    category: NotificationCategory
    priority: NotificationPriority = NotificationPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    read: bool = False
    read_at: Optional[datetime] = None
    target_member_id: Optional[int] = None  # None = broadcast to all
    metadata: Dict = field(default_factory=dict)


@dataclass
class NotificationPreference:
    """User preferences for notifications."""
    member_id: int
    enabled_categories: List[NotificationCategory] = field(
        default_factory=lambda: list(NotificationCategory)
    )
    min_priority: NotificationPriority = NotificationPriority.LOW
    email_enabled: bool = False
    email_address: Optional[str] = None


# Type alias for notification handlers
NotificationHandler = Callable[[Notification], None]


class NotificationsModule:
    """
    Manages notifications for the system.

    This is a standalone module that other modules can use
    to send notifications.
    """

    def __init__(self):
        self._notifications: Dict[int, Notification] = {}
        self._next_id: int = 1
        self._preferences: Dict[int, NotificationPreference] = {}
        self._handlers: List[NotificationHandler] = []
        self._broadcast_notifications: List[int] = []

    def register_handler(self, handler: NotificationHandler) -> None:
        """Register a callback for new notifications."""
        self._handlers.append(handler)

    def unregister_handler(self, handler: NotificationHandler) -> None:
        """Remove a notification handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def _notify_handlers(self, notification: Notification) -> None:
        """Call all registered handlers."""
        for handler in self._handlers:
            try:
                handler(notification)
            except Exception:
                pass  # Don't let handler errors break notifications

    def create_notification(self, title: str, message: str,
                            notification_type: NotificationType,
                            category: NotificationCategory,
                            priority: NotificationPriority = NotificationPriority.MEDIUM,
                            target_member_id: Optional[int] = None,
                            metadata: Optional[Dict] = None) -> Notification:
        """
        Create and send a notification.

        Args:
            title: Short title
            message: Full message
            notification_type: Type (info, warning, etc.)
            category: Category for filtering
            priority: Priority level
            target_member_id: Specific recipient, or None for broadcast
            metadata: Additional data

        Returns:
            The created notification
        """
        notification = Notification(
            notification_id=self._next_id,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            priority=priority,
            target_member_id=target_member_id,
            metadata=metadata or {}
        )

        self._notifications[self._next_id] = notification

        if target_member_id is None:
            self._broadcast_notifications.append(self._next_id)

        self._next_id += 1
        self._notify_handlers(notification)

        return notification

    # Convenience methods for common notification types

    def notify_race_starting(self, race_id: int, race_name: str,
                             member_id: Optional[int] = None) -> Notification:
        """Notify that a race is about to start."""
        return self.create_notification(
            title="Race Starting Soon",
            message=f"Race '{race_name}' is about to begin!",
            notification_type=NotificationType.INFO,
            category=NotificationCategory.RACE,
            priority=NotificationPriority.HIGH,
            target_member_id=member_id,
            metadata={"race_id": race_id}
        )

    def notify_race_result(self, race_id: int, position: int,
                           member_id: int, earnings: float) -> Notification:
        """Notify a driver of their race result."""
        if position == 1:
            title = "Victory!"
            ntype = NotificationType.SUCCESS
        elif position <= 3:
            title = f"Podium Finish - P{position}"
            ntype = NotificationType.SUCCESS
        else:
            title = f"Race Complete - P{position}"
            ntype = NotificationType.INFO

        return self.create_notification(
            title=title,
            message=f"You finished in position {position}. "
                   f"Earnings: ${earnings:,.2f}",
            notification_type=ntype,
            category=NotificationCategory.RACE,
            priority=NotificationPriority.MEDIUM,
            target_member_id=member_id,
            metadata={"race_id": race_id, "position": position,
                      "earnings": earnings}
        )

    def notify_mission_available(self, mission_name: str,
                                 reward: float) -> Notification:
        """Broadcast that a new mission is available."""
        return self.create_notification(
            title="New Mission Available",
            message=f"Mission '{mission_name}' is now available! "
                   f"Reward: ${reward:,.2f}",
            notification_type=NotificationType.INFO,
            category=NotificationCategory.MISSION,
            priority=NotificationPriority.MEDIUM,
            metadata={"mission_name": mission_name, "reward": reward}
        )

    def notify_mission_assigned(self, mission_name: str,
                                member_id: int) -> Notification:
        """Notify a crew member they've been assigned to a mission."""
        return self.create_notification(
            title="Mission Assignment",
            message=f"You have been assigned to mission '{mission_name}'",
            notification_type=NotificationType.INFO,
            category=NotificationCategory.MISSION,
            priority=NotificationPriority.HIGH,
            target_member_id=member_id,
            metadata={"mission_name": mission_name}
        )

    def notify_low_funds(self, balance: float,
                         threshold: float) -> Notification:
        """Alert about low funds."""
        return self.create_notification(
            title="Low Funds Warning",
            message=f"Cash balance (${balance:,.2f}) has dropped below "
                   f"${threshold:,.2f}",
            notification_type=NotificationType.WARNING,
            category=NotificationCategory.FINANCIAL,
            priority=NotificationPriority.URGENT
        )

    def notify_car_needs_repair(self, car_name: str,
                                car_id: int) -> Notification:
        """Alert about car needing repair."""
        return self.create_notification(
            title="Car Needs Repair",
            message=f"Vehicle '{car_name}' has been damaged and needs repair",
            notification_type=NotificationType.WARNING,
            category=NotificationCategory.INVENTORY,
            priority=NotificationPriority.HIGH,
            metadata={"car_id": car_id}
        )

    def notify_achievement_unlocked(self, achievement_name: str,
                                    member_id: int,
                                    points: int) -> Notification:
        """Notify about unlocked achievement."""
        return self.create_notification(
            title="Achievement Unlocked!",
            message=f"You earned '{achievement_name}' (+{points} points)",
            notification_type=NotificationType.SUCCESS,
            category=NotificationCategory.ACHIEVEMENT,
            priority=NotificationPriority.MEDIUM,
            target_member_id=member_id,
            metadata={"achievement_name": achievement_name, "points": points}
        )

    def notify_crew_joined(self, member_name: str,
                           role: str) -> Notification:
        """Broadcast that a new crew member joined."""
        return self.create_notification(
            title="New Crew Member",
            message=f"{member_name} has joined the crew as {role}",
            notification_type=NotificationType.INFO,
            category=NotificationCategory.CREW,
            priority=NotificationPriority.LOW
        )

    def get_notification(self, notification_id: int) -> Optional[Notification]:
        """Get a notification by ID."""
        return self._notifications.get(notification_id)

    def get_notifications_for_member(self, member_id: int,
                                     unread_only: bool = False,
                                     category: Optional[NotificationCategory] = None,
                                     limit: int = 50) -> List[Notification]:
        """
        Get notifications for a specific member.

        Includes broadcasts and targeted notifications.
        """
        notifications = []

        for notif in self._notifications.values():
            # Check if notification is for this member
            if notif.target_member_id is not None and \
               notif.target_member_id != member_id:
                continue

            # Apply filters
            if unread_only and notif.read:
                continue

            if category is not None and notif.category != category:
                continue

            notifications.append(notif)

        # Sort by created_at descending
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications[:limit]

    def get_all_notifications(self, unread_only: bool = False,
                              limit: int = 100) -> List[Notification]:
        """Get all notifications (for admin view)."""
        notifications = list(self._notifications.values())

        if unread_only:
            notifications = [n for n in notifications if not n.read]

        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications[:limit]

    def mark_as_read(self, notification_id: int) -> bool:
        """Mark a notification as read."""
        notif = self._notifications.get(notification_id)
        if notif is None:
            return False

        if not notif.read:
            notif.read = True
            notif.read_at = datetime.now()

        return True

    def mark_all_read(self, member_id: int) -> int:
        """Mark all notifications for a member as read."""
        count = 0
        for notif in self.get_notifications_for_member(member_id, unread_only=True):
            self.mark_as_read(notif.notification_id)
            count += 1
        return count

    def delete_notification(self, notification_id: int) -> bool:
        """Delete a notification."""
        if notification_id in self._notifications:
            del self._notifications[notification_id]
            if notification_id in self._broadcast_notifications:
                self._broadcast_notifications.remove(notification_id)
            return True
        return False

    def get_unread_count(self, member_id: int) -> int:
        """Get count of unread notifications for a member."""
        return len(self.get_notifications_for_member(member_id, unread_only=True))

    def set_preferences(self, member_id: int,
                        preferences: NotificationPreference) -> None:
        """Set notification preferences for a member."""
        self._preferences[member_id] = preferences

    def get_preferences(self, member_id: int) -> NotificationPreference:
        """Get notification preferences for a member."""
        if member_id not in self._preferences:
            self._preferences[member_id] = NotificationPreference(
                member_id=member_id
            )
        return self._preferences[member_id]

    def clear_old_notifications(self, days: int = 30) -> int:
        """Clear notifications older than specified days."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        to_delete = [
            nid for nid, notif in self._notifications.items()
            if notif.created_at < cutoff and notif.read
        ]

        for nid in to_delete:
            self.delete_notification(nid)

        return len(to_delete)
