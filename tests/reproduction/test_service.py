from datetime import date, timedelta

import pytest
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.reproduction.models import BreedingEvent, PregnancyCheck
from apps.reproduction.services.reproduction_service import ReproductionService


@pytest.mark.django_db
class TestReproductionService:
    def test_record_breeding(self):
        """Test that breeding updates cow status to BRED."""
        cow = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_OPEN
        )
        bull = baker.make(Cattle, sex=Cattle.SEX_MALE)
        breeding_date = date(2024, 1, 1)

        event = ReproductionService.record_breeding(
            dam=cow, date=breeding_date, method=BreedingEvent.METHOD_AI, sire=bull
        )

        cow.refresh_from_db()
        assert event.dam == cow
        assert cow.reproduction_status == Cattle.REP_STATUS_BRED

    def test_record_diagnosis_positive(self):
        """Test positive diagnosis updates status to PREGNANT and calculates due date."""
        cow = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_BRED
        )
        event = baker.make(BreedingEvent, dam=cow, date=date(2024, 1, 1))

        check_date = date(2024, 2, 1)
        check = ReproductionService.record_diagnosis(
            breeding_event=event, date=check_date, result=PregnancyCheck.RESULT_POSITIVE
        )

        cow.refresh_from_db()
        assert cow.reproduction_status == Cattle.REP_STATUS_PREGNANT

        # Check calculation (290 days)
        expected_due = event.date + timedelta(days=290)
        assert check.expected_calving_date == expected_due

    def test_record_diagnosis_negative(self):
        """Test negative diagnosis resets status to OPEN."""
        cow = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_BRED
        )
        event = baker.make(BreedingEvent, dam=cow, date=date(2024, 1, 1))

        ReproductionService.record_diagnosis(
            breeding_event=event,
            date=date(2024, 2, 1),
            result=PregnancyCheck.RESULT_NEGATIVE,
        )

        cow.refresh_from_db()
        assert cow.reproduction_status == Cattle.REP_STATUS_OPEN

    def test_register_birth_auto_creation(self):
        """Test that registering a birth automatically creates the calf with lineage."""
        cow = baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
        )
        bull = baker.make(Cattle, sex=Cattle.SEX_MALE)
        event = baker.make(BreedingEvent, dam=cow, sire=bull, date=date(2024, 1, 1))

        calving_date = date(2024, 10, 15)
        calf_data = {"tag": "CALF001", "sex": Cattle.SEX_FEMALE, "weight_kg": 35.5}

        calving, calf = ReproductionService.register_birth(
            dam=cow, date=calving_date, breeding_event=event, calf_data=calf_data
        )

        # Verify Calf
        assert calf.tag == "CALF001"
        assert calf.dam == cow
        assert calf.sire == bull
        assert calf.birth_date == calving_date

        # Verify Dam Status
        cow.refresh_from_db()
        assert cow.reproduction_status == Cattle.REP_STATUS_LACTATING

        # Verify Calving Link
        assert calving.calf == calf

    def test_calculate_due_date_none(self):
        """Test calculate_due_date returns None if date is missing."""
        assert ReproductionService.calculate_due_date(None) is None

    def test_record_breeding_male_exception(self):
        """Test that breeding a male raises ValueError."""
        bull = baker.make(Cattle, sex=Cattle.SEX_MALE)
        with pytest.raises(ValueError, match="Only female cattle can be bred"):
            ReproductionService.record_breeding(
                dam=bull, date=date(2024, 1, 1), method=BreedingEvent.METHOD_NATURAL
            )
