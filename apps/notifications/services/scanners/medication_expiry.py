from datetime import timedelta

from django.urls import reverse
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

        # Link to Update view since Detail view doesn't exist
        link = reverse("health:medication-update", kwargs={"pk": medication.pk})

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
