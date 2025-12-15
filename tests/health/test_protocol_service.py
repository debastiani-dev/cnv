import pytest
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.health.models import (
    HealthProtocol,
    Medication,
    ProtocolItem,
    SanitaryEvent,
    SanitaryEventTarget,
)
from apps.health.services.protocol_service import ProtocolService


@pytest.mark.django_db
class TestProtocolService:
    def test_apply_protocol_creates_events(self):
        """
        Verify that apply_protocol creates one event per item, and targets all selected cattle.
        """
        # 1. Setup Data
        protocol = baker.make(HealthProtocol, name="Test Protocol", is_active=True)
        med1 = baker.make(Medication, name="Med A", withdrawal_days_meat=0)
        med2 = baker.make(Medication, name="Med B", withdrawal_days_meat=10)

        baker.make(
            ProtocolItem, protocol=protocol, medication=med1, default_dosage="5ml"
        )
        baker.make(
            ProtocolItem, protocol=protocol, medication=med2, default_dosage="10ml"
        )

        cows = baker.make(Cattle, _quantity=3)
        cow_ids = [c.pk for c in cows]

        # 2. Execute
        result = ProtocolService.apply_protocol(protocol.pk, cow_ids)

        # 3. Verify Summary Return
        assert result["events_created"] == 2  # 2 items in protocol
        assert result["cattle_count"] == 3

        # 4. Verify DB State - Events
        events = SanitaryEvent.objects.all()
        assert events.count() == 2

        # Verify Med A Event
        event_a = events.filter(medication=med1).first()
        assert event_a is not None
        assert "Med A" in event_a.medication.name

        # Verify Targets for Event A
        targets_a = SanitaryEventTarget.objects.filter(event=event_a)
        assert targets_a.count() == 3
        assert list(
            targets_a.values_list("animal_id", flat=True).order_by("animal_id")
        ) == sorted(cow_ids)
        assert targets_a.first().observation == "Dosage: 5ml"

    def test_apply_protocol_withdrawal_update(self):
        """
        Verify that applying a protocol with withdrawal meds updates the cattle's withdrawal date.
        """
        protocol = baker.make(HealthProtocol)
        med = baker.make(Medication, withdrawal_days_meat=20)
        baker.make(ProtocolItem, protocol=protocol, medication=med)

        cow = baker.make(Cattle, withdrawal_end_date=None)

        today = timezone.now().date()
        ProtocolService.apply_protocol(protocol.pk, [cow.pk], date=today)

        cow.refresh_from_db()
        expected_withdrawal = today + timezone.timedelta(days=20)
        assert cow.withdrawal_end_date == expected_withdrawal
