import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.partners.models import Partner
from apps.transactions.forms import TransactionForm, TransactionItemForm
from apps.transactions.models import Transaction


@pytest.mark.django_db
class TestTransactionForms:
    def test_transaction_form_valid(self):
        partner = baker.make(Partner)
        data = {
            "date": "2023-01-01",
            "type": Transaction.TYPE_SALE,
            "partner": partner.pk,
            "notes": "Test Note",
        }
        form = TransactionForm(data=data)
        assert form.is_valid()

    def test_transaction_item_form_valid(self):
        cow = baker.make(Cattle)
        ct = ContentType.objects.get_for_model(Cattle)

        data = {
            "content_type": ct.pk,
            "object_id": cow.pk,
            "quantity": 1,
            "unit_price": 5000.00,
        }
        form = TransactionItemForm(data=data)
        assert form.is_valid()

    def test_transaction_item_form_invalid_item(self):
        """Test validation error if object_id does not exist for the content_type."""
        ct = ContentType.objects.get_for_model(Cattle)
        # Random UUID that doesn't exist

        data = {
            "content_type": ct.pk,
            "object_id": uuid.uuid4(),
            "quantity": 1,
            "unit_price": 5000.00,
        }
        form = TransactionItemForm(data=data)
        assert not form.is_valid()
        assert "object_id" in form.errors
