from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.cattle.models.cattle import Cattle
from apps.notifications.models import Notification
from apps.notifications.services.scanners.base import BaseScanner


class WithdrawalEndScanner(BaseScanner):
    """
    Scans for cattle whose withdrawal period ends today.
    """

    def scan(self) -> int:
        count = 0
        today = timezone.now().date()

        # Animals whose withdrawal ends exactly today
        safe_cattle = Cattle.objects.filter(withdrawal_end_date=today)

        for animal in safe_cattle:
            if self.check_animal(animal):
                count += 1

        return count

    def check_animal(self, animal) -> bool:
        """
        Check and notify.
        """
        # One-time notification for this event.
        # Since query is strict (date=today), we just need to ensure we didn't already run today.

        link = f"/cattle/{animal.pk}/"

        if self.should_notify(
            recipient=None,
            category=Notification.Category.SUCCESS,
            link=link,
            # Cooldown isn't mostly relevant as date changes tomorrow,
            # but prevents double run same day.
            cooldown_delta=None,
        ):
            # Special check: prevent multiple same-day alerts if should_notify didn't catch it
            # (e.g. if we rely on unread).
            # But BaseScanner checks unread.
            # Let's add strict 'since today' check for safety?
            # BaseScanner.notification_exists(since=midnight) is good.
            # Let's pass cooldown_delta=1 day just to be safe.

            if not self.should_notify(
                None, Notification.Category.SUCCESS, link, timedelta(days=1)
            ):
                return False

            self._create_alert(animal, link)
            return True
        return False

    def _create_alert(self, animal, link):
        self.notify_staff(
            title=_("Withdrawal Period Ended"),
            message=_("Animal {tag} is now safe for slaughter/production.").format(
                tag=animal.tag
            ),
            category=Notification.Category.SUCCESS,
            link=link,
        )
