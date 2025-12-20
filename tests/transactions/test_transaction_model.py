import pytest
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.partners.models import Partner
from apps.transactions.models import Transaction, TransactionItem


@pytest.mark.django_db
class TestTransactionModel:
    def test_create_transaction_sale(self):
        partner = baker.make(Partner)
        transaction = baker.make(
            Transaction,
            partner=partner,
            type=Transaction.TYPE_SALE,
            total_amount=Money("100.00"),
        )

        assert Transaction.objects.count() == 1
        assert transaction.partner == partner
        assert transaction.type == Transaction.TYPE_SALE
        assert str(transaction) == f"Sale / Revenue - {partner} - {transaction.date}"

    def test_create_transaction_purchase(self):
        partner = baker.make(Partner)
        transaction = baker.make(
            Transaction, partner=partner, type=Transaction.TYPE_PURCHASE
        )

        assert Transaction.objects.count() == 1
        assert transaction.type == Transaction.TYPE_PURCHASE

    def test_transaction_item_polymorphism(self):
        # Create a Cow (Asset)
        cow = baker.make(Cattle, tag="COW-001", name="Bessie")

        # Create a Transaction
        transaction = baker.make(Transaction, type=Transaction.TYPE_SALE)

        # Create a TransactionItem linked to the Cow
        item = TransactionItem.objects.create(
            transaction=transaction,
            content_object=cow,
            quantity=1,
            unit_price=Money("5000.00"),
        )

        assert item.content_object == cow
        assert Money(item.total_price) == Money("5000.00")
        assert str(item) == f"1x {cow} in {transaction}"

    def test_transaction_item_total_calculation(self):
        transaction = baker.make(Transaction)
        cow = baker.make(Cattle)

        item = TransactionItem(
            transaction=transaction,
            content_object=cow,
            quantity=2.5,
            unit_price=Money("100.00"),
        )
        item.save()

        # Item total should be 250
        assert Money(item.total_price) == Money("250.00")

        # Transaction header total should be auto-updated (logic in TransactionItem.save)
        transaction.refresh_from_db()
        assert Money(transaction.total_amount) == Money("250.00")
