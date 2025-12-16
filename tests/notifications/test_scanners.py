from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.notifications.models import Notification
from apps.notifications.services.scanners.low_stock import LowStockScanner
from apps.notifications.services.scanners.pregnancy_check import PregnancyCheckScanner
from apps.notifications.services.scanners.task_due import TaskDueScanner
from apps.nutrition.models.ingredient import FeedIngredient
from apps.reproduction.models.reproduction import BreedingEvent
from apps.tasks.models.tasks import Task


@pytest.mark.django_db
class TestScanners:

    def test_low_stock_scanner(self, user):
        """Test that low stock scanner creates notifications."""
        # Setup: 1 low stock, 1 normal stock
        low = baker.make(FeedIngredient, stock_quantity=10, min_stock_alert=50)
        ok = baker.make(FeedIngredient, stock_quantity=100, min_stock_alert=50)

        # Ensure staff user exists for notification
        user.is_staff = True
        user.save()

        scanner = LowStockScanner()
        count = scanner.scan()

        assert count == 1
        assert (
            Notification.objects.filter(category=Notification.Category.ALERT).count()
            == 1
        )
        assert Notification.objects.first().recipient == user

        # Run again: Should NOT create duplicate (deduplication check)
        count_2 = scanner.scan()
        assert count_2 == 0
        assert Notification.objects.count() == 1

    def test_task_due_scanner(self, user):
        """Test task due scanner."""
        today = timezone.now().date()

        # Due today, pending -> Notify
        t1 = baker.make(Task, due_date=today, status="PENDING", assigned_to=user)
        # Due tomorrow -> Ignore
        t2 = baker.make(
            Task, due_date=today + timedelta(days=1), status="PENDING", assigned_to=user
        )
        # Completed -> Ignore
        t3 = baker.make(Task, due_date=today, status="COMPLETED", assigned_to=user)

        # Signal listener creates notification for t1. Clear it to test scanner.
        Notification.objects.all().delete()

        scanner = TaskDueScanner()
        count = scanner.scan()

        assert count == 1
        assert (
            Notification.objects.filter(category=Notification.Category.REMINDER).count()
            == 1
        )

        # Deduplication
        count_2 = scanner.scan()
        assert count_2 == 0

    def test_pregnancy_check_scanner(self, user):
        """Test pregnancy check scanner."""
        user.is_staff = True
        user.save()

        today = timezone.now().date()
        old_date = today - timedelta(days=31)

        # Breeding > 30 days ago, no check -> Notify
        b1 = baker.make(BreedingEvent, date=old_date)

        # Recent breeding -> Ignore
        b2 = baker.make(BreedingEvent, date=today)

        # Signal listener likely fired for b1. Clear it.
        Notification.objects.all().delete()

        scanner = PregnancyCheckScanner()
        count = scanner.scan()

        # Note regarding pregnancy checks related name:
        # Since we passed `pregnancy_checks=[]` to baker, it implies a reverse relation.
        # If relation issue persists we might need to adjust how we mock 'no children'.
        # By default baker doesn't create children unless asked.

        assert count == 1
        assert (
            Notification.objects.filter(category=Notification.Category.REMINDER).count()
            == 1
        )

        # Deduplication
        count_2 = scanner.scan()
        assert count_2 == 0
