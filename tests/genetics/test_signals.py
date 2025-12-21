# pylint: disable=unused-argument, redefined-outer-name
import pytest

from apps.transactions.models import Transaction, TransactionItem


@pytest.mark.django_db
def test_update_inventory_on_purchase(semen_batch, partner, user):
    """Verify inventory increases when a PURCHASE transaction is created."""
    initial_qty = semen_batch.current_quantity
    purchase_qty = 50

    transaction = Transaction.objects.create(
        partner=partner,
        date="2023-01-01",
        type=Transaction.TYPE_PURCHASE,
        status=Transaction.STATUS_DRAFT,
    )

    TransactionItem.objects.create(
        transaction=transaction,
        content_object=semen_batch,
        quantity=purchase_qty,
        unit_price=50.00,
    )

    semen_batch.refresh_from_db()
    assert semen_batch.current_quantity == initial_qty + purchase_qty


@pytest.mark.django_db
def test_update_inventory_on_sale(semen_batch, partner, user):
    """Verify inventory decreases when a SALE transaction is created."""
    initial_qty = semen_batch.current_quantity
    sale_qty = 20

    transaction = Transaction.objects.create(
        partner=partner,
        date="2023-01-01",
        type=Transaction.TYPE_SALE,
        status=Transaction.STATUS_DRAFT,
    )

    TransactionItem.objects.create(
        transaction=transaction,
        content_object=semen_batch,
        quantity=sale_qty,
        unit_price=100.00,
    )

    semen_batch.refresh_from_db()
    assert semen_batch.current_quantity == initial_qty - sale_qty


@pytest.mark.django_db
def test_signal_ignored_on_update(semen_batch, partner, user):
    """Verify signal is ignored if transaction item is updated (created=False)."""
    initial_qty = semen_batch.current_quantity

    transaction = Transaction.objects.create(
        partner=partner,
        date="2023-01-01",
        type=Transaction.TYPE_PURCHASE,
        status=Transaction.STATUS_DRAFT,
    )

    # Create first (signals runs)
    item = TransactionItem.objects.create(
        transaction=transaction,
        content_object=semen_batch,
        quantity=10,
        unit_price=50.00,
    )
    semen_batch.refresh_from_db()
    assert semen_batch.current_quantity == initial_qty + 10

    # Update (signal should return early)
    item.quantity = 20
    # Manually trigger signal or just save, but signal checks `created` arg.
    # The signal is connected to post_save. When we save, created=False.
    item.save()

    semen_batch.refresh_from_db()
    # Should NOT have increased by another 20 (or diff). Logic says "return if not created".
    # So quantity remains 110.
    assert semen_batch.current_quantity == initial_qty + 10


@pytest.mark.django_db
def test_signal_insufficient_stock_branch(semen_batch, partner, user):
    """Verify the insufficient stock branch is hit (safe fail)."""
    semen_batch.current_quantity = 5
    semen_batch.save()

    transaction = Transaction.objects.create(
        partner=partner,
        date="2023-01-01",
        type=Transaction.TYPE_SALE,
        status=Transaction.STATUS_DRAFT,
    )

    # Sale of 10 (more than 5)
    TransactionItem.objects.create(
        transaction=transaction,
        content_object=semen_batch,
        quantity=10,
        unit_price=100.00,
    )

    semen_batch.refresh_from_db()
    # Logic: if current >= quantity: reduce. Else: pass.
    # So quantity should remain 5.
    assert semen_batch.current_quantity == 5


@pytest.mark.django_db
def test_signal_ignored_for_non_genetic_item(partner, user):
    """Verify signal ignores non-genetic items."""
    transaction = Transaction.objects.create(
        partner=partner,
        date="2023-01-01",
        type=Transaction.TYPE_PURCHASE,
        status=Transaction.STATUS_DRAFT,
    )

    # Create an item with content_object = partner (just as a random model)
    item = TransactionItem.objects.create(
        transaction=transaction,
        content_object=partner,  # Not SemenBatch/EmbryoBatch
        quantity=1,
        unit_price=10.00,
    )
    assert item.pk is not None
