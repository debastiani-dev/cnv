from abc import ABC, abstractmethod

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.notifications.models import Notification


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
        # Avoid circular import - Handled at top now (lazy loading if needed?)
        # Notification is imported at top.

        filters = {"category": category, "link": link}
        if recipient:
            filters["recipient"] = recipient

        qs = Notification.objects.filter(**filters)

        if unread_only and qs.filter(is_read=False).exists():
            return True

        if since and qs.filter(created_at__gte=since).exists():
            return True

        return False

    def should_notify(self, recipient, category, link, cooldown_delta=None) -> bool:
        """
        Generic deduplication logic.
        Returns True if we SHOULD notify (i.e., no recent/unread notification exists).
        """
        # 1. Check for UNREAD
        if self.notification_exists(
            recipient=recipient,
            category=category,
            link=link,
            unread_only=True,
        ):
            return False

        # 2. Check for RECENT (within cooldown)
        if cooldown_delta:
            since = timezone.now() - cooldown_delta
            if self.notification_exists(
                recipient=recipient,
                category=category,
                link=link,
                since=since,
            ):
                return False

        return True
