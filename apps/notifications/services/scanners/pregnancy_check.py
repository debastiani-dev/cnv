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
        cutoff_date = today - timezone.timedelta(days=30)

        # Find breeding events older than 30 days with no pregnancy checks
        # Using filter logic from check_reminders command
        pending_checks = BreedingEvent.objects.filter(
            date__lte=cutoff_date, pregnancy_checks__isnull=True
        )

        for event in pending_checks:
            if self._should_notify(event):
                self._create_reminder(event)
                count += 1

        return count

    def _should_notify(self, event) -> bool:
        """
        Avoid spam.
        """
        link = f"/reproduction/breeding/{event.pk}/"

        # 1. Check for unread
        if self.notification_exists(
            recipient=None,  # Check if *anyone* has an unread reminder for this?
            # Actually, reminders are usually personal, but for breeding
            # we broadcast to all staff. If ONE staff has it unread, maybe don't spam others?
            # Original logic:
            # unread_exists = Notification.objects.filter(..., link=link, is_read=False).exists()
            # This implies checking ALL recipients again.
            category=Notification.Category.REMINDER,
            link=link,
            unread_only=True,
        ):
            return False

        # 2. Check for recent (sent in last 7 days)
        last_week = timezone.now() - timezone.timedelta(days=7)

        if self.notification_exists(
            recipient=None,  # Check if anyone got it recently
            category=Notification.Category.REMINDER,
            link=link,
            since=last_week,
        ):
            return False

        return True

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
                link=f"/reproduction/breeding/{event.pk}/",
            )
