from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.cattle.models import Cattle
from apps.health.services import HealthService
from apps.nutrition.models.ingredient import FeedIngredient
from apps.transactions.models.transaction import Transaction


class TransactionService:
    @staticmethod
    def get_stats(days: int | None = None, transaction_type: str | None = None) -> dict:
        """
        Returns unified statistics for Transactions.
        """
        queryset = Transaction.objects.filter(status=Transaction.STATUS_CONFIRMED)
        if days:
            cutoff_date = timezone.now().date() - timedelta(days=days)
            queryset = queryset.filter(date__gte=cutoff_date)

        if transaction_type:
            queryset = queryset.filter(type=transaction_type)

        # Sales Stats
        sales = queryset.filter(type=Transaction.TYPE_SALE)
        sales_count = sales.count()
        total_revenue = sales.aggregate(total=Sum("total_amount"))["total"] or 0

        # Purchase Stats
        purchases = queryset.filter(type=Transaction.TYPE_PURCHASE)
        purchases_count = purchases.count()
        total_expense = purchases.aggregate(total=Sum("total_amount"))["total"] or 0

        # Calculations
        net_profit = total_revenue - total_expense

        return {
            "sales_count": sales_count,
            "purchases_count": purchases_count,
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "net_profit": net_profit,
            "recent": queryset.order_by("-date", "-created_at")[:5],
        }

    @staticmethod
    def get_all_transactions(
        search_query: str | None = None,
        partner_id: str | None = None,
        transaction_type: str | None = None,
    ):
        """
        Returns a filtered queryset of transactions.
        """
        queryset = (
            Transaction.objects.all()
            .select_related("partner")
            .prefetch_related("items")
        )

        if search_query:
            queryset = queryset.filter(
                partner__name__icontains=search_query
            ) | queryset.filter(notes__icontains=search_query)

        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)

        if transaction_type:
            queryset = queryset.filter(type=transaction_type)

        return queryset.order_by("-date", "-created_at")

    @staticmethod
    def validate_item_for_sale(item_object):
        """
        Performs checks to ensure an item is sellable.
        1. Is it active?
        2. Is it biologically safe? (Cattle Withdrawal)
        """
        # Specific Logic for Cattle
        if isinstance(item_object, Cattle):
            if item_object.status != Cattle.STATUS_AVAILABLE:
                raise ValidationError(
                    _("Cattle is not available for sale (Status: %(status)s)")
                    % {"status": item_object.get_status_display()}
                )

            # Biological Safety Valve (Cattle Only)
            is_blocked, reason = HealthService.check_withdrawal_status(item_object)
            if is_blocked:
                raise ValidationError(
                    _("Sanitary Block: %(reason)s") % {"reason": reason}
                )

        # General Logic for other items
        elif hasattr(item_object, "is_active") and not item_object.is_active:
            raise ValidationError(_("This item is not active/available for sale."))

        return True

    @staticmethod
    @transaction.atomic
    def confirm_transaction(transaction_instance: Transaction) -> None:
        """
        Confirms a transaction and executes side effects (Integrations).
        """
        if transaction_instance.status == Transaction.STATUS_CONFIRMED:
            return  # Already confirmed

        # validate items before confirming
        TransactionService._validate_transaction_items(transaction_instance)

        # Execute Integrations
        TransactionService._execute_transaction_integrations(transaction_instance)

        # Finalize Header
        transaction_instance.status = Transaction.STATUS_CONFIRMED
        transaction_instance.save(update_fields=["status"])

    @staticmethod
    def _validate_transaction_items(transaction_instance: Transaction) -> None:
        """Validates all items in the transaction."""
        for item in transaction_instance.items.all():  # type: ignore
            if transaction_instance.type == Transaction.TYPE_SALE:
                if item.content_object:
                    TransactionService.validate_item_for_sale(item.content_object)

    @staticmethod
    def _execute_transaction_integrations(transaction_instance: Transaction) -> None:
        """Executes side effects for each item."""
        for item in transaction_instance.items.all():  # type: ignore
            content_object = item.content_object

            # 1. SALE -> Cattle Integration
            if transaction_instance.type == Transaction.TYPE_SALE:
                if isinstance(content_object, Cattle):
                    content_object.status = Cattle.STATUS_SOLD
                    content_object.save(update_fields=["status"])

            # 2. PURCHASE -> Feed/Inventory Integration
            elif transaction_instance.type == Transaction.TYPE_PURCHASE:
                if isinstance(content_object, FeedIngredient):
                    TransactionService._update_inventory_wac(
                        content_object, item.quantity, item.unit_price
                    )

    @staticmethod
    def _update_inventory_wac(ingredient, new_qty, new_cost):
        """Calculates and updates Weighted Average Cost."""
        current_qty = ingredient.stock_quantity
        current_cost = ingredient.unit_cost

        total_qty = current_qty + new_qty

        if total_qty > 0:
            new_avg_cost = (
                (current_qty * current_cost) + (new_qty * new_cost)
            ) / total_qty
            ingredient.unit_cost = new_avg_cost

        ingredient.stock_quantity = total_qty
        ingredient.save(update_fields=["stock_quantity", "unit_cost"])
