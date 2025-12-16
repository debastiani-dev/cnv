from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.notifications.models import Notification
from apps.notifications.services.notification_service import create_notification
from apps.notifications.services.scanners.base import BaseScanner
from apps.reproduction.models.reproduction import BreedingEvent


class PregnancyCheckScanner(BaseScanner):
    """
    Scans for breeding events that are overdue for a pregnancy check (30+ days).
    """

    def scan(self) -> int:
        count = 0
        today = timezone.now().date()
        cutoff_date = today - timedelta(days=30)

        # Find breeding events older than 30 days with no pregnancy checks
        # Using filter logic from check_reminders command
        pending_checks = BreedingEvent.objects.filter(
            date__lte=cutoff_date, pregnancy_checks__isnull=True
        )

        for event in pending_checks:
            if self.check_event(event):
                count += 1

        return count

    def check_event(self, event) -> bool:
        """
        Check a single breeding event and notify if needed.
        Returns True if notification was created.
        """
        if self._should_notify(event):
            self._create_reminder(event)
            return True
        return False

    def _should_notify(self, event) -> bool:
        """
        Avoid spam.
        """
        # Fix: Point to list view with query param for uniqueness and highlighting
        # This solves W0613 (unused event) and provides a valid URL
        return self.should_notify(
            recipient=None,
            category=Notification.Category.REMINDER,
            link=f"/reproduction/breeding/?highlight={event.pk}",
            cooldown_delta=timedelta(days=7),
        )

    def _create_reminder(self, event):
        staff_users = self._get_staff_users()
        for user in staff_users:
            create_notification(
                recipient=user,
                title=_("Pregnancy Check Due"),
                message=_(
                    "Breeding event for {dam} on {date} needs a pregnancy check."
                ).format(dam=event.dam, date=event.date),
                category=Notification.Category.REMINDER,
                link=f"/reproduction/breeding/?highlight={event.pk}",
            )
