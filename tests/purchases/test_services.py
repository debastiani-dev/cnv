from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.nutrition.models import FeedIngredient
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

    def test_create_purchase_from_forms_inventory_math(self):
        """Test that purchasing ingredients updates stock and calculates WAC correctly."""
        # Initial State: 10 units @ $10.00
        ingredient = baker.make(
            FeedIngredient, stock_quantity=Decimal("10.00"), unit_cost=Decimal("10.00")
        )

        partner = baker.make("partners.Partner")
        # Pre-create purchase to return in form save
        # We need commit=False simulation but let's keep it simple
        purchase = baker.make(Purchase, partner=partner)

        class MockForm:
            def save(self, commit=True):
                # pylint: disable=unused-argument
                return purchase

        class MockFormSet:
            def save(self, commit=True):
                # pylint: disable=unused-argument
                # Return list of dummy items that are not yet saved to DB fully or detached
                # The service saves them.
                # ContentType and ObjectID must be set for GFK
                ct = ContentType.objects.get_for_model(FeedIngredient)

                # Mock instance needs to look like PurchaseItem but be unsaved?
                # Service calls save() on them.
                # Baker makes saved instances by default.
                # Let's instantiate manually.
                item = PurchaseItem(
                    purchase=purchase,
                    content_type=ct,
                    object_id=ingredient.pk,
                    quantity=Decimal("10.00"),
                    unit_price=Decimal("20.00"),
                )
                # Important: GFK needs to be accessable?
                # Django GFK might not resolve on unsaved instance unless content_object set
                item.content_object = ingredient

                return [item]

            deleted_objects = []

        PurchaseService.create_purchase_from_forms(MockForm(), MockFormSet())

        ingredient.refresh_from_db()
        # Original: 10 @ 10 = 100
        # New: 10 @ 20 = 200
        # Total: 20 @ 300 val -> 15 cost
        assert ingredient.stock_quantity == Decimal("20.00")
        assert ingredient.unit_cost == Decimal("15.00")

        purchase.refresh_from_db()
        assert purchase.total_amount == Decimal("200.00")

    def test_create_purchase_direct(self):
        """Test create_purchase method (direct usage)."""
        purchase = baker.make(Purchase, total_amount=Decimal("0.00"))
        ingredient = baker.make(FeedIngredient)

        # Item to be created
        item = PurchaseItem(
            purchase=purchase,
            content_object=ingredient,
            quantity=Decimal("5.00"),
            unit_price=Decimal("10.00"),
            content_type=ContentType.objects.get_for_model(FeedIngredient),
            object_id=ingredient.pk,
        )

        PurchaseService.create_purchase(purchase, [item])

        purchase.refresh_from_db()
        assert purchase.total_amount == Decimal("50.00")
        assert purchase.items.count() == 1
        assert purchase.items.first().content_object == ingredient

    def test_create_purchase_from_forms_with_deletion(self):
        """Test that formset deleted_objects are actually deleted."""
        purchase = baker.make(Purchase)
        item_to_delete = baker.make(PurchaseItem, purchase=purchase)

        class MockForm:
            def save(self, commit=True):
                # pylint: disable=unused-argument
                return purchase

        class MockFormSet:
            def save(self, commit=True):
                # pylint: disable=unused-argument
                return []

            deleted_objects = [item_to_delete]

        PurchaseService.create_purchase_from_forms(MockForm(), MockFormSet())

        assert not PurchaseItem.objects.filter(pk=item_to_delete.pk).exists()
