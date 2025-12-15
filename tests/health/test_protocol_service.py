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


@pytest.mark.django_db
def test_protocol_item_string_representation():
    """
    Test ProtocolItem.__str__ method (line 61 in protocol.py).
    """
    med = baker.make(Medication, name="Ivermectin")
    protocol = baker.make(HealthProtocol, name="Test Protocol")
    item = baker.make(
        ProtocolItem, protocol=protocol, medication=med, default_dosage="10ml/head"
    )

    assert str(item) == "Ivermectin (10ml/head)"


@pytest.mark.django_db
def test_apply_protocol_empty_cattle_list():
    """
    Test that applying a protocol with no cattle raises ValidationError (line 19).
    """
    protocol = baker.make(HealthProtocol)

    with pytest.raises(Exception) as exc_info:
        ProtocolService.apply_protocol(protocol.pk, [])

    assert "No cattle selected" in str(exc_info.value)


@pytest.mark.django_db
def test_apply_protocol_nonexistent_protocol():
    """
    Test that applying a non-existent protocol raises ValidationError (lines 23-24).
    """
    cow = baker.make(Cattle)

    with pytest.raises(Exception) as exc_info:
        ProtocolService.apply_protocol(999999, [cow.pk])

    assert "not found" in str(exc_info.value)


@pytest.mark.django_db
def test_apply_protocol_inactive_protocol():
    """
    Test that applying an inactive protocol raises ValidationError (line 27).
    """
    protocol = baker.make(HealthProtocol, is_active=False)
    cow = baker.make(Cattle)

    with pytest.raises(Exception) as exc_info:
        ProtocolService.apply_protocol(protocol.pk, [cow.pk])

    assert "inactive" in str(exc_info.value)


@pytest.mark.django_db
def test_apply_protocol_no_items():
    """
    Test that applying a protocol with no items raises ValidationError (line 31).
    """
    protocol = baker.make(HealthProtocol, is_active=True)
    cow = baker.make(Cattle)

    # Protocol has no items
    with pytest.raises(Exception) as exc_info:
        ProtocolService.apply_protocol(protocol.pk, [cow.pk])

    assert "no items" in str(exc_info.value).lower()


@pytest.mark.django_db
def test_apply_protocol_with_item_notes():
    """
    Test that item notes are included in event notes (line 70).
    """
    protocol = baker.make(HealthProtocol, name="Test Protocol", is_active=True)
    med = baker.make(Medication, name="Med A", withdrawal_days_meat=0)
    baker.make(
        ProtocolItem,
        protocol=protocol,
        medication=med,
        default_dosage="5ml",
        notes="Subcutaneous injection",
    )

    cow = baker.make(Cattle)

    ProtocolService.apply_protocol(protocol.pk, [cow.pk])

    event = SanitaryEvent.objects.first()
    assert "Subcutaneous injection" in event.notes


@pytest.mark.django_db
def test_apply_protocol_invalid_cattle_ids():
    """
    Test protocol application with some invalid cattle IDs (line 44).
    Should continue with valid IDs.
    """
    protocol = baker.make(HealthProtocol, name="Test Protocol", is_active=True)
    med = baker.make(Medication, name="Med A", withdrawal_days_meat=0)
    baker.make(ProtocolItem, protocol=protocol, medication=med, default_dosage="5ml")

    valid_cow = baker.make(Cattle)
    invalid_id = 999999

    # Should process valid cattle and skip invalid IDs without error
    result = ProtocolService.apply_protocol(protocol.pk, [valid_cow.pk, invalid_id])

    # Verify event was created even with invalid ID in list
    assert result["events_created"] == 1
    assert SanitaryEventTarget.objects.count() == 1
