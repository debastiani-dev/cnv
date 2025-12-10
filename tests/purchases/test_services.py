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

    def test_get_all_purchases_filters(self):
        partner1 = baker.make("partners.Partner", name="Alpha")
        partner2 = baker.make("partners.Partner", name="Beta")
        purchase1 = baker.make(Purchase, partner=partner1, notes="Notes 1")
        purchase2 = baker.make(Purchase, partner=partner2, notes="Notes 2")

        # No filter
        all_purchases = PurchaseService.get_all_purchases()
        assert purchase1 in all_purchases
        assert purchase2 in all_purchases

        # Search filter (name)
        search_results = PurchaseService.get_all_purchases(search_query="Alpha")
        assert purchase1 in search_results
        assert purchase2 not in search_results

        # Search filter (notes)
        search_results_notes = PurchaseService.get_all_purchases(search_query="Notes 2")
        assert purchase2 in search_results_notes
        assert purchase1 not in search_results_notes

        # Partner filter
        partner_results = PurchaseService.get_all_purchases(partner_id=str(partner1.pk))
        assert purchase1 in partner_results
        assert purchase2 not in partner_results

    # Creation from forms is tricky to mock fully without complex form setups,
    # but we can test the specific logic if we extract it or rely on
    # integration tests in test_views.
