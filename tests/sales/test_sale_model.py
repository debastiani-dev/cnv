import pytest
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.partners.models import Partner
from apps.sales.models import Sale, SaleItem


@pytest.mark.django_db
class TestSaleModel:
    def test_create_sale(self):
        partner = baker.make(Partner)
        sale = baker.make(Sale, partner=partner, total_amount=Money("100.00"))

        assert Sale.objects.count() == 1
        assert sale.partner == partner
        assert str(sale) == f"Sale - {partner} - {sale.date}"

    def test_sale_item_polymorphism(self):
        # Create a Cow (Asset)
        cow = baker.make(Cattle, tag="COW-001", name="Bessie")

        # Create a Sale
        sale = baker.make(Sale)

        # Create a SaleItem linked to the Cow
        item = SaleItem.objects.create(
            sale=sale, content_object=cow, quantity=1, unit_price=Money("5000.00")
        )

        assert item.content_object == cow
        assert Money(item.total_price) == Money("5000.00")
        assert str(item) == f"1x {cow} in {sale}"

    def test_sale_item_total_calculation(self):
        sale = baker.make(Sale)
        cow = baker.make(Cattle)

        item = SaleItem(
            sale=sale, content_object=cow, quantity=2.5, unit_price=Money("100.00")
        )
        item.save()

        assert Money(item.total_price) == Money("250.00")
