from abc import ABC, abstractmethod

from django.contrib.auth import get_user_model


class BaseScanner(ABC):
    """
    Abstract base class for all notification scanners.
    Scanners are responsible for proactively checking system state
    and generating notifications if conditions are met.
    """

    @abstractmethod
    def scan(self) -> int:
        """
        Run the scan logic.
        Returns:
            int: Number of notifications created.
        """

    def _get_staff_users(self):
        """Helper to get all active staff users."""
        return get_user_model().objects.filter(is_active=True, is_staff=True)

    def notification_exists(
        self, recipient, category, link, unread_only=False, since=None
    ) -> bool:
        """
        Check if a notification exists matching specific criteria.
        Useful for deduplication.

        Args:
            recipient: The user object.
            category: Notification category string.
            link: The unique link identifier.
            unread_only (bool): If True, checks for any UNREAD notification.
            since (datetime): If provided, checks for any notification created after this time.

        Returns:
            bool: True if a match is found.
        """
        # Avoid circular import
        from apps.notifications.models import Notification

        filters = {"category": category, "link": link}
        if recipient:
            filters["recipient"] = recipient

        qs = Notification.objects.filter(**filters)

        if unread_only and qs.filter(is_read=False).exists():
            return True

        if since and qs.filter(created_at__gte=since).exists():
            return True

        return False
