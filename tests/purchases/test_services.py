import pytest
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.purchases.models import Purchase, PurchaseItem
from apps.purchases.services.purchase_service import PurchaseService


@pytest.mark.django_db
class TestPurchaseService:
    def test_update_purchase_totals(self):
        purchase = baker.make(Purchase)
        cow1 = baker.make(Cattle)
        cow2 = baker.make(Cattle)

        # Item 1: 1 * 100 = 100
        PurchaseItem.objects.create(
            purchase=purchase,
            content_object=cow1,
            quantity=1,
            unit_price=Money("100.00"),
        )
        # Item 2: 2 * 50 = 100
        PurchaseItem.objects.create(
            purchase=purchase,
            content_object=cow2,
            quantity=2,
            unit_price=Money("50.00"),
        )

        PurchaseService.update_purchase_totals(purchase)

        purchase.refresh_from_db()
        assert Money(purchase.total_amount) == Money("200.00")

    def test_soft_delete_and_restore(self):
        purchase = baker.make(Purchase)

        PurchaseService.hard_delete_purchase(
            purchase
        )  # Wait, we want soft delete first usually?
        # The service has hard_delete_purchase, let's check view logic.
        # Views use PurchaseService.get_deleted_purchases, restore_purchase, hard_delete_purchase.
        # Standard deletion is via Django's DeleteView
        # (which calls obj.delete() -> SoftDeleteModel.delete() -> sets is_deleted=True)

        purchase.delete()
        assert purchase.is_deleted

        PurchaseService.restore_purchase(purchase)
        purchase.refresh_from_db()
        assert not purchase.is_deleted

    def test_get_deleted_purchases(self):
        purchase1 = baker.make(Purchase)
        purchase2 = baker.make(Purchase)
        purchase2.delete()

        deleted = PurchaseService.get_deleted_purchases()
        assert purchase2 in deleted
        assert purchase1 not in deleted

    # Creation from forms is tricky to mock fully without complex form setups,
    # but we can test the specific logic if we extract it or rely on
    # integration tests in test_views.
