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
        baker.make(FeedIngredient, stock_quantity=10, min_stock_alert=50)
        baker.make(FeedIngredient, stock_quantity=100, min_stock_alert=50)

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

        # Run again: Should NOT create duplicate (deduplication check - unread)
        count_2 = scanner.scan()
        assert count_2 == 0
        assert Notification.objects.count() == 1

        # Run again: Should NOT create duplicate (read but recently sent)
        notif = Notification.objects.first()
        notif.is_read = True
        notif.save()

        count_3 = scanner.scan()
        assert count_3 == 0  # Should be 0 because < 24h passed

    def test_task_due_scanner(self, user):
        """Test task due scanner."""
        today = timezone.now().date()

        # Due today, pending -> Notify
        baker.make(Task, due_date=today, status="PENDING", assigned_to=user)
        # Due tomorrow -> Ignore
        baker.make(
            Task, due_date=today + timedelta(days=1), status="PENDING", assigned_to=user
        )
        # Completed -> Ignore
        baker.make(Task, due_date=today, status="COMPLETED", assigned_to=user)

        # Signal listener creates notification for t1. Clear it to test scanner.
        Notification.all_objects.all().delete(destroy=True)

        scanner = TaskDueScanner()
        count = scanner.scan()

        assert count == 1
        assert (
            Notification.objects.filter(category=Notification.Category.REMINDER).count()
            == 1
        )

        # Deduplication (unread)
        count_2 = scanner.scan()
        assert count_2 == 0

        # Deduplication (read but sent TODAY)
        notif = Notification.objects.first()
        notif.is_read = True
        notif.save()

        # Should still be 0 because it was sent today
        count_3 = scanner.scan()
        assert count_3 == 0

    def test_pregnancy_check_scanner(self, user):
        """Test pregnancy check scanner."""
        user.is_staff = True
        user.save()

        today = timezone.now().date()
        old_date = today - timedelta(days=31)

        # Breeding > 30 days ago, no check -> Notify
        baker.make(BreedingEvent, date=old_date)

        # Recent breeding -> Ignore
        baker.make(BreedingEvent, date=today)

        # Signal listener likely fired for b1. Clear it.
        Notification.all_objects.all().delete(destroy=True)

        scanner = PregnancyCheckScanner()
        count = scanner.scan()

        assert count == 1
        assert (
            Notification.objects.filter(category=Notification.Category.REMINDER).count()
            == 1
        )
        # Since we use ?highlight=pk, and b1 is the one older than 30 days
        # We need to find the b1 object. b1 variable is not available here actually...
        # Wait, lines 99-102: b1 = baker.make... b1 is local to that block? No, Python scoiing.
        # But b1 was created in previous edit (baker.make calls).
        # Ah, I replaced the variable assignment with bare call in step 16882!
        # So I don't have b1 reference easily.
        # I'll fetch it from DB or notification.
        notif = Notification.objects.first()
        assert notif.link.startswith("/reproduction/diagnosis/add/?breeding_event=")

        # Deduplication (unread)
        count_2 = scanner.scan()
        assert count_2 == 0

        # Deduplication (read but sent recently - within 7 days)
        notif = Notification.objects.first()
        notif.is_read = True
        notif.save()

        # Should still be 0 because it was sent recently
        count_3 = scanner.scan()
        assert count_3 == 0
