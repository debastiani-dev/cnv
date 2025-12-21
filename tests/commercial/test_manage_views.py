# pylint: disable=redefined-outer-name
from unittest.mock import patch

import pytest
from django.urls import reverse
from model_bakery import baker

from apps.authentication.models.user import User
from apps.commercial.models import SalesEvent, SalesLot
from apps.partners.models import Partner


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="password")


@pytest.fixture
def client(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestManageLotsView:
    def test_post_validation_error(self, client):
        event = baker.make(SalesEvent)
        url = reverse("commercial:manage_lots", kwargs={"pk": event.pk})

        # Missing required fields
        response = client.post(url, {}, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert any("Please provide Lot Number" in str(m) for m in messages)

    def test_update_lot_success(self, client):
        event = baker.make(SalesEvent)
        lot = baker.make(SalesLot, event=event)
        url = reverse("commercial:lot_update", kwargs={"pk": lot.pk})

        data = {"lot_number": "999", "reserve_price": "100.00"}
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert any("Lot updated successfully" in str(m) for m in messages)

        lot.refresh_from_db()
        assert lot.lot_number == 999

    def test_delete_lot_success(self, client):
        event = baker.make(SalesEvent)
        lot = baker.make(SalesLot, event=event)
        url = reverse("commercial:lot_delete", kwargs={"pk": lot.pk})

        response = client.post(url, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert any("Lot deleted successfully" in str(m) for m in messages)
        assert not SalesLot.objects.filter(pk=lot.pk).exists()


@pytest.mark.django_db
class TestCloseLotView:
    def test_context_data(self, client):
        lot = baker.make(SalesLot)
        url = reverse("commercial:lot_close", kwargs={"pk": lot.pk})
        baker.make(Partner, _quantity=2)

        response = client.get(url)
        assert response.status_code == 200
        assert "buyers" in response.context
        assert response.context["buyers"].count() == 2

    def test_post_validation_error(self, client):
        lot = baker.make(SalesLot)
        url = reverse("commercial:lot_close", kwargs={"pk": lot.pk})

        # Missing buyer and price
        response = client.post(url, {}, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert any("Please select a Buyer" in str(m) for m in messages)

    def test_post_success(self, client):
        lot = baker.make(SalesLot)
        buyer = baker.make(Partner)
        url = reverse("commercial:lot_close", kwargs={"pk": lot.pk})

        with patch(
            "apps.commercial.services.commercial_service.CommercialService.close_lot"
        ) as mock_close:
            data = {"buyer": buyer.pk, "hammer_price": "5000.00"}
            response = client.post(url, data, follow=True)

            assert response.status_code == 200
            messages = list(response.context["messages"])
            assert any(f"Lot sold to {buyer.name}" in str(m) for m in messages)

            mock_close.assert_called_once()

    def test_post_exception(self, client):
        lot = baker.make(SalesLot)
        buyer = baker.make(Partner)
        url = reverse("commercial:lot_close", kwargs={"pk": lot.pk})

        with patch(
            "apps.commercial.services.commercial_service.CommercialService.close_lot",
            side_effect=Exception("Close Error"),
        ):
            data = {"buyer": buyer.pk, "hammer_price": "5000.00"}
            response = client.post(url, data, follow=True)

            assert response.status_code == 200
            messages = list(response.context["messages"])
            assert any("Error closing lot: Close Error" in str(m) for m in messages)
