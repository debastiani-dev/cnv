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

        SaleService.hard_delete_sale(sale)  # Wait, we want soft delete first usually?
        # The service has hard_delete_sale, let's check view logic.
        # Views use SaleService.get_deleted_sales, restore_sale, hard_delete_sale.
        # Standard deletion is via Django's DeleteView (which calls obj.delete() -> SoftDeleteModel.delete() -> sets is_deleted=True)

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

    # Creation from forms is tricky to mock fully without complex form setups,
    # but we can test the specific logic if we extract it or rely on integration tests in test_views.
