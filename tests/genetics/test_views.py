# pylint: disable=unused-argument, redefined-outer-name
import unittest

import pytest
from django.db.models import ProtectedError
from django.urls import reverse

from apps.authentication.models import User
from apps.cattle.models import Cattle
from apps.genetics.models import EmbryoBatch, SemenBatch, StorageTank


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="password")


@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def tank(db):
    return StorageTank.objects.create(
        name="Tank 1", capacity_liters=20.0, location_description="Lab"
    )


@pytest.fixture
def bull(db):
    return Cattle.objects.create(
        tag="BULL01",
        sex=Cattle.SEX_MALE,
        status=Cattle.STATUS_AVAILABLE,
        breed=Cattle.BREED_NELORE,
    )


@pytest.fixture
def dam(db):
    return Cattle.objects.create(
        tag="DAM01",
        sex=Cattle.SEX_FEMALE,
        status=Cattle.STATUS_AVAILABLE,
        breed=Cattle.BREED_NELORE,
    )


@pytest.fixture
def semen_batch(db, tank, bull):
    return SemenBatch.objects.create(
        tank=tank,
        canister="Canister 1",
        initial_quantity=100,
        current_quantity=100,
        purchase_date="2023-01-01",
        cost_per_unit=50.00,
        bull=bull,
        batch_code="B001",
    )


@pytest.fixture
def embryo_batch(db, tank, bull, dam):
    return EmbryoBatch.objects.create(
        tank=tank,
        canister="Canister 2",
        initial_quantity=10,
        current_quantity=10,
        purchase_date="2023-01-01",
        cost_per_unit=500.00,
        sire=bull,
        dam=dam,
        grade="1",
        stage="Blastocyst",
    )


# --- Storage Tank Tests ---


