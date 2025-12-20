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
    def get_stats(days: int | None = None) -> dict:
        """
        Returns unified statistics for Transactions.
        """
        queryset = Transaction.objects.filter(status=Transaction.STATUS_CONFIRMED)
        if days:
            cutoff_date = timezone.now().date() - timedelta(days=days)
            queryset = queryset.filter(date__gte=cutoff_date)

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
    def validate_item_for_sale(item_object):
        """
        Performs checks to ensure an item is sellable.
        1. Is it active?
        2. Is it biologically safe? (Cattle Withdrawal)
        """
        if hasattr(item_object, "is_active") and not item_object.is_active:
            # If it's cattle, status SOLD or DEAD means inactive usually.
            # But let's check specifically if it is Cattle and status.
            if isinstance(item_object, Cattle):
                if item_object.status != Cattle.STATUS_AVAILABLE:
                    raise ValidationError(
                        _("Cattle is not available for sale (Status: %(status)s)")
                        % {"status": item_object.get_status_display()}
                    )
            else:
                raise ValidationError(_("This item is not active/available for sale."))

        # Biological Safety Valve (Cattle Only)
        if isinstance(item_object, Cattle):
            is_blocked, reason = HealthService.check_withdrawal_status(item_object)
            if is_blocked:
                raise ValidationError(
                    _("Sanitary Block: %(reason)s") % {"reason": reason}
                )

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
        for item in transaction_instance.items.all():
            if transaction_instance.type == Transaction.TYPE_SALE:
                if item.content_object:
                    TransactionService.validate_item_for_sale(item.content_object)

        # Execute Integrations
        for item in transaction_instance.items.all():
            content_object = item.content_object

            # 1. SALE -> Cattle Integration
            if transaction_instance.type == Transaction.TYPE_SALE:
                if isinstance(content_object, Cattle):
                    content_object.status = Cattle.STATUS_SOLD
                    content_object.save(update_fields=["status"])

            # 2. PURCHASE -> Feed/Inventory Integration
            elif transaction_instance.type == Transaction.TYPE_PURCHASE:
                if isinstance(content_object, FeedIngredient):
                    # Weighted Average Cost (WAC) Logic
                    # New Cost = ( (OldQty * OldCost) + (NewQty * NewCost) ) / (OldQty + NewQty)

                    current_qty = content_object.stock_quantity
                    current_cost = content_object.unit_cost
                    new_qty = item.quantity
                    new_cost = item.unit_price

                    total_qty = current_qty + new_qty

                    if total_qty > 0:
                        new_avg_cost = (
                            (current_qty * current_cost) + (new_qty * new_cost)
                        ) / total_qty
                        content_object.unit_cost = new_avg_cost

                    content_object.stock_quantity = total_qty
                    content_object.save(update_fields=["stock_quantity", "unit_cost"])

        # Finalize Header
        transaction_instance.status = Transaction.STATUS_CONFIRMED
        transaction_instance.save(update_fields=["status"])
