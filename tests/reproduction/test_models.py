import pytest
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.reproduction.models import (
    BreedingEvent,
    Calving,
    PregnancyCheck,
    ReproductiveSeason,
)


@pytest.mark.django_db
class TestReproductionModels:
    def test_reproduction_season_creation(self):
        season = baker.make(ReproductiveSeason, name="2024/2025")
        assert str(season) == "2024/2025"

    def test_breeding_event_creation(self):
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        bull = baker.make(Cattle, sex=Cattle.SEX_MALE)

        event = baker.make(
            BreedingEvent, dam=cow, sire=bull, breeding_method=BreedingEvent.METHOD_AI
        )

        assert event.dam == cow
        assert event.sire == bull
        assert cow.tag in str(event)

    def test_pregnancy_check_creation(self):
        event = baker.make(BreedingEvent)
        check = baker.make(
            PregnancyCheck, breeding_event=event, result=PregnancyCheck.RESULT_POSITIVE
        )
        assert check.breeding_event == event
        assert check.result == PregnancyCheck.RESULT_POSITIVE

    def test_calving_creation(self):
        event = baker.make(BreedingEvent)
        calving = baker.make(Calving, dam=event.dam, breeding_event=event)
        assert calving.dam == event.dam
        assert str(calving).startswith("Calving:")

    def test_pregnancy_check_str(self):
        """Test PregnancyCheck __str__ method (reproduction.py line 115)."""
        dam = baker.make(Cattle, tag="COW001", sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(
            PregnancyCheck,
            breeding_event=breeding,
            result=PregnancyCheck.RESULT_POSITIVE,
        )

        # __str__ should return "Dam - Result Display"
        expected_str = str(check)
        assert str(dam) in expected_str
        assert "Positive" in expected_str