class TestStorageTankViews:
    def test_list_view(self, authenticated_client, tank):
        url = reverse("genetics:tank-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert tank in response.context["tanks"]

    def test_detail_view(self, authenticated_client, tank):
        url = reverse("genetics:tank-detail", args=[tank.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.context["tank"] == tank

    def test_create_view_post(self, authenticated_client):
        url = reverse("genetics:tank-create")
        data = {
            "name": "New Tank",
            "capacity_liters": 50,
            "location_description": "Office",
            "last_refill_date": "2023-01-01",
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302  # Redirects
        assert StorageTank.objects.filter(name="New Tank").exists()

    def test_update_view_post(self, authenticated_client, tank):
        url = reverse("genetics:tank-update", args=[tank.pk])
        data = {
            "name": "Updated Tank",
            "capacity_liters": 20,
            "location_description": "Lab",
            "last_refill_date": "2023-01-01",
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        tank.refresh_from_db()
        assert tank.name == "Updated Tank"

    def test_delete_view_post(self, authenticated_client, tank):
        # Soft Delete
        url = reverse("genetics:tank-delete", args=[tank.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        tank.refresh_from_db()
        assert tank.is_deleted is True

    def test_trash_view(self, authenticated_client, tank):
        tank.soft_delete()
        url = reverse("genetics:tank-trash")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert tank in response.context["tanks"]

    def test_restore_view(self, authenticated_client, tank):
        tank.soft_delete()
        url = reverse("genetics:tank-restore", args=[tank.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        tank.refresh_from_db()
        assert tank.is_deleted is False

    def test_permanent_delete_view(self, authenticated_client, tank):
        tank.soft_delete()
        url = reverse("genetics:tank-permanent-delete", args=[tank.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        assert not StorageTank.objects.filter(pk=tank.pk).exists()

    def test_permanent_delete_view_protected_error(self, authenticated_client, tank):
        tank.soft_delete()
        url = reverse("genetics:tank-permanent-delete", args=[tank.pk])

        with unittest.mock.patch(
            "apps.genetics.services.GeneticsService.hard_delete_tank"
        ) as mock_delete:
            mock_delete.side_effect = ProtectedError("Protected", [])
            response = authenticated_client.post(url)
            assert response.status_code == 200
            assert "cannot delete this object" in response.content.decode().lower()

    def test_delete_view_protected_error(self, authenticated_client, tank):
        url = reverse("genetics:tank-delete", args=[tank.pk])

        with unittest.mock.patch(
            "apps.genetics.services.GeneticsService.delete_tank"
        ) as mock_delete:
            mock_delete.side_effect = ProtectedError("Protected", [])
            response = authenticated_client.post(url)
            # Should handle error and probably re-render page or redirect with error
            # Code: return self.handle_delete_error(request, e) -> renders valid template
            assert response.status_code == 200
            assert "cannot delete this object" in response.content.decode().lower()

    def test_restore_view_get(self, authenticated_client, tank):
        tank.soft_delete()
        url = reverse("genetics:tank-restore", args=[tank.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/tank_confirm_restore.html" in [
            t.name for t in response.templates
        ]

    def test_restore_view_not_found(self, authenticated_client):
        url = reverse(
            "genetics:tank-restore", args=["00000000-0000-0000-0000-000000000000"]
        )
        response = authenticated_client.post(url)
        assert response.status_code == 302  # Redirects to list

        response_get = authenticated_client.get(url)
        assert response_get.status_code == 302

    def test_permanent_delete_view_get(self, authenticated_client, tank):
        tank.soft_delete()
        url = reverse("genetics:tank-permanent-delete", args=[tank.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/tank_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]

    def test_permanent_delete_view_not_found(self, authenticated_client):
        url = reverse(
            "genetics:tank-permanent-delete",
            args=["00000000-0000-0000-0000-000000000000"],
        )
        response = authenticated_client.post(url)
        assert response.status_code == 302

        response_get = authenticated_client.get(url)
        assert response_get.status_code == 302

    def test_create_view_context(self, authenticated_client):
        url = reverse("genetics:tank-create")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "title" in response.context

    def test_update_view_context(self, authenticated_client, tank):
        url = reverse("genetics:tank-update", args=[tank.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "title" in response.context


# --- Semen Batch Tests ---


class TestSemenBatchViews:
    def test_list_view(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert semen_batch in response.context["semen_batches"]

    def test_detail_view(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-detail", args=[semen_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.context["batch"] == semen_batch

    def test_create_view_post(self, authenticated_client, tank, bull):
        url = reverse("genetics:semen-create")
        data = {
            "tank": tank.pk,
            "canister": "A1",
            "initial_quantity": 50,
            "current_quantity": 50,
            "min_stock_alert": 10,
            "purchase_date": "2023-05-01",
            "cost_per_unit": 25.00,
            "bull": bull.pk,
            "batch_code": "NEWBATCH",
            "breed": "Nelore",
            "type": SemenBatch.TYPE_CONVENTIONAL,
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        assert SemenBatch.objects.filter(batch_code="NEWBATCH").exists()

    def test_update_view_post(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-update", args=[semen_batch.pk])
        data = {
            "tank": semen_batch.tank.pk,
            "canister": "A2",  # Changed
            "initial_quantity": 100,
            "current_quantity": 100,
            "min_stock_alert": 10,
            "purchase_date": "2023-01-01",
            "cost_per_unit": 50.00,
            "bull": semen_batch.bull.pk,  # Keep existing
            "batch_code": "B001",
            "breed": "Nelore",
            "type": SemenBatch.TYPE_CONVENTIONAL,
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        semen_batch.refresh_from_db()
        assert semen_batch.canister == "A2"

    def test_stock_adjustment_view_get(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-adjust-stock", args=[semen_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/stock_adjustment.html" in [t.name for t in response.templates]

    def test_stock_adjustment_view(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-adjust-stock", args=[semen_batch.pk])
        # LOSS
        data = {"adjustment_type": "LOSS", "quantity": 5}
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        semen_batch.refresh_from_db()
        assert semen_batch.current_quantity == 95

        # FOUND
        data_found = {"adjustment_type": "FOUND", "quantity": 2}
        authenticated_client.post(url, data_found)
        semen_batch.refresh_from_db()
        assert semen_batch.current_quantity == 97

    def test_stock_adjustment_validation(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-adjust-stock", args=[semen_batch.pk])
        # Try adjusting more than available
        data = {"adjustment_type": "LOSS", "quantity": 1000}
        response = authenticated_client.post(url, data)
        assert response.status_code == 200  # Form error, re-renders page
        assert "Cannot remove" in response.content.decode()

    def test_delete_view_post(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-delete", args=[semen_batch.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        semen_batch.refresh_from_db()
        assert semen_batch.is_deleted is True

    def test_delete_view_protected_error(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-delete", args=[semen_batch.pk])

        with unittest.mock.patch(
            "apps.genetics.services.GeneticsService.delete_semen_batch"
        ) as mock_delete:
            mock_delete.side_effect = ProtectedError("Protected", [])
            response = authenticated_client.post(url)
            assert response.status_code == 200
            assert "cannot delete this object" in response.content.decode().lower()

    def test_restore_view(self, authenticated_client, semen_batch):
        semen_batch.soft_delete()
        url = reverse("genetics:semen-restore", args=[semen_batch.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        semen_batch.refresh_from_db()
        assert semen_batch.is_deleted is False

    def test_permanent_delete_view(self, authenticated_client, semen_batch):
        semen_batch.soft_delete()
        url = reverse("genetics:semen-permanent-delete", args=[semen_batch.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        assert not SemenBatch.objects.filter(pk=semen_batch.pk).exists()

    def test_permanent_delete_view_protected_error(
        self, authenticated_client, semen_batch
    ):
        semen_batch.soft_delete()
        url = reverse("genetics:semen-permanent-delete", args=[semen_batch.pk])

        with unittest.mock.patch(
            "apps.genetics.services.GeneticsService.hard_delete_semen_batch"
        ) as mock_delete:
            mock_delete.side_effect = ProtectedError("Protected", [])
            response = authenticated_client.post(url)
            assert response.status_code == 200
            assert "cannot delete this object" in response.content.decode().lower()

    def test_restore_view_get(self, authenticated_client, semen_batch):
        semen_batch.soft_delete()
        url = reverse("genetics:semen-restore", args=[semen_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/semen_confirm_restore.html" in [
            t.name for t in response.templates
        ]

    def test_restore_view_not_found(self, authenticated_client):
        url = reverse(
            "genetics:semen-restore", args=["00000000-0000-0000-0000-000000000000"]
        )
        response = authenticated_client.post(url)
        assert response.status_code == 302

        response_get = authenticated_client.get(url)
        assert response_get.status_code == 302

    def test_permanent_delete_view_get(self, authenticated_client, semen_batch):
        semen_batch.soft_delete()
        url = reverse("genetics:semen-permanent-delete", args=[semen_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/semen_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]

    def test_permanent_delete_view_not_found(self, authenticated_client):
        url = reverse(
            "genetics:semen-permanent-delete",
            args=["00000000-0000-0000-0000-000000000000"],
        )
        response = authenticated_client.post(url)
        assert response.status_code == 302

        response_get = authenticated_client.get(url)
        assert response_get.status_code == 302

    def test_create_view_context(self, authenticated_client):
        url = reverse("genetics:semen-create")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "title" in response.context

    def test_update_view_context(self, authenticated_client, semen_batch):
        url = reverse("genetics:semen-update", args=[semen_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "title" in response.context

    def test_trash_view(self, authenticated_client, semen_batch):
        semen_batch.soft_delete()
        url = reverse("genetics:semen-trash")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert semen_batch in response.context["semen_batches"]


# --- Embryo Batch Tests ---


class TestEmbryoBatchViews:
    def test_list_view(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert embryo_batch in response.context["embryo_batches"]

    def test_detail_view(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-detail", args=[embryo_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.context["batch"] == embryo_batch

    def test_create_view_post(self, authenticated_client, tank, bull, dam):
        url = reverse("genetics:embryo-create")
        data = {
            "tank": tank.pk,
            "canister": "C1",
            "initial_quantity": 5,
            "current_quantity": 5,
            "min_stock_alert": 2,
            "purchase_date": "2023-06-01",
            "cost_per_unit": 700.00,
            "sire": bull.pk,
            "dam": dam.pk,
            "grade": "1",
            "stage": "Blastocyst",
            "sire_name": "",  # Should use linked
            "dam_name": "",
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        assert EmbryoBatch.objects.filter(tank=tank, canister="C1").exists()

    def test_update_view_post(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-update", args=[embryo_batch.pk])
        data = {
            "tank": embryo_batch.tank.pk,
            "canister": "C2-Updated",
            "initial_quantity": 10,
            "current_quantity": 10,
            "min_stock_alert": 2,
            "purchase_date": "2023-01-01",
            "cost_per_unit": 500.00,
            "sire": embryo_batch.sire.pk,
            "dam": embryo_batch.dam.pk,
            "grade": "1",
            "stage": "Blastocyst",
            "sire_name": "",
            "dam_name": "",
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        embryo_batch.refresh_from_db()
        assert embryo_batch.canister == "C2-Updated"

    def test_stock_adjustment_view_get(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-adjust-stock", args=[embryo_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/stock_adjustment.html" in [t.name for t in response.templates]

    def test_stock_adjustment_view(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-adjust-stock", args=[embryo_batch.pk])

        # LOSS
        data = {"adjustment_type": "LOSS", "quantity": 2}
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        embryo_batch.refresh_from_db()
        assert embryo_batch.current_quantity == 8

        # FOUND
        data_found = {"adjustment_type": "FOUND", "quantity": 1}
        authenticated_client.post(url, data_found)
        embryo_batch.refresh_from_db()
        assert embryo_batch.current_quantity == 9

    def test_stock_adjustment_view_invalid(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-adjust-stock", args=[embryo_batch.pk])
        # Invalid data (missing quantity)
        data = {"adjustment_type": "LOSS"}
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        # Should render the template again
        assert "genetics/stock_adjustment.html" in [t.name for t in response.templates]

    def test_delete_view_post(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-delete", args=[embryo_batch.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        embryo_batch.refresh_from_db()
        assert embryo_batch.is_deleted is True

    def test_delete_view_protected_error(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-delete", args=[embryo_batch.pk])
        with unittest.mock.patch(
            "apps.genetics.services.GeneticsService.delete_embryo_batch"
        ) as mock_delete:
            mock_delete.side_effect = ProtectedError("Protected", [])
            response = authenticated_client.post(url)
            assert response.status_code == 200
            assert "cannot delete this object" in response.content.decode().lower()

    def test_restore_view(self, authenticated_client, embryo_batch):
        embryo_batch.soft_delete()
        url = reverse("genetics:embryo-restore", args=[embryo_batch.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        embryo_batch.refresh_from_db()
        assert embryo_batch.is_deleted is False

    def test_permanent_delete_view(self, authenticated_client, embryo_batch):
        embryo_batch.soft_delete()
        url = reverse("genetics:embryo-permanent-delete", args=[embryo_batch.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        assert not EmbryoBatch.objects.filter(pk=embryo_batch.pk).exists()

    def test_permanent_delete_view_protected_error(
        self, authenticated_client, embryo_batch
    ):
        embryo_batch.soft_delete()
        url = reverse("genetics:embryo-permanent-delete", args=[embryo_batch.pk])
        with unittest.mock.patch(
            "apps.genetics.services.GeneticsService.hard_delete_embryo_batch"
        ) as mock_delete:
            mock_delete.side_effect = ProtectedError("Protected", [])
            response = authenticated_client.post(url)
            assert response.status_code == 200
            assert "cannot delete this object" in response.content.decode().lower()

    def test_restore_view_get(self, authenticated_client, embryo_batch):
        embryo_batch.soft_delete()
        url = reverse("genetics:embryo-restore", args=[embryo_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/embryo_confirm_restore.html" in [
            t.name for t in response.templates
        ]

    def test_restore_view_not_found(self, authenticated_client):
        url = reverse(
            "genetics:embryo-restore", args=["00000000-0000-0000-0000-000000000000"]
        )
        response = authenticated_client.post(url)
        assert response.status_code == 302

        response_get = authenticated_client.get(url)
        assert response_get.status_code == 302

    def test_permanent_delete_view_get(self, authenticated_client, embryo_batch):
        embryo_batch.soft_delete()
        url = reverse("genetics:embryo-permanent-delete", args=[embryo_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "genetics/embryo_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]

    def test_permanent_delete_view_not_found(self, authenticated_client):
        url = reverse(
            "genetics:embryo-permanent-delete",
            args=["00000000-0000-0000-0000-000000000000"],
        )
        response = authenticated_client.post(url)
        assert response.status_code == 302

        response_get = authenticated_client.get(url)
        assert response_get.status_code == 302

    def test_create_view_context(self, authenticated_client):
        url = reverse("genetics:embryo-create")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "title" in response.context

    def test_update_view_context(self, authenticated_client, embryo_batch):
        url = reverse("genetics:embryo-update", args=[embryo_batch.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert "title" in response.context

    def test_trash_view(self, authenticated_client, embryo_batch):
        embryo_batch.soft_delete()
        url = reverse("genetics:embryo-trash")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert embryo_batch in response.context["embryo_batches"]
