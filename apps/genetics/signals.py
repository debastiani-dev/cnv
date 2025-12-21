from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.genetics.models import EmbryoBatch, SemenBatch
from apps.transactions.models import Transaction, TransactionItem


@receiver(post_save, sender=TransactionItem)
def update_genetics_inventory_on_transaction(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
    """
    Update genetic material inventory when a transaction item is saved.
    - Purchase: Increase current_quantity
    - Sale: Decrease current_quantity
    """
    if not created:
        return  # Only process new items

    content_object = instance.content_object

    # Check if the transaction item is for genetics material
    if not isinstance(content_object, (SemenBatch, EmbryoBatch)):
        return

    transaction = instance.transaction
    quantity = int(instance.quantity)

    if transaction.type == Transaction.TYPE_PURCHASE:
        # Increase inventory on purchase
        content_object.current_quantity += quantity
        content_object.save(update_fields=["current_quantity"])

    elif transaction.type == Transaction.TYPE_SALE:
        # Decrease inventory on sale
        if content_object.current_quantity >= quantity:
            content_object.current_quantity -= quantity
            content_object.save(update_fields=["current_quantity"])
        else:
            # Log warning or raise error if insufficient stock
            pass  # Could add logging here
