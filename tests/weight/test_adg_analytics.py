from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.weight.models import WeighingSession, WeightRecord
from apps.weight.services.analytics import get_global_adg_metrics


@pytest.mark.django_db
class TestAdgAnalytics:
    def test_basic_adg_calculation(self):
        """
        Verify ADG is aggregated correctly for active animals.
        Cow A: ADG 1.0
        Cow B: ADG 0.5
        Global: 0.75
        """
        # Create Cows
        cow_a = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)
        cow_b = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)

        # Create Session 30 days ago and Now
        now = timezone.now()
        session_now = baker.make(WeighingSession, date=now)

        # Cow A (ADG 1.0)
        baker.make(
            WeightRecord,
            animal=cow_a,
            session=session_now,
            adg=Decimal("1.000"),
            weight_kg=Decimal("330.00"),
        )

        # Cow B (ADG 0.5)
        baker.make(
            WeightRecord,
            animal=cow_b,
            session=session_now,
            adg=Decimal("0.500"),
            weight_kg=Decimal("315.00"),
        )

        metrics = get_global_adg_metrics()
        assert metrics["value"] == pytest.approx(0.75)
        assert metrics["status"] == "PROFITABLE"

    def test_filters_out_dead_sold_cattle(self):
        """
        Ensure stats do not include DEAD or SOLD animals even if they had weight records recently.
        """
        active_cow = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)
        sold_cow = baker.make(Cattle, status=Cattle.STATUS_SOLD)

        session = baker.make(WeighingSession, date=timezone.now())

        # Active Cow ADG 1.0
        baker.make(WeightRecord, animal=active_cow, session=session, adg=Decimal("1.0"))
        # Sold Cow ADG 0.2 (Should be ignored)
        baker.make(WeightRecord, animal=sold_cow, session=session, adg=Decimal("0.2"))

        metrics = get_global_adg_metrics()
        assert metrics["value"] == pytest.approx(1.0)  # Only the active one

    def test_status_thresholds(self):
        """
        Test BASIC thresholds: <0.3 (Critical), <0.6 (Maintenance), else Profitable.
        """
        # Critical (< 0.3)
        baker.make(
            WeightRecord,
            adg=Decimal("0.1"),
            animal__status=Cattle.STATUS_AVAILABLE,
            session__date=timezone.now(),
        )
        assert get_global_adg_metrics()["status"] == "CRITICAL"

        # Maintenance (< 0.6)
        WeightRecord.objects.update(adg=Decimal("0.4"))
        assert get_global_adg_metrics()["status"] == "MAINTENANCE"

        # Profitable (>= 0.6)
        WeightRecord.objects.update(adg=Decimal("0.8"))
        assert get_global_adg_metrics()["status"] == "PROFITABLE"

    def test_history_generation(self):
        """
        Verify history list is generated for the sparkline.
        Create records in different weeks.
        """
        cow = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)
        now = timezone.now()

        # Week 1
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("0.5"),
            session__date=now - timedelta(days=20),
        )
        # Week 2
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("0.8"),
            session__date=now - timedelta(days=5),
        )

        metrics = get_global_adg_metrics()
        history = metrics["history"]

        # Should have 2 entries (one per week with data)
        assert len(history) == 2
        assert history[0] == pytest.approx(0.5)
        assert history[1] == pytest.approx(0.8)

    def test_trend_calculation(self):
        """
        Verify UP/DOWN/STABLE trends based on previous period comparison.
        """
        now = timezone.now()
        cow = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)

        # Previous Period (90-180 days ago): Low ADG (0.5)
        # We need records > 90 days ago
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("0.5"),
            session__date=now - timedelta(days=100),
        )

        # Current Period (0-90 days ago): High ADG (0.8) -> Trend UP
        # We need to simulate current calc via creating current records
        # BUT get_global_adg_metrics relies on 'recent_entries' avg
        # Let's create current record
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("0.8"),
            session__date=now - timedelta(days=10),
        )

        metrics = get_global_adg_metrics()
        # Current ~0.8, Prev ~0.5. Diff +0.3 > 0.05 -> UP
        assert metrics["trend"] == "UP"

        # Case 2: DOWN
        # Clear DB
        WeightRecord.objects.all().delete()
        # Prev High (1.0)
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("1.0"),
            session__date=now - timedelta(days=100),
        )
        # Current Low (0.5)
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("0.5"),
            session__date=now - timedelta(days=10),
        )
        metrics = get_global_adg_metrics()
        assert metrics["trend"] == "DOWN"

        # Case 3: STABLE
        WeightRecord.objects.all().delete()
        # Prev 0.5
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("0.5"),
            session__date=now - timedelta(days=100),
        )
        # Current 0.53 (Diff 0.03 < 0.05)
        baker.make(
            WeightRecord,
            animal=cow,
            adg=Decimal("0.53"),
            session__date=now - timedelta(days=10),
        )
        metrics = get_global_adg_metrics()
        assert metrics["trend"] == "STABLE"

    def test_empty_history_fallback(self):
        """
        Test that when there's no ADG history, it returns [0.0] instead of empty list.
        This covers line 94 in analytics.py.
        """
        # Create cattle but NO weight records
        baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)

        metrics = get_global_adg_metrics()

        # Should return empty history with [0.0] fallback
        assert metrics["history"] == [0.0]
        assert metrics["value"] == pytest.approx(0.0)
