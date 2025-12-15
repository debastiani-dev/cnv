from decimal import Decimal

import pytest
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.locations.models import Location
from apps.locations.services.analytics import get_stocking_rate_metrics


@pytest.mark.django_db
class TestStockingRate:
    def test_stocking_calculation_basic(self):
        """
        Test that 10 cows (4500kg total) on 10ha pasture results in 1.0 AU/ha.
        (4500kg / 450kg/AU) = 10 AU.
        10 AU / 10 ha = 1.0 AU/ha.
        """
        # Create Pasture
        pasture = baker.make(
            Location, type="PASTURE", area_hectares=Decimal("10.00"), is_active=True
        )

        # Create 10 Cows, each 450kg
        baker.make(
            Cattle,
            _quantity=10,
            current_weight=Decimal("450.00"),
            location=pasture,
            status=Cattle.STATUS_AVAILABLE,
        )

        metrics = get_stocking_rate_metrics()

        assert metrics["rate"] == 1.0
        assert metrics["total_au"] == 10
        assert metrics["total_area"] == 10
        assert metrics["status"] == "OPTIMAL"

    def test_empty_pasture(self):
        """Test with no animals."""
        baker.make(
            Location, type="PASTURE", area_hectares=Decimal("10.00"), is_active=True
        )
        metrics = get_stocking_rate_metrics()

        assert metrics["rate"] == 0.0
        assert metrics["total_au"] == 0
        assert metrics["status"] == "UNDERSTOCKED"

    def test_zero_area_pasture(self):
        """Test division by zero safety (though model should prevent 0 area, we handle it)."""
        # No active pastures
        Location.objects.all().delete()

        metrics = get_stocking_rate_metrics()

        # Should default area to 1.00 to avoid div/0, resulting in 0 rate if no cattle
        assert metrics["total_area"] == 1
        assert metrics["rate"] == 0.0

    def test_ignores_non_pasture_animals(self):
        """Ensure animals in Feedlot are not counted for Stocking Rate (Pasture-based)."""
        pasture = baker.make(
            Location, type="PASTURE", area_hectares=Decimal("10.00"), is_active=True
        )
        feedlot = baker.make(
            Location, type="FEEDLOT", area_hectares=Decimal("5.00"), is_active=True
        )

        # 5 Cows in Pasture (2250kg -> 5 AU)
        baker.make(
            Cattle,
            _quantity=5,
            current_weight=Decimal("450.00"),
            location=pasture,
            status=Cattle.STATUS_AVAILABLE,
        )

        # 5 Cows in Feedlot (2250kg -> 5 AU) - Should be ignored
        baker.make(
            Cattle,
            _quantity=5,
            current_weight=Decimal("450.00"),
            location=feedlot,
            status=Cattle.STATUS_AVAILABLE,
        )

        metrics = get_stocking_rate_metrics()

        # Should only count pasture animals (5 AU) on pasture area (10 ha) -> 0.5 AU/ha
        assert metrics["total_au"] == 5
        assert (
            metrics["total_area"] == 10
        )  # 10 pasture, 5 feedlot (feedlot area not counted in implementation? check code)
        # Check implementation: Location.objects.filter(type="PASTURE", ...)
        # So yes, feedlot area is ignored.
        assert metrics["rate"] == 0.5

    def test_rate_status_thresholds(self):
        """Test status strings based on rate."""
        # 1. Overstocked: 20 cows (9000kg -> 20 AU) on 10ha -> 2.0 AU/ha
        pasture = baker.make(
            Location, type="PASTURE", area_hectares=Decimal("10.00"), is_active=True
        )
        baker.make(
            Cattle,
            _quantity=20,
            current_weight=Decimal("450.00"),
            location=pasture,
            status=Cattle.STATUS_AVAILABLE,
        )
        metrics = get_stocking_rate_metrics()
        assert metrics["rate"] == 2.0
        assert metrics["status"] == "OVERSTOCKED"

        # 2. Understocked (<0.5): 4 cows (1800kg -> 4 AU) on 10ha -> 0.4 AU/ha
        Cattle.objects.all().delete()
        baker.make(
            Cattle,
            _quantity=4,
            current_weight=Decimal("450.00"),
            location=pasture,
            status=Cattle.STATUS_AVAILABLE,
        )
        metrics = get_stocking_rate_metrics()
        assert metrics["rate"] == 0.4
        assert metrics["status"] == "UNDERSTOCKED"
