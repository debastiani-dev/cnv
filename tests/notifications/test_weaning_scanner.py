from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.notifications.models import Notification
from apps.notifications.services.scanners.calf_weaning import CalfWeaningScanner


@pytest.mark.django_db
class TestCalfWeaningScanner:
    def test_scanner_alerts_weaning_age(self, user):
        user.is_staff = True
        user.save()
        today = timezone.now().date()

        # Born 210 days ago (Weaning age)
        weaning_bday = today - timedelta(days=210)

        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)

        # Valid Calf
        baker.make(
            Cattle,
            birth_date=weaning_bday,
            dam=dam,
            status=Cattle.STATUS_AVAILABLE,
            tag="CALF01",
        )

        # Too young (200 days)
        baker.make(Cattle, birth_date=today - timedelta(days=200), dam=dam)

        # No Dam (Orphan/Bought? Might handle differently, but current logic requires Dam)
        baker.make(Cattle, birth_date=weaning_bday, dam=None)

        # Dead Calf
        baker.make(Cattle, birth_date=weaning_bday, dam=dam, status=Cattle.STATUS_DEAD)

        scanner = CalfWeaningScanner()
        count = scanner.scan()

        assert count == 1
        notif = Notification.objects.first()
        assert "CALF01" in notif.message
        assert "ready for weaning" in notif.message

    def test_deduplication(self, user):
        user.is_staff = True
        user.save()
        today = timezone.now().date()
        weaning_bday = today - timedelta(days=210)
        dam = baker.make(Cattle)

        baker.make(Cattle, birth_date=weaning_bday, dam=dam)

        scanner = CalfWeaningScanner()
        scanner.scan()
        assert Notification.objects.count() == 1

        # Run again -> 0
        assert scanner.scan() == 0
