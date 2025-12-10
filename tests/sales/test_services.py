import pytest
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.sales.models import Sale, SaleItem
from apps.sales.services.sale_service import SaleService


@pytest.mark.django_db
class TestSaleService:
    def test_update_sale_totals(self):
        sale = baker.make(Sale)
        cow1 = baker.make(Cattle)
        cow2 = baker.make(Cattle)

        # Item 1: 1 * 100 = 100
        SaleItem.objects.create(
            sale=sale, content_object=cow1, quantity=1, unit_price=Money("100.00")
        )
        # Item 2: 2 * 50 = 100
        SaleItem.objects.create(
            sale=sale, content_object=cow2, quantity=2, unit_price=Money("50.00")
        )

        SaleService.update_sale_totals(sale)

        sale.refresh_from_db()
        assert Money(sale.total_amount) == Money("200.00")

    def test_soft_delete_and_restore(self):
        sale = baker.make(Sale)

        sale.delete()
        assert sale.is_deleted

        SaleService.restore_sale(sale)
        sale.refresh_from_db()
        assert not sale.is_deleted

    def test_get_deleted_sales(self):
        sale1 = baker.make(Sale)
        sale2 = baker.make(Sale)
        sale2.delete()

        deleted = SaleService.get_deleted_sales()
        assert sale2 in deleted
        assert sale1 not in deleted

    def test_get_all_sales_filters(self):
        partner1 = baker.make("partners.Partner", name="Alpha")
        partner2 = baker.make("partners.Partner", name="Beta")
        sale1 = baker.make(Sale, partner=partner1, notes="Notes 1")
        sale2 = baker.make(Sale, partner=partner2, notes="Notes 2")

        # No filter
        all_sales = SaleService.get_all_sales()
        assert sale1 in all_sales
        assert sale2 in all_sales

        # Search filter (name)
        search_results = SaleService.get_all_sales(search_query="Alpha")
        assert sale1 in search_results
        assert sale2 not in search_results

        # Search filter (notes)
        search_results_notes = SaleService.get_all_sales(search_query="Notes 2")
        assert sale2 in search_results_notes
        assert sale1 not in search_results_notes

        # Partner filter
        partner_results = SaleService.get_all_sales(partner_id=str(partner1.pk))
        assert sale1 in partner_results
        assert sale2 not in partner_results

    # Creation from forms is tricky to mock fully without complex form setups,
    # but we can test the specific logic if we extract it or rely on
    # integration tests in test_views.
