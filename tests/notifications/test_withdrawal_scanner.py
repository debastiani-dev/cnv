import pytest
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.notifications.models import Notification
from apps.notifications.services.scanners.withdrawal_end import WithdrawalEndScanner


@pytest.mark.django_db
class TestWithdrawalEndScanner:
    def test_scanner_alerts_withdrawal_end(self, user):
        user.is_staff = True
        user.save()
        today = timezone.now().date()

        # Ends today -> Notify
        baker.make(Cattle, withdrawal_end_date=today, tag="SAFE001")
        # Ends tomorrow -> Ignore
        baker.make(Cattle, withdrawal_end_date=today + timezone.timedelta(days=1))
        # Ended yesterday -> Ignore (already notified presumably)
        baker.make(Cattle, withdrawal_end_date=today - timezone.timedelta(days=1))

        scanner = WithdrawalEndScanner()
        count = scanner.scan()

        assert count == 1
        notif = Notification.objects.first()
        assert notif.category == Notification.Category.SUCCESS
        assert "SAFE001" in notif.message
        assert "safe for slaughter" in notif.message

    def test_deduplication(self, user):
        user.is_staff = True
        user.save()
        today = timezone.now().date()

        baker.make(Cattle, withdrawal_end_date=today)

        scanner = WithdrawalEndScanner()
        scanner.scan()
        assert Notification.objects.count() == 1

        # Run again -> 0
        assert scanner.scan() == 0

    def test_check_end_withdrawal_explicit(self, user):
        """Explicitly test check_end_withdrawal returns False if notification exists."""
        user.is_staff = True
        user.save()
        today = timezone.now().date()
        cow = baker.make(Cattle, withdrawal_end_date=today)
        scanner = WithdrawalEndScanner()

        # First run: True
        assert scanner.check_animal(cow) is True

        # Second run: False (hits line 56)
        assert scanner.check_animal(cow) is False

    def test_scanner_skips_read_recent_notification(self, user):
        """Test that line 56 (recent READ notification) is hit."""
        user.is_staff = True
        user.save()
        today = timezone.now().date()
        cow = baker.make(Cattle, withdrawal_end_date=today)
        scanner = WithdrawalEndScanner()

        # 1. Create Notification
        scanner.scan()
        assert Notification.objects.count() == 1
        notif = Notification.objects.first()

        # 2. Mark as READ
        notif.is_read = True
        notif.save()

        # 3. Scan again
        # Outer check (Unread?) -> Passes (No unread)
        # Inner check (Recent?) -> Fails (Recent exists) -> Returns False (Line 56)
        assert scanner.check_animal(cow) is False
