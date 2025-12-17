from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.health.models.health import Medication
from apps.notifications.models import Notification
from apps.notifications.services.scanners.medication_expiry import (
    MedicationExpiryScanner,
)


@pytest.mark.django_db
class TestMedicationExpiryScanner:
    def test_scanner_alerts_expired_and_expiring(self, user):
        user.is_staff = True
        user.save()
        today = timezone.now().date()

        # Expired (yesterday)
        baker.make(
            Medication, expiration_date=today - timedelta(days=1), name="Expired Med"
        )
        # Expiring Soon (tomorrow)
        baker.make(
            Medication, expiration_date=today + timedelta(days=1), name="Expiring Soon"
        )
        # Safe (next year)
        baker.make(
            Medication, expiration_date=today + timedelta(days=365), name="Safe Med"
        )

        scanner = MedicationExpiryScanner()
        count = scanner.scan()

        # 1 Expired + 1 Expiring = 2
        assert count == 2
        assert Notification.objects.count() == 2

        # Verify Categories
        expired_notif = Notification.objects.get(title="Medication Expired")
        assert expired_notif.category == Notification.Category.ALERT

        expiring_notif = Notification.objects.get(title="Medication Expiring Soon")
        assert expiring_notif.category == Notification.Category.INFO

    def test_deduplication(self, user):
        user.is_staff = True
        user.save()
        today = timezone.now().date()

        baker.make(Medication, expiration_date=today + timedelta(days=5))

        scanner = MedicationExpiryScanner()
        scanner.scan()
        assert Notification.objects.count() == 1

        # Run again immediately -> 0
        assert scanner.scan() == 0
