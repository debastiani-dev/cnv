import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.partners.models import Partner
from apps.sales.models import Sale


@pytest.mark.django_db
class TestSaleViews:
    def test_sale_list_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        baker.make(Sale, _quantity=3)

        response = client.get(reverse("sales:list"))
        assert response.status_code == 200
        assert len(response.context["sales"]) == 3

    def test_sale_create_view_get(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        response = client.get(reverse("sales:create"))
        assert response.status_code == 200
        assert "form" in response.context
        assert "items" in response.context

    def test_sale_create_view_post_valid(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        partner = baker.make(Partner)
        cow = baker.make(Cattle)
        ct = ContentType.objects.get_for_model(Cattle)

        data = {
            "date": "2023-01-01",
            "partner": partner.pk,
            "notes": "Test Note",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-content_type": ct.pk,
            "items-0-object_id": cow.pk,
            "items-0-quantity": "1",
            "items-0-unit_price": "100.00",
        }

        response = client.post(reverse("sales:create"), data)
        # Should redirect to list on success
        assert response.status_code == 302
        assert Sale.objects.count() == 1
        sale = Sale.objects.first()
        assert sale.items.count() == 1
        assert sale.items.first().content_object == cow

    def test_sale_detail_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        sale = baker.make(Sale)
        response = client.get(reverse("sales:detail", kwargs={"pk": sale.pk}))
        assert response.status_code == 200
        assert response.context["sale"] == sale

    def test_item_lookup_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        cow1 = baker.make(Cattle, name="Bessie")
        cow2 = baker.make(
            Cattle, name="Daisy", is_deleted=True
        )  # Should be filtered out

        ct = ContentType.objects.get_for_model(Cattle)

        url = reverse("sales:api-item-lookup")
        response = client.get(f"{url}?content_type_id={ct.pk}")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        ids = [item["id"] for item in data["results"]]
        assert str(cow1.pk) in ids
        assert str(cow2.pk) not in ids

    def test_item_lookup_view_invalid_ct(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        # User model is not whitelisted
        ct = ContentType.objects.get_for_model(django_user_model)

        url = reverse("sales:api-item-lookup")
        response = client.get(f"{url}?content_type_id={ct.pk}")

        assert response.status_code == 403
