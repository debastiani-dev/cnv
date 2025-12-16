from django.utils import timezone
from django.utils.translation import gettext as _

from apps.notifications.models import Notification
from apps.notifications.services.notification_service import create_notification
from apps.notifications.services.scanners.base import BaseScanner
from apps.tasks.models.tasks import Task


class TaskDueScanner(BaseScanner):
    """
    Scans for tasks that are due today or overdue.
    """

    def scan(self) -> int:
        count = 0
        today = timezone.now().date()

        # Find tasks due today or earlier (overdue) that are incomplete
        pending_tasks = Task.objects.filter(
            due_date__lte=today,
            status__in=["PENDING", "IN_PROGRESS"],
            assigned_to__isnull=False,
        )

        for task in pending_tasks:
            if self._should_notify(task):
                self._create_reminder(task)
                count += 1

        return count

    def _should_notify(self, task) -> bool:
        """
        Prevent spam. Only notify if:
        1. No unread reminder exists.
        2. AND no reminder sent TODAY.
        """
        link = f"/tasks/{task.pk}/"

        # 1. Check for unread
        if self.notification_exists(
            recipient=task.assigned_to,
            category=Notification.Category.REMINDER,
            link=link,
            unread_only=True,
        ):
            return False

        # 2. Check for any sent TODAY
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if self.notification_exists(
            recipient=task.assigned_to,
            category=Notification.Category.REMINDER,
            link=link,
            since=today_start,
        ):
            return False

        return True

    def _create_reminder(self, task):
        create_notification(
            recipient=task.assigned_to,
            title=_("Task Due"),
            message=_("Task '{title}' is due today or overdue.").format(
                title=task.title
            ),
            category=Notification.Category.REMINDER,
            link=f"/tasks/{task.pk}/",
        )
