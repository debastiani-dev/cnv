from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.health.models import Medication, SanitaryEvent, SanitaryEventTarget
from apps.health.services import HealthService


@pytest.mark.django_db
class TestHealthServiceBatchCreate:
    def test_create_batch_event_splits_cost(self):
        # Setup
        cows = baker.make(Cattle, _quantity=10)
        cow_uuids = [str(c.pk) for c in cows]

        event_data = {
            "date": date.today(),
            "title": "Batch Test",
            "total_cost": 100.00,
            "medication": None,
        }

        # Execute
        event = HealthService.create_batch_event(event_data, cow_uuids)

        # Verify Header
        assert event.total_cost == 100.00
        assert SanitaryEvent.objects.count() == 1

        # Verify Targets
        assert SanitaryEventTarget.objects.count() == 10
        target = SanitaryEventTarget.objects.first()
        # 100 / 10 = 10.00
        assert target.cost_per_head == Decimal("10.00")
        assert target.animal.pk in [c.pk for c in cows]

    def test_create_batch_event_empty_list_raises_error(self):
        with pytest.raises(ValueError):
            HealthService.create_batch_event({}, [])


@pytest.mark.django_db
class TestHealthServiceWithdrawal:
    def test_withdrawal_period_blocks_animal(self):
        # Setup: Med with 20 days withdrawal
        med = baker.make(Medication, withdrawal_days_meat=20, name="Strong Med")
        cow = baker.make(Cattle)

        # Event 10 days ago (Active Withdrawal)
        event_date = timezone.localdate() - timedelta(days=10)
        event = baker.make(SanitaryEvent, date=event_date, medication=med)
        baker.make(SanitaryEventTarget, event=event, animal=cow)

        # Check
        is_blocked, reason = HealthService.check_withdrawal_status(cow)

        assert is_blocked is True
        assert "Animal in withdrawal period" in reason
        assert "Strong Med" in reason

    def test_withdrawal_period_expired_allows_animal(self):
        # Setup: Med with 20 days withdrawal
        med = baker.make(Medication, withdrawal_days_meat=20)
        cow = baker.make(Cattle)

        # Event 30 days ago (Expired Withdrawal)
        event_date = timezone.localdate() - timedelta(days=30)
        event = baker.make(SanitaryEvent, date=event_date, medication=med)
        baker.make(SanitaryEventTarget, event=event, animal=cow)

        # Check
        is_blocked, reason = HealthService.check_withdrawal_status(cow)

        assert is_blocked is False
        assert reason is None

    def test_no_medication_event_does_not_block(self):
        # Setup: Event without medication (e.g. dehorning)
        cow = baker.make(Cattle)
        event = baker.make(SanitaryEvent, date=date.today(), medication=None)
        baker.make(SanitaryEventTarget, event=event, animal=cow)

        is_blocked, _ = HealthService.check_withdrawal_status(cow)
        assert is_blocked is False
