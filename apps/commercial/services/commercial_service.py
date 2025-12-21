from django.core.exceptions import ValidationError
from django.db import transaction

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.commercial.models import SalesLot
from apps.transactions.models import Transaction, TransactionItem


class CommercialService:
    @staticmethod
    def calculate_lot_cost(animals) -> Money:
        """
        Helper: Sums up the accumulated cost of all animals in the list.
        Used when creating the Lot to show the user their break-even point.
        """
        return Money(sum(animal.total_cost for animal in animals))

    @staticmethod
    @transaction.atomic
    def close_lot(lot: SalesLot, buyer_partner, final_hammer_price, date):
        """
        Finalizes the sale of a Lot.
        """
        if lot.status != SalesLot.STATUS_AVAILABLE:
            raise ValidationError(f"Lot {lot.lot_number} is not available.")

        # 1. Update Marketing Status
        lot.status = SalesLot.STATUS_SOLD
        lot.save()

        # 2. Update Biological Status for ALL animals involved
        # This prevents them from being added to other lists
        lot.animals.update(status=Cattle.STATUS_SOLD)

        # 3. Financial Integration (Create Draft Invoice)
        # We check if a Draft Sale already exists for this Partner on this Date.
        # This groups multiple Lot purchases into a single Invoice.
        invoice, _ = Transaction.objects.get_or_create(
            partner=buyer_partner,
            date=date,
            type=Transaction.TYPE_SALE,
            status=Transaction.STATUS_DRAFT,
            defaults={"notes": f"Generated automatically from event: {lot.event.name}"},
        )

        # 4. Create the Ledger Line Item
        # We link the Item to the Ledger Line Item associated with this Lot
        TransactionItem.objects.create(
            transaction=invoice,
            content_object=lot,  # <--- The Bridge: Links Ledger to Commercial Lot
            quantity=1,  # One Lot sold
            unit_price=final_hammer_price,
        )

        # Update totals for the transaction
        invoice.update_total()

        return invoice
