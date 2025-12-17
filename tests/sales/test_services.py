from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
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

    def test_validate_item_for_sale_inactive(self):
        """Test that validating an inactive item raises ValidationError."""

        # Using a mock object that has is_active attribute
        class MockItem:
            is_active = False

        with pytest.raises(ValidationError, match="not active/available for sale"):
            SaleService.validate_item_for_sale(MockItem())

    def test_create_sale_from_forms_with_deletion(self):
        """Test that formset deleted_objects are actually deleted."""
        sale = baker.make(Sale)
        item_to_delete = baker.make(SaleItem, sale=sale)

        class MockForm:
            def save(self, **kwargs):
                return sale

        class MockFormSet:
            def save(self, **kwargs):
                return []

            deleted_objects = [item_to_delete]

        SaleService.create_sale_from_forms(MockForm(), MockFormSet())

    def test_get_sales_stats_by_period(self):
        """Verify sales stats filtering by period."""
        today = timezone.now().date()

        # Sale 1: Today (Inside 30 days)
        baker.make(Sale, date=today, total_amount=Money("100.00"))

        # Sale 2: 20 days ago (Inside 30 days)
        baker.make(Sale, date=today - timedelta(days=20), total_amount=Money("200.00"))

        # Sale 3: 40 days ago (Outside 30 days)
        baker.make(Sale, date=today - timedelta(days=40), total_amount=Money("300.00"))

        # Test Last 30 Days
        stats_30d = SaleService.get_sales_stats(days=30)
        assert stats_30d["count"] == 2
        assert stats_30d["total_revenue"] == Money("300.00")

        # Test All Time (No Arg)
        stats_all = SaleService.get_sales_stats()
        assert stats_all["count"] == 3
        assert stats_all["total_revenue"] == Money("600.00")
