import pytest
from django.db.utils import IntegrityError
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.health.models import (
    Medication,
    MedicationType,
    MedicationUnit,
    SanitaryEvent,
    SanitaryEventTarget,
)


@pytest.mark.django_db
class TestMedicationModel:
    def test_create_medication(self):
        med = baker.make(
            Medication,
            name="Dipyrone",
            medication_type=MedicationType.OTHER,
            unit=MedicationUnit.ML,
            withdrawal_days_meat=0,
        )
        assert med.name == "Dipyrone"
        assert str(med) == "Dipyrone (Other)"
        assert med.unit == "ML"

    def test_medication_defaults(self):
        med = baker.make(Medication, name="Generic Med")
        assert med.withdrawal_days_meat == 0
        assert med.unit == MedicationUnit.ML
        assert med.medication_type == MedicationType.OTHER


@pytest.mark.django_db
class TestSanitaryEventModel:
    def test_create_event_with_medication(self):
        med = baker.make(Medication, name="Vaccine X")
        event = baker.make(SanitaryEvent, title="Annual Vax", medication=med)
        assert event.medication == med
        assert str(event) == f"{event.date} - Annual Vax"

    def test_create_event_without_medication(self):
        # Allow events like 'Dehorning' which have no meds
        event = baker.make(SanitaryEvent, title="Dehorning", medication=None)
        assert event.medication is None


@pytest.mark.django_db
class TestSanitaryEventTargetModel:
    def test_target_creation(self):
        event = baker.make(SanitaryEvent)
        cow = baker.make(Cattle)
        target = baker.make(
            SanitaryEventTarget,
            event=event,
            animal=cow,
            applied_dose=10,
            cost_per_head=5.50,
        )

        assert target.event == event
        assert target.animal == cow
        assert target.applied_dose == 10
        assert target.cost_per_head == 5.50

    def test_unique_animal_per_event_constraint(self):
        event = baker.make(SanitaryEvent)
        cow = baker.make(Cattle)

        # First record
        baker.make(SanitaryEventTarget, event=event, animal=cow)

        # Duplicate record should fail
        with pytest.raises(IntegrityError):
            baker.make(SanitaryEventTarget, event=event, animal=cow)

    def test_soft_deleted_constraint_exception(self):
        """
        If a record is soft-deleted, we should be able to create a new one
        (if the unique constraint condition=Q(is_deleted=False) works).
        """
        event = baker.make(SanitaryEvent)
        cow = baker.make(Cattle)

        # Create and Soft Delete
        target1 = baker.make(SanitaryEventTarget, event=event, animal=cow)
        target1.delete()  # Soft delete

        # Should NOT raise IntegrityError because the first one is deleted
        target2 = baker.make(SanitaryEventTarget, event=event, animal=cow)
        assert target2.pk != target1.pk
