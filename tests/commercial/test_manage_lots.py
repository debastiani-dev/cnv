# pylint: disable=unused-argument, redefined-outer-name
import unittest.mock

import pytest
from django.urls import reverse

from apps.commercial.models import SalesEvent, SalesLot
from apps.genetics.models.genetics import EmbryoBatch, SemenBatch


@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def event(db, user):
    return SalesEvent.objects.create(
        name="Test Auction", date="2023-01-01", sales_type=SalesEvent.TYPE_AUCTION
    )


@pytest.fixture
def embryo_batch(db, tank):
    return EmbryoBatch.objects.create(
        tank=tank,
        canister="E1",
        initial_quantity=10,
        current_quantity=10,
        purchase_date="2023-01-01",
        sire_name="Sire X",
        dam_name="Dam Y",
        cost_per_unit=500.00,
    )


@pytest.mark.django_db
class TestManageLotsGeneticValues:
    def test_create_semen_lot(self, authenticated_client, event, semen_batch):
        url = reverse("commercial:manage_lots", args=[event.pk])

        data = {
            "lot_number": "1",
            "reserve_price": "100.00",
            "lot_type": "semen",
            "genetic_batch_id": semen_batch.pk,
            "quantity": 10,
        }

        response = authenticated_client.post(url, data)
        assert response.status_code == 200

        # Verify SalesLot created
        lot = SalesLot.objects.get(event=event, lot_number=1)
        assert lot.content_object == semen_batch
        assert lot.quantity == 10

        # Standard commercial logic: Inventory is deducted upon Closing the lot (Sale),
        # not at creation time. So quantity should remain unchanged here.
        semen_batch.refresh_from_db()
        assert semen_batch.current_quantity == 100

    def test_create_embryo_lot(self, authenticated_client, event, embryo_batch):
        url = reverse("commercial:manage_lots", args=[event.pk])

        data = {
            "lot_number": "2",
            "reserve_price": "1000.00",
            "lot_type": "embryo",
            "genetic_batch_id": embryo_batch.pk,
            "quantity": 2,
        }

        response = authenticated_client.post(url, data)
        assert response.status_code == 200

        lot = SalesLot.objects.get(event=event, lot_number=2)
        assert lot.content_object == embryo_batch
        assert lot.quantity == 2

    def test_create_invalid_lot_type(self, authenticated_client, event):
        url = reverse("commercial:manage_lots", args=[event.pk])
        # Missing batch_id or quantity
        data = {
            "lot_number": "3",
            "reserve_price": "100.00",
            "lot_type": "semen",
            "quantity": 0,
        }
        response = authenticated_client.post(url, data)
        # Should show error message and redirect (GET)
        assert (
            response.status_code == 200
        )  # It renders the form with errors (or redirects depending on impl)
        # Looking at view code (Step 1019): `return self.get(request, ...)` if error.
        # So status code is 200 (re-render).
        assert "Please select a batch and valid quantity." in [
            m.message for m in response.context["messages"]
        ]

    def test_create_animal_lot_no_selection(self, authenticated_client, event):
        url = reverse("commercial:manage_lots", args=[event.pk])
        data = {
            "lot_number": "4",
            "reserve_price": "1000.00",
            "lot_type": "animal",
            "animals": [],  # Empty selection
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        assert "Please select at least one animal." in [
            m.message for m in response.context["messages"]
        ]

    def test_create_lot_exception_handling(
        self, authenticated_client, event, tank, bull
    ):
        url = reverse("commercial:manage_lots", args=[event.pk])
        semen = SemenBatch.objects.create(
            tank=tank,
            bull=bull,
            batch_code="XX",
            initial_quantity=10,
            current_quantity=10,
            purchase_date="2023-01-01",
            cost_per_unit=10,
        )
        data = {
            "lot_number": "5",
            "reserve_price": "100.00",
            "lot_type": "semen",
            "genetic_batch_id": semen.pk,
            "quantity": 5,
        }

        with unittest.mock.patch(
            "apps.commercial.models.SalesLot.objects.create"
        ) as mock_create:
            mock_create.side_effect = Exception("Database Error")
            response = authenticated_client.post(url, data)
            assert response.status_code == 200
            assert "Error creating lot: Database Error" in [
                m.message for m in response.context["messages"]
            ]
