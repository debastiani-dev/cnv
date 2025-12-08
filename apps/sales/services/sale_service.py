from django.db import transaction

from apps.base.utils.money import Money
from apps.sales.models import Sale, SaleItem


class SaleService:
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
            item.sale = sale_instance
            item.save()  # formatting and total_price calc happens in model save
            total_amount += Money(item.total_price)

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
        items = sale.items.all()
        total = Money(0)
        for item in items:
            total += Money(item.total_price)

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
