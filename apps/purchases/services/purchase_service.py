from django.db import transaction
from django.db.models import Sum

from apps.base.utils.money import Money
from apps.purchases.models import Purchase, PurchaseItem


class PurchaseService:
    @staticmethod
    def get_purchases_stats() -> dict:
        """
        Returns statistics about purchases.
        """
        queryset = Purchase.objects.all()
        total_count = queryset.count()
        total_cost = queryset.aggregate(total=Sum("total_amount"))["total"] or 0
        recent_purchases = queryset.order_by("-date", "-created_at")[:5]

        return {
            "count": total_count,
            "total_cost": total_cost,
            "recent": recent_purchases,
        }

    @staticmethod
    @transaction.atomic
    def create_purchase(
        purchase_instance: Purchase, purchase_items_data: list[PurchaseItem]
    ) -> Purchase:
        """
        Creates a Purchase and its Items, updating totals.
        """
        # Save the purchase first to get a PK
        purchase_instance.save()

        total_amount = Money(0)

        for item in purchase_items_data:
            item.purchase = purchase_instance
            item.save()  # formatting and total_price calc happens in model save
            # money library handles addition, but mypy might not know __add__ returns Money
            total_amount += Money(item.total_price)  # type: ignore

        purchase_instance.total_amount = total_amount
        purchase_instance.save()

        return purchase_instance

    @staticmethod
    @transaction.atomic
    def update_purchase_totals(purchase: Purchase) -> None:
        """
        Recalculates and updates the total amount for a purchase.
        """
        # Use aggregation or python loop. Python loop is safer with Money class precision
        # though DB aggregation is faster. Given Money logic in app, let's use app logic.
        items = purchase.items.all()  # type: ignore
        total = Money(0)
        for item in items:
            total += Money(item.total_price)  # type: ignore

        purchase.total_amount = total
        purchase.save()

    @staticmethod
    @transaction.atomic
    def create_purchase_from_forms(form, formset) -> Purchase:
        """
        Orchestrates creation from Django Forms.
        """
        purchase = form.save(commit=False)
        purchase.save()  # Get PK

        # Save formset items
        instances = formset.save(commit=False)
        for instance in instances:
            instance.purchase = purchase
            instance.save()

        # Handle deletions
        for obj in formset.deleted_objects:
            obj.delete()

        PurchaseService.update_purchase_totals(purchase)
        return purchase

    @staticmethod
    def get_deleted_purchases():
        """
        Returns a queryset of soft-deleted purchases.
        """
        return Purchase.all_objects.filter(is_deleted=True).order_by("-date")

    @staticmethod
    def restore_purchase(purchase: Purchase) -> None:
        """
        Restores a soft-deleted purchase.
        """
        purchase.restore()

    @staticmethod
    def hard_delete_purchase(purchase: Purchase) -> None:
        """
        Permanently deletes a purchase.
        """
        purchase.delete(destroy=True)
