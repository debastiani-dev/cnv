import pytest
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.purchases.models import Purchase, PurchaseItem


@pytest.mark.django_db
class TestPurchaseModel:
    def test_purchase_creation(self):
        purchase = baker.make(Purchase)
        assert purchase.pk is not None

    def test_purchase_item_creation(self):
        # Create a purchase
        purchase = baker.make(Purchase)
        # Create a Cow (Asset)
        cow = baker.make(Cattle, tag="COW-001", name="Bessie")

        # Create a PurchaseItem linked to the Cow
        item = PurchaseItem.objects.create(
            purchase=purchase,
            content_object=cow,
            quantity=1,
            unit_price=Money("5000.00"),
        )

        assert item.content_object == cow
        assert Money(item.total_price) == Money("5000.00")
        assert str(item) == f"1x {cow} in {purchase}"

    def test_purchase_item_total_calculation(self):
        purchase = baker.make(Purchase)
        cow = baker.make(Cattle)

        item = PurchaseItem(
            purchase=purchase,
            content_object=cow,
            quantity=2.5,
            unit_price=Money("100.00"),
        )
        item.save()

        assert Money(item.total_price) == Money("250.00")
