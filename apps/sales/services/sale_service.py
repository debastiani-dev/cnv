# pylint: disable=duplicate-code
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils.translation import gettext_lazy as _

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.health.services import HealthService
from apps.sales.models import Sale, SaleItem


class SaleService:
    @staticmethod
    def get_sales_stats() -> dict:
        """
        Returns statistics about sales.
        """
        queryset = Sale.objects.all()
        total_count = queryset.count()
        total_revenue = queryset.aggregate(total=Sum("total_amount"))["total"] or 0
        recent_sales = queryset.order_by("-date", "-created_at")[:5]

        return {
            "count": total_count,
            "total_revenue": total_revenue,
            "recent": recent_sales,
        }

    @staticmethod
    def get_all_sales(search_query: str | None = None, partner_id: str | None = None):
        """
        Returns all sales, optionally filtered by search query and partner.
        """
        queryset = (
            Sale.objects.all()
            .select_related("partner")
            .annotate(item_count=Count("items"))
            .order_by("-date")
        )

        if search_query:
            queryset = queryset.filter(
                Q(partner__name__icontains=search_query)
                | Q(notes__icontains=search_query)
            )

        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)

        return queryset

    @staticmethod
    def validate_item_for_sale(item_object):
        """
        Performs all checks to ensure an item is sellable.
        1. Is it available? (Not sold/dead)
        2. Is it biologically safe? (Withdrawal period)
        """
        if hasattr(item_object, "is_active") and not item_object.is_active:
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
    def create_sale(sale_instance: Sale, sale_items_data: list[SaleItem]) -> Sale:
        """
        Creates a Sale and its Items, updating totals.
        """
        # Save the sale first to get a PK
        sale_instance.save()

        total_amount = Money(0)

        for item in sale_items_data:
            # Check Withdrawal Logic
            if item.content_object:
                SaleService.validate_item_for_sale(item.content_object)

            item.sale = sale_instance
            item.save()  # formatting and total_price calc happens in model save
            # money library handles addition, but mypy might not know __add__ returns Money
            total_amount += Money(item.total_price)  # type: ignore

        sale_instance.total_amount = total_amount
        sale_instance.save()

        return sale_instance

    @staticmethod
    @transaction.atomic
    def update_sale_totals(sale: Sale) -> None:
        """
        Recalculates and updates the total amount for a sale.
        """
        # Use aggregation or python loop. Python loop is safer with Money class precision
        # though DB aggregation is faster. Given Money logic in app, let's use app logic.
        items = sale.items.all()  # type: ignore
        total = Money(0)
        for item in items:
            total += Money(item.total_price)  # type: ignore

        sale.total_amount = total
        sale.save()

    @staticmethod
    @transaction.atomic
    def create_sale_from_forms(form, formset) -> Sale:
        """
        Orchestrates creation from Django Forms.
        """
        sale = form.save(commit=False)
        sale.save()  # Get PK

        # Save formset items
        instances = formset.save(commit=False)
        for instance in instances:
            # Check Withdrawal Logic
            if instance.content_object:
                SaleService.validate_item_for_sale(instance.content_object)

            instance.sale = sale
            instance.save()

        # Handle deletions
        for obj in formset.deleted_objects:
            obj.delete()

        SaleService.update_sale_totals(sale)
        return sale

    @staticmethod
    def get_deleted_sales():
        """
        Returns a queryset of soft-deleted sales.
        """
        return Sale.all_objects.filter(is_deleted=True).order_by("-date")

    @staticmethod
    def restore_sale(sale: Sale) -> None:
        """
        Restores a soft-deleted sale.
        """
        sale.restore()

    @staticmethod
    def hard_delete_sale(sale: Sale) -> None:
        """
        Permanently deletes a sale.
        """
        sale.delete(destroy=True)
