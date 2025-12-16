from datetime import timedelta

from django.utils.translation import gettext as _

from apps.notifications.models import Notification
from apps.notifications.services.notification_service import create_notification
from apps.notifications.services.scanners.base import BaseScanner
from apps.nutrition.models.ingredient import FeedIngredient


class LowStockScanner(BaseScanner):
    """
    Scans for ingredients that are below their minimum stock threshold.
    """

    def scan(self) -> int:
        count = 0
        for ingredient in FeedIngredient.objects.all():
            if ingredient.stock_quantity < ingredient.min_stock_alert:
                if self.check_ingredient(ingredient):
                    count += 1
        return count

    def check_ingredient(self, ingredient) -> bool:
        """
        Check a single ingredient and notify if needed.
        """
        if self._should_notify(ingredient):
            self._create_alert(ingredient)
            return True
        return False

    def _should_notify(self, ingredient) -> bool:
        """
        Check if we already notified about this recently.
        """
        return self.should_notify(
            recipient=None,
            category=Notification.Category.ALERT,
            link=f"/nutrition/ingredients/{ingredient.pk}/update/",
            cooldown_delta=timedelta(days=1),
        )

    def _create_alert(self, ingredient):
        staff_users = self._get_staff_users()
        for user in staff_users:
            create_notification(
                recipient=user,
                title=_("Low Stock Alert"),
                message=_(
                    "Stock for {ingredient} is low ({current}kg). Min threshold: {min}kg."
                ).format(
                    ingredient=ingredient.name,
                    current=ingredient.stock_quantity,
                    min=ingredient.min_stock_alert,
                ),
                category=Notification.Category.ALERT,
                link=f"/nutrition/ingredients/{ingredient.pk}/update/",
            )
