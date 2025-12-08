# pylint: disable=duplicate-code
import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.purchases.forms import PurchaseItemForm
from apps.purchases.models.purchase import Purchase, PurchaseItem


@pytest.mark.django_db
class TestPurchaseItemForm:
    def test_purchase_item_form_valid(self):
        cow = baker.make(Cattle)
        ct = ContentType.objects.get_for_model(Cattle)

        data = {
            "content_type": ct.pk,
            "object_id": cow.pk,
            "quantity": 1,
            "unit_price": "100.00",
        }

        form = PurchaseItemForm(data=data)
        assert form.is_valid()
        assert form.instance.content_object == cow

    def test_purchase_item_form_invalid_object_id(self):
        ct = ContentType.objects.get_for_model(Cattle)
        # Random UUID
        data = {
            "content_type": ct.pk,
            "object_id": uuid.uuid4(),
            "quantity": 1,
            "unit_price": "100.00",
        }

        form = PurchaseItemForm(data=data)
        assert not form.is_valid()
        assert "object_id" in form.errors
        assert str(form.errors["object_id"][0]) == "Selected item does not exist."

    def test_purchase_item_form_init_with_instance(self):
        # Test pre-filling logic
        cow = baker.make(Cattle, name="Bessie")

        purchase = baker.make(Purchase)
        item = PurchaseItem.objects.create(
            purchase=purchase, content_object=cow, quantity=1, unit_price=100
        )

        form = PurchaseItemForm(instance=item)
        assert form.fields["content_type"].initial == ContentType.objects.get_for_model(
            Cattle
        )
        assert form.fields["object_id"].initial == cow.pk
        assert form.fields["item_name"].initial == str(cow)
