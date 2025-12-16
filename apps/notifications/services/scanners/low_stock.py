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
        # Find ingredients with low stock

        # We need F object for comparison in filter, but let's just iterate for complex logic
        # Actually filter is better:
        # We can't easily use F() for creation logic, so let's just iterate efficiently.

        for ingredient in FeedIngredient.objects.all():
            if ingredient.stock_quantity < ingredient.min_stock_alert:
                if self._should_notify(ingredient):
                    self._create_alert(ingredient)
                    count += 1
        return count

    def _should_notify(self, ingredient) -> bool:
        """
        Check if we already notified about this recently.
        Prevent spamming every minute.
        """
        # We need to construct the unique link or identity to check.
        link = f"/nutrition/ingredients/{ingredient.pk}/update/"

        # Check if there is an UNREAD alert for this ingredient
        return not self.notification_exists(
            recipient=None,  # We check in the loop actually... wait, strict definition says by user.
            # But here we want to know if *anyone* got it?
            # The original code checked:
            # exists = Notification.objects.filter(category=ALERT, link=link, is_read=False).exists()
            # It DID NOT filter by recipient!
            # So my helper needing recipient is slightly off for this specific logic unless I pass None.
            category=Notification.Category.ALERT,
            link=link,
            unread_only=True,
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
