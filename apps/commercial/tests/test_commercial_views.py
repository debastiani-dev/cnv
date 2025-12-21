import pytest
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.commercial.models import SalesEvent, SalesLot
from apps.finance.models.finance import CostEntry


@pytest.mark.django_db
class TestCommercialViews:
    @pytest.fixture(autouse=True)
    def override_storages(self, settings):
        settings.STORAGES = {
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            }
        }

    def test_event_catalog_view(self, client, django_user_model):
        """Test the Event Catalog View renders correctly."""
        user = baker.make(django_user_model)
        client.force_login(user)
        event = baker.make(SalesEvent, name="Catalog Event")
        lot = baker.make(SalesLot, event=event, lot_number=1)
        animal = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE, current_weight=500)
        lot.animals.add(animal)

        url = reverse("commercial:event_catalog", kwargs={"pk": event.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "catalog/event_catalog.html" in [t.name for t in response.templates]
        assert response.context["event"] == event
        assert lot in response.context["lots"]

    def test_lot_print_view(self, client):
        """Test the Lot Print View renders correctly."""
        event = baker.make(SalesEvent)
        lot = baker.make(SalesLot, event=event, lot_number=55)
        animal = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)
        lot.animals.add(animal)

        url = reverse("commercial:print_lot", kwargs={"pk": lot.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "catalog/print_view.html" in [t.name for t in response.templates]
        assert response.context["lot"] == lot

    def test_manage_lots_view_get(self, client, django_user_model):
        """Test Manage Lots GET request returns available animals."""
        user = baker.make(django_user_model)
        client.force_login(user)
        event = baker.make(SalesEvent)
        available_cow = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)
        sold_cow = baker.make(Cattle, status=Cattle.STATUS_SOLD)

        url = reverse("commercial:manage_lots", kwargs={"pk": event.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert available_cow in response.context["available_animals"]
        assert sold_cow not in response.context["available_animals"]

    def test_manage_lots_view_post_success(self, client, django_user_model):
        """Test creating a lot via POST in Manage Lots view."""
        user = baker.make(django_user_model)
        client.force_login(user)
        event = baker.make(SalesEvent)
        cows = baker.make(Cattle, _quantity=3, status=Cattle.STATUS_AVAILABLE)

        # Add some costs
        for cow in cows:
            baker.make(CostEntry, animal=cow, amount=100)

        url = reverse("commercial:manage_lots", kwargs={"pk": event.pk})
        data = {
            "lot_number": 101,
            "reserve_price": "5000.00",
            "animals": [cow.pk for cow in cows],
        }

        response = client.post(url, data, follow=True)

        assert response.status_code == 200
        assert SalesLot.objects.filter(event=event, lot_number=101).exists()

        lot = SalesLot.objects.get(lot_number=101)
        assert lot.animals.count() == 3
        # 3 cows * 100 cost = 300
        assert lot.cost_at_creation == 300.00
        assert lot.reserve_price == 5000.00
