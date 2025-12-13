# pylint: disable=unused-argument, redefined-outer-name
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.cattle.models.cattle import Cattle
from apps.weight.models.session import WeighingSession
from apps.weight.services.weight_service import WeightService


@pytest.mark.django_db
class TestWeightService:
    @pytest.fixture
    def cattle(self):
        return Cattle.objects.create(
            tag="TEST001",
            birth_date=date(2023, 1, 1),
            weight_kg=Decimal("40.00"),  # Birth weight
        )

    @pytest.fixture
    def session_1(self):
        return WeighingSession.objects.create(
            date=date(2023, 6, 1),
            name="Session 1",
            session_type="ROUTINE",
        )

    @pytest.fixture
    def session_2(self):
        return WeighingSession.objects.create(
            date=date(2023, 7, 1),  # 30 days later
            name="Session 2",
            session_type="ROUTINE",
        )

    def test_record_weight_first_time(self, cattle, session_1):
        """Test recording weight for the first time updates cattle inventory."""
        weight = Decimal("200.00")
        record = WeightService.record_weight(session_1, cattle, weight)

        # Check record
        assert record.weight_kg == weight
        assert record.adg is None  # No previous record
        assert record.days_since_prev_weight is None

        # Check cattle inventory update
        cattle.refresh_from_db()
        assert cattle.current_weight == weight
        assert cattle.last_weighing_date == session_1.date

    def test_record_weight_calculates_adg(self, cattle, session_1, session_2):
        """Test ADG calculation between two sessions."""
        # Record 1
        WeightService.record_weight(session_1, cattle, Decimal("200.00"))

        # Record 2 (30 days later, +30kg)
        # ADG should be 1.0 kg/day
        weight_2 = Decimal("230.00")
        record_2 = WeightService.record_weight(session_2, cattle, weight_2)

        # Check record 2
        assert record_2.weight_kg == weight_2
        assert record_2.days_since_prev_weight == 30
        assert record_2.adg == Decimal("1.000")  # 30kg / 30days

        # Check cattle inventory update
        cattle.refresh_from_db()
        assert cattle.current_weight == weight_2
        assert cattle.last_weighing_date == session_2.date

    def test_record_weight_historical_insert(self, cattle, session_1, session_2):
        """Test inserting a historical record does NOT overwrite later inventory data."""
        # Record 2 (Latest) first
        WeightService.record_weight(session_2, cattle, Decimal("230.00"))

        cattle.refresh_from_db()
        assert cattle.current_weight == Decimal("230.00")
        assert cattle.last_weighing_date == session_2.date

        # Record 1 (Historical) - 30 days earlier
        weight_1 = Decimal("200.00")
        record_1 = WeightService.record_weight(session_1, cattle, weight_1)

        # Check record 1 ADG (Should be None as there is no record BEFORE it)
        assert record_1.adg is None

        # Check cattle inventory (Should UNCHANGED)
        cattle.refresh_from_db()
        assert cattle.current_weight == Decimal("230.00")
        assert cattle.last_weighing_date == session_2.date

    def test_get_herd_adg_stats(self, cattle, session_1, session_2):
        """Test herd stats calculation."""
        # Setup: cattle with 1.0 ADG in last 90 days
        # We need another cow to make it an average
        cattle_2 = Cattle.objects.create(tag="TEST002", birth_date=date(2023, 1, 1))

        # Make sure sessions are recent relative to generic "now" if test runs far in future?
        # Actually session dates are hardcoded 2023. If run in 2025, 'last 90 days' will fail.
        # We should use timezone.now() relative dates for this test.

        # Re-creating sessions with relative dates
        today = timezone.now().date()
        date_1 = today - timedelta(days=30)
        date_2 = today

        session_recent_1 = WeighingSession.objects.create(
            date=date_1, name="R1", session_type="ROUTINE"
        )
        session_recent_2 = WeighingSession.objects.create(
            date=date_2, name="R2", session_type="ROUTINE"
        )

        # Cow 1: 1.0 ADG
        WeightService.record_weight(session_recent_1, cattle, Decimal("200.00"))
        WeightService.record_weight(
            session_recent_2, cattle, Decimal("230.00")
        )  # +30kg / 30d = 1.0

        # Cow 2: 2.0 ADG
        WeightService.record_weight(session_recent_1, cattle_2, Decimal("200.00"))
        WeightService.record_weight(
            session_recent_2, cattle_2, Decimal("260.00")
        )  # +60kg / 30d = 2.0

        stats = WeightService.get_herd_adg_stats(days=90)

        # Average of 1.0 and 2.0 is 1.5
        assert stats["avg_adg"] == Decimal("1.500")

    def test_get_animal_weight_history(self, cattle, session_1, session_2):
        """Test retrieving weight history ordered by date."""
        # Create records out of order
        rec2 = WeightService.record_weight(session_2, cattle, Decimal("300"))
        rec1 = WeightService.record_weight(session_1, cattle, Decimal("200"))

        history = WeightService.get_animal_weight_history(cattle)
        assert list(history) == [rec1, rec2]
        assert history[0].session.date < history[1].session.date
