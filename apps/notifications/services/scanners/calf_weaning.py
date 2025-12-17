from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.cattle.models.cattle import Cattle
from apps.notifications.models import Notification
from apps.notifications.services.scanners.base import BaseScanner


class CalfWeaningScanner(BaseScanner):
    """
    Scans for calves that reached weaning age (7 months / 210 days).
    """

    def scan(self) -> int:
        count = 0
        today = timezone.now().date()

        # 7 months approx 210 days
        weaning_age_days = 210
        target_birth_date = today - timedelta(days=weaning_age_days)

        # Find calves born exactly 210 days ago
        # Must be active, have a dam (implies nursing context usually), not dead/sold
        ready_calves = Cattle.objects.filter(
            birth_date=target_birth_date,
            status=Cattle.STATUS_AVAILABLE,
            dam__isnull=False,
        )

        for calf in ready_calves:
            if self.check_calf(calf):
                count += 1

        return count

    def check_calf(self, calf) -> bool:
        link = f"/cattle/{calf.pk}/"

        if self.should_notify(
            recipient=None,
            category=Notification.Category.INFO,
            link=link,
            # Prevent duplicate on same day
            cooldown_delta=timedelta(days=1),
        ):
            self._create_alert(calf, link)
            return True
        return False

    def _create_alert(self, calf, link):
        self.notify_staff(
            title=_("Weaning Due"),
            message=_("Calf {tag} is 7 months old and ready for weaning.").format(
                tag=calf.tag
            ),
            category=Notification.Category.INFO,
            link=link,
        )
