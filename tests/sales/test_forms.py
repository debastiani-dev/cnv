import pytest
from django.contrib.contenttypes.models import ContentType
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.sales.forms import SaleItemForm


@pytest.mark.django_db
class TestSaleItemForm:
    def test_sale_item_form_valid(self):
        cow = baker.make(Cattle)
        ct = ContentType.objects.get_for_model(Cattle)

        data = {
            "content_type": ct.pk,
            "object_id": cow.pk,
            "quantity": 1,
            "unit_price": "100.00",
        }

        form = SaleItemForm(data=data)
        assert form.is_valid()
        assert form.instance.content_object == cow

    def test_sale_item_form_invalid_object_id(self):
        ct = ContentType.objects.get_for_model(Cattle)
        # Random UUID
        import uuid

        data = {
            "content_type": ct.pk,
            "object_id": uuid.uuid4(),
            "quantity": 1,
            "unit_price": "100.00",
        }

        form = SaleItemForm(data=data)
        assert not form.is_valid()
        assert "object_id" in form.errors
        assert str(form.errors["object_id"][0]) == "Selected item does not exist."

    def test_sale_item_form_init_with_instance(self):
        # Test pre-filling logic
        cow = baker.make(Cattle, name="Bessie")
        from apps.sales.models import Sale, SaleItem

        sale = baker.make(Sale)
        item = SaleItem.objects.create(
            sale=sale, content_object=cow, quantity=1, unit_price=100
        )

        form = SaleItemForm(instance=item)
        assert form.fields["content_type"].initial == ContentType.objects.get_for_model(
            Cattle
        )
        assert form.fields["object_id"].initial == cow.pk
        assert form.fields["item_name"].initial == str(cow)
