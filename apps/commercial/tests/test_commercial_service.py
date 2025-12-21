from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.commercial.models import SalesEvent, SalesLot
from apps.commercial.services import CommercialService
from apps.finance.models.finance import CostEntry
from apps.partners.models import Partner
from apps.transactions.models import Transaction


@pytest.mark.django_db
class TestCommercialService:
    def test_multi_animal_lot_creation(self):
        """
        Test creating a lot with multiple animals and validating cost calculation.
        """
        # 1. Create Event
        event = baker.make(SalesEvent, name="Spring Auction")

        # 2. Create 5 Steers and assign costs
        steers = baker.make(Cattle, _quantity=5, status=Cattle.STATUS_AVAILABLE)

        # Create Cost Entries (e.g. Purchase Cost)
        for steer in steers:
            baker.make(
                CostEntry,
                animal=steer,
                amount=Decimal("1000.00"),
                date=timezone.now().date(),
            )

        initial_cost_sum = sum(s.total_cost for s in steers)

        # 3. Create Lot
        lot = SalesLot.objects.create(
            event=event,
            lot_number=1,
            cost_at_creation=initial_cost_sum,
            reserve_price=Decimal("15000.00"),
        )
        lot.animals.set(steers)

        # Assertions
        assert lot.animals.count() == 5
        assert lot.cost_at_creation == initial_cost_sum
        assert lot.status == SalesLot.STATUS_AVAILABLE

    def test_calculate_lot_cost_returns_money(self):
        """Test that calculate_lot_cost returns a Money instance."""
        steers = baker.make(Cattle, _quantity=2)
        baker.make(CostEntry, animal=steers[0], amount=Decimal("100.00"))
        baker.make(CostEntry, animal=steers[1], amount=Decimal("200.00"))

        total = CommercialService.calculate_lot_cost(steers)

        assert isinstance(total, Money)
        assert total == Money("300.00")

    def test_closing_multi_animal_lot(self):
        """
        Test closing a lot moves animals to SOLD and creates TransactionItem.
        """
        event = baker.make(SalesEvent)
        buyer = baker.make(Partner)
        steers = baker.make(Cattle, _quantity=5, status=Cattle.STATUS_AVAILABLE)

        lot = baker.make(
            SalesLot, event=event, lot_number=1, status=SalesLot.STATUS_AVAILABLE
        )
        lot.animals.set(steers)

        hammer_price = Decimal("20000.00")
        sale_date = timezone.localdate()

        # Action
        invoice = CommercialService.close_lot(lot, buyer, hammer_price, sale_date)

        # Assertions
        # 1. Lot Status
        lot.refresh_from_db()
        assert lot.status == SalesLot.STATUS_SOLD

        # 2. Animals Status
        for steer in steers:
            steer.refresh_from_db()
            assert steer.status == Cattle.STATUS_SOLD

        # 3. Transaction/Invoice
        assert invoice.partner == buyer
        assert invoice.date == sale_date
        assert invoice.status == Transaction.STATUS_DRAFT
        assert invoice.items.count() == 1

        # 4. Transaction Item
        item = invoice.items.first()
        assert item.content_object == lot
        assert item.unit_price == hammer_price
        assert item.quantity == 1
        assert invoice.total_amount == hammer_price

    def test_invoice_grouping(self):
        """
        Test that multiple lots bought by same partner on same day are grouped into one Invoice.
        """
        event = baker.make(SalesEvent)
        buyer = baker.make(Partner)
        date = timezone.localdate()

        lot1 = baker.make(
            SalesLot, event=event, lot_number=1, status=SalesLot.STATUS_AVAILABLE
        )
        lot2 = baker.make(
            SalesLot, event=event, lot_number=2, status=SalesLot.STATUS_AVAILABLE
        )

        # Buy Lot 1
        invoice1 = CommercialService.close_lot(lot1, buyer, Decimal("10000.00"), date)

        # Buy Lot 2
        invoice2 = CommercialService.close_lot(lot2, buyer, Decimal("15000.00"), date)

        # Assertions
        invoice1.refresh_from_db()  # Refresh to get updated total and items count
        assert invoice1.pk == invoice2.pk  # Same Invoice
        assert invoice1.items.count() == 2
        assert invoice1.total_amount == Decimal("25000.00")

    def test_close_lot_unavailable_validation(self):
        """Test validation error when closing an unavailable lot."""
        lot = baker.make(SalesLot, status=SalesLot.STATUS_SOLD)
        buyer = baker.make(Partner)

        with pytest.raises(ValidationError, match="not available"):
            CommercialService.close_lot(
                lot, buyer, Decimal("100.00"), timezone.localdate()
            )
