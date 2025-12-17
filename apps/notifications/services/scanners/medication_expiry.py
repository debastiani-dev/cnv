from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.health.models.health import Medication
from apps.notifications.models import Notification
from apps.notifications.services.scanners.base import BaseScanner


class MedicationExpiryScanner(BaseScanner):
    """
    Scans for medications that are expired or expiring soon (30 days).
    """

    def scan(self) -> int:
        count = 0
        today = timezone.now().date()
        warning_threshold = today + timedelta(days=30)

        # 1. Expired
        expired = Medication.objects.filter(expiration_date__lt=today)
        for med in expired:
            if self.check_medication(med, status="EXPIRED"):
                count += 1

        # 2. Expiring Soon (future but within 30 days)
        expiring = Medication.objects.filter(
            expiration_date__gte=today, expiration_date__lte=warning_threshold
        )
        for med in expiring:
            if self.check_medication(med, status="EXPIRING"):
                count += 1

        return count

    def check_medication(self, medication, status) -> bool:
        """
        Check a single medication and notify if needed.
        """
        category = (
            Notification.Category.ALERT
            if status == "EXPIRED"
            else Notification.Category.INFO
        )

        # Link to list view with filter or detail if available.
        # Assuming detail view exists or fallback to list.
        link = f"/health/medications/{medication.pk}/"

        # Unique identifier for this SPECIFIC alert type
        # We append status to link purely for deduplication uniqueness if needed,
        # or rely on separate scan logic.
        # Actually, let's use the standard link but rely on cooldown/unread.

        # Deduplication Rule:
        # If we notified about "EXPIRING" recently, don't spam.
        # If it changes to "EXPIRED", that is a NEW event?
        # Yes. But the link is the same.
        # So `notification_exists` with same link would block it?
        # We should probably differentiate the link or category in deduplication.
        # BaseScanner uses (recipient, category, link).
        # Category differs! ALERT vs INFO. So that helps.

        if self.should_notify(
            recipient=None,
            category=category,
            link=link,
            cooldown_delta=timedelta(days=7),  # Remind weekly
        ):
            self._create_alert(medication, status, category, link)
            return True
        return False

    def _create_alert(self, medication, status, category, link):
        if status == "EXPIRED":
            title = _("Medication Expired")
            msg = _("Medication '{name}' expired on {date}.").format(
                name=medication.name, date=medication.expiration_date
            )
        else:
            title = _("Medication Expiring Soon")
            msg = _("Medication '{name}' expires on {date}.").format(
                name=medication.name, date=medication.expiration_date
            )

        self.notify_staff(title, msg, category, link)
