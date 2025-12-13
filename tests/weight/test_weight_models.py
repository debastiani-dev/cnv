import pytest
from model_bakery import baker

from apps.weight.models import WeighingSession, WeighingSessionType


@pytest.mark.django_db
def test_weighing_session_str():
    """Test the __str__ method of WeighingSession."""
    session = baker.make(
        WeighingSession,
        name="Test Session",
        date="2024-01-01",
        session_type=WeighingSessionType.ROUTINE,
    )
    assert str(session) == "2024-01-01 - Test Session (Routine)"


@pytest.mark.django_db
def test_weight_record_str():
    """Test the __str__ method of WeightRecord."""
    # Mocking cattle string if necessary, but baker should handle it.
    cow = baker.make("cattle.Cattle", tag="TAG123")
    record = baker.make("weight.WeightRecord", animal=cow, weight_kg=350.50)
    expected_cow_str = str(cow)
    assert (
        str(record) == f"{expected_cow_str} - 350.5kg"
        or str(record) == f"{expected_cow_str} - 350.50kg"
    )
