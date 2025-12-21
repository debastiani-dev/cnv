from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.nutrition.models import FeedIngredient
from apps.transactions.models import Transaction, TransactionItem
from apps.transactions.services.transaction_service import TransactionService


@pytest.mark.django_db
class TestTransactionService:
    def test_update_totals(self):
        transaction = baker.make(Transaction, type=Transaction.TYPE_SALE)
        cow1 = baker.make(Cattle)
        cow2 = baker.make(Cattle)

        # Item 1: 1 * 100 = 100
        TransactionItem.objects.create(
            transaction=transaction,
            content_object=cow1,
            quantity=1,
            unit_price=Money("100.00"),
        )
        # Item 2: 2 * 50 = 100
        TransactionItem.objects.create(
            transaction=transaction,
            content_object=cow2,
            quantity=2,
            unit_price=Money("50.00"),
        )

        transaction.update_total()
        transaction.refresh_from_db()
        assert Money(transaction.total_amount) == Money("200.00")

    def test_soft_delete_and_restore(self):
        transaction = baker.make(Transaction)

        transaction.delete()
        assert transaction.is_deleted

        transaction.restore()
        transaction.refresh_from_db()
        assert not transaction.is_deleted

    def test_get_all_transactions_filters(self):
        partner1 = baker.make("partners.Partner", name="Alpha")
        partner2 = baker.make("partners.Partner", name="Beta")

        tx_sale = baker.make(
            Transaction, partner=partner1, type=Transaction.TYPE_SALE, notes="Notes 1"
        )
        tx_purchase = baker.make(
            Transaction,
            partner=partner2,
            type=Transaction.TYPE_PURCHASE,
            notes="Notes 2",
        )

        # No filter
        all_tx = TransactionService.get_all_transactions()
        assert tx_sale in all_tx
        assert tx_purchase in all_tx

        # Type filter
        sales_only = TransactionService.get_all_transactions(
            transaction_type=Transaction.TYPE_SALE
        )
        assert tx_sale in sales_only
        assert tx_purchase not in sales_only

        # Search filter (name)
        search_results = TransactionService.get_all_transactions(search_query="Alpha")
        assert tx_sale in search_results
        assert tx_purchase not in search_results

        # Search filter (notes)
        search_results_notes = TransactionService.get_all_transactions(
            search_query="Notes 2"
        )
        assert tx_purchase in search_results_notes
        assert tx_sale not in search_results_notes

        # Partner filter
        partner_results = TransactionService.get_all_transactions(
            partner_id=str(partner1.pk)
        )
        assert tx_sale in partner_results
        assert tx_purchase not in partner_results

    def test_purchase_inventory_math(self):
        """Test that purchasing ingredients updates stock and calculates WAC correctly."""
        # Initial State: 10 units @ $10.00
        ingredient = baker.make(
            FeedIngredient, stock_quantity=Decimal("10.00"), unit_cost=Decimal("10.00")
        )

        # Create confirmed purchase
        # In the new system, we usually create DRAFT then CONFIRM.
        # But if the service handles confirmation logic from forms, we test that or confirm_transaction method.
        # Assuming confirm_transaction is the key method for side effects.

        purchase = baker.make(
            Transaction, type=Transaction.TYPE_PURCHASE, status=Transaction.STATUS_DRAFT
        )

        TransactionItem.objects.create(
            transaction=purchase,
            content_object=ingredient,
            quantity=Decimal("10.00"),
            unit_price=Decimal("20.00"),
        )
        purchase.update_total()

        # Execute confirmation
        TransactionService.confirm_transaction(purchase)

        ingredient.refresh_from_db()
        # Original: 10 @ 10 = 100
        # New: 10 @ 20 = 200
        # Total: 20 @ 300 val -> 15 cost
        assert ingredient.stock_quantity == Decimal("20.00")
        assert ingredient.unit_cost == Decimal("15.00")
        assert purchase.status == Transaction.STATUS_CONFIRMED

    def test_validate_item_for_sale_inactive(self):
        """Test that validating an inactive item for SALE raises ValidationError."""

        # 1. Non-Cattle Inactive
        class MockItem:
            is_active = False
            pk = 1

        with pytest.raises(ValidationError, match="not active/available"):
            TransactionService.validate_item_for_sale(MockItem())

    def test_validate_item_for_sale_cattle_unavailable(self):
        """Test Cattle status validation."""
        # Cattle not AVAILABLE
        cow = baker.make(Cattle, status=Cattle.STATUS_SOLD)

        with pytest.raises(ValidationError, match="Cattle is not available"):
            TransactionService.validate_item_for_sale(cow)

    def test_validate_item_sanitary_block(self):
        """Test sanitary block (line 102)."""
        cow = baker.make(Cattle)
        with patch(
            "apps.transactions.services.transaction_service.HealthService.check_withdrawal_status",
            return_value=(True, "Blocked"),
        ):
            with pytest.raises(ValidationError, match="Sanitary Block: Blocked"):
                TransactionService.validate_item_for_sale(cow)

    def test_confirm_transaction_already_confirmed(self):
        """Test early return if already confirmed (line 115)."""
        tx = baker.make(Transaction, status=Transaction.STATUS_CONFIRMED)

        with patch.object(
            TransactionService, "_validate_transaction_items"
        ) as mock_val:
            TransactionService.confirm_transaction(tx)
            mock_val.assert_not_called()

    def test_get_stats_by_period_and_type(self):
        """Verify stats filtering."""
        today = timezone.now().date()

        # Sale Today: 100
        baker.make(
            Transaction,
            type=Transaction.TYPE_SALE,
            date=today,
            total_amount=Money("100.00"),
            status=Transaction.STATUS_CONFIRMED,
        )

        # Purchase Today: 50
        baker.make(
            Transaction,
            type=Transaction.TYPE_PURCHASE,
            date=today,
            total_amount=Money("50.00"),
            status=Transaction.STATUS_CONFIRMED,
        )

        # Old Sale: 200 (20 days ago)
        baker.make(
            Transaction,
            type=Transaction.TYPE_SALE,
            date=today - timedelta(days=20),
            total_amount=Money("200.00"),
            status=Transaction.STATUS_CONFIRMED,
        )

        # Test Last 30 Days Sales
        stats_sales = TransactionService.get_stats(
            transaction_type=Transaction.TYPE_SALE, days=30
        )
        assert stats_sales["sales_count"] == 2
        assert stats_sales["total_revenue"] == Money("300.00")

        # Test Last 30 Days Purchases
        stats_purchases = TransactionService.get_stats(
            transaction_type=Transaction.TYPE_PURCHASE, days=30
        )
        assert stats_purchases["purchases_count"] == 1
        assert stats_purchases["total_expense"] == Money("50.00")
