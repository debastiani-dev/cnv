import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.transactions.models import Transaction, TransactionItem


@pytest.mark.django_db
class TestCattleDeletionValidation:

    def test_cannot_delete_cattle_in_sale(self):
        cattle = baker.make(Cattle)
        # Create Sale Transaction
        tx = baker.make(Transaction, type=Transaction.TYPE_SALE)
        # Create Transaction Item linked to cattle
        baker.make(
            TransactionItem,
            transaction=tx,
            content_type=ContentType.objects.get_for_model(Cattle),
            object_id=cattle.pk,
            quantity=1,
            unit_price=100,
        )

        # Validation Error expected on delete
        with pytest.raises(ValidationError) as exc:
            cattle.delete()
        assert "part of a Transaction" in str(exc.value)

    def test_cannot_delete_cattle_in_purchase(self):
        cattle = baker.make(Cattle)
        # Create Purchase Transaction
        tx = baker.make(Transaction, type=Transaction.TYPE_PURCHASE)
        # Create Transaction Item linked to cattle
        baker.make(
            TransactionItem,
            transaction=tx,
            content_type=ContentType.objects.get_for_model(Cattle),
            object_id=cattle.pk,
            quantity=1,
            unit_price=100,
        )

        # Validation Error expected on delete
        with pytest.raises(ValidationError) as exc:
            cattle.delete()
        assert "part of a Transaction" in str(exc.value)

    def test_can_delete_unlinked_cattle(self):
        cattle = baker.make(Cattle)
        cattle.delete()  # Should not raise
        assert cattle.is_deleted

    def test_cannot_hard_delete_if_linked(self):
        cattle = baker.make(Cattle)
        tx = baker.make(Transaction, type=Transaction.TYPE_SALE)
        baker.make(
            TransactionItem,
            transaction=tx,
            content_type=ContentType.objects.get_for_model(Cattle),
            object_id=cattle.pk,
        )
        with pytest.raises(ValidationError):
            cattle.delete(destroy=True)
