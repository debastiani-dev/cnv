from decimal import Decimal

import pytest
from django.db.utils import IntegrityError
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.commercial.models import SalesEvent, SalesLot


@pytest.mark.django_db
class TestSalesEvent:
    def test_str_representation(self):
        """Test the string representation of SalesEvent."""
        event = baker.make(SalesEvent, name="Fall Auction", date="2024-10-15")
        # String format: f"{self.name} ({self.date})" uses default date str implementation
        assert str(event) == "Fall Auction (2024-10-15)"


@pytest.mark.django_db
class TestSalesLot:
    def test_str_representation(self):
        """Test the string representation of SalesLot."""
        event = baker.make(SalesEvent, name="Spring Sale")
        lot = baker.make(SalesLot, event=event, lot_number=10)
        assert str(lot) == "Lot 10 (Spring Sale)"

    def test_default_status(self):
        """Test default status is AVAILABLE."""
        lot = baker.make(SalesLot)
        assert lot.status == SalesLot.STATUS_AVAILABLE

    def test_unique_lot_number_per_event(self):
        """Test that lot number must be unique within an event."""
        event = baker.make(SalesEvent)
        baker.make(SalesLot, event=event, lot_number=1)

        with pytest.raises(IntegrityError):
            baker.make(SalesLot, event=event, lot_number=1)

    def test_average_weight_calculation(self):
        """Test average weight property calculation."""
        lot = baker.make(SalesLot)

        # 1. Zero animals
        assert lot.average_weight == 0

        # 2. One animal
        cow1 = baker.make(Cattle, current_weight=Decimal("500.00"))
        lot.animals.add(cow1)
        # Re-fetch or just call property (it queries DB relation)
        assert lot.average_weight == Decimal("500.0")

        # 3. Multiple animals
        cow2 = baker.make(Cattle, current_weight=Decimal("600.00"))
        lot.animals.add(cow2)

        # (500 + 600) / 2 = 550
        assert lot.average_weight == Decimal("550.0")

    def test_average_weight_rounding(self):
        """Test average weight is rounded to 1 decimal place."""
        lot = baker.make(SalesLot)
        # 100 / 3 = 33.333...
        cows = [
            baker.make(Cattle, current_weight=Decimal("33.33")),
            baker.make(Cattle, current_weight=Decimal("33.33")),
            baker.make(Cattle, current_weight=Decimal("33.34")),
        ]
        lot.animals.set(cows)

        # Sum = 100.00. Count = 3. Avg = 33.3333
        assert lot.average_weight == Decimal("33.3")
