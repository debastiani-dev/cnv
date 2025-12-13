from unittest.mock import patch

# pylint: disable=redefined-outer-name
import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.cattle.services.cattle_service import CattleService


@pytest.fixture
def cattle_auth_client(client, django_user_model):
    user = baker.make(django_user_model)
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestCattleCrudViews:
    def test_create_view(self, cattle_auth_client):
        url = reverse("cattle:create")
        data = {
            "tag": "NEWCOW",
            "name": "Bessie",
            "sex": Cattle.SEX_FEMALE,
            "status": Cattle.STATUS_AVAILABLE,
            "birth_date": "2024-01-01",
        }
        response = cattle_auth_client.post(url, data)
        assert response.status_code == 302
        assert Cattle.objects.filter(tag="NEWCOW").exists()

    def test_update_view(self, cattle_auth_client):
        cow = baker.make(Cattle, tag="OLDTAG")
        url = reverse("cattle:update", kwargs={"pk": cow.pk})
        data = {
            "tag": "NEWTAG",
            "name": "Updated Name",
            "sex": cow.sex,
            "status": cow.status,
            "birth_date": "2024-01-01",
        }
        response = cattle_auth_client.post(url, data)
        assert response.status_code == 302
        cow.refresh_from_db()
        assert cow.tag == "NEWTAG"

    def test_delete_view_get_confirmation(self, cattle_auth_client):
        cow = baker.make(Cattle)
        url = reverse("cattle:delete", kwargs={"pk": cow.pk})
        response = cattle_auth_client.get(url)
        assert response.status_code == 200
        # Checking for "Delete" or similar in template
        assert "delete" in response.content.decode().lower()

    def test_delete_view_post(self, cattle_auth_client):
        cow = baker.make(Cattle)
        url = reverse("cattle:delete", kwargs={"pk": cow.pk})
        response = cattle_auth_client.post(url)
        assert response.status_code == 302
        assert not Cattle.objects.filter(pk=cow.pk).exists()
        assert Cattle.all_objects.filter(pk=cow.pk, is_deleted=True).exists()

    def test_delete_view_exception(self, cattle_auth_client):
        cow = baker.make(Cattle)
        url = reverse("cattle:delete", kwargs={"pk": cow.pk})

        # Mock delete to raise exception
        with patch.object(
            CattleService, "delete_cattle", side_effect=ProtectedError("Protected", [])
        ):
            response = cattle_auth_client.post(url)

        assert response.status_code == 200
        assert (
            "cannot delete" in response.content.decode().lower()
            or "referenced" in response.content.decode().lower()
        )

    def test_trash_list_view(self, cattle_auth_client):
        cow = baker.make(Cattle)
        cow.delete()
        url = reverse("cattle:trash")
        response = cattle_auth_client.get(url)
        assert response.status_code == 200
        assert cow in response.context["cattle_list"]

    def test_restore_view_get_confirmation(self, cattle_auth_client):
        cow = baker.make(Cattle)
        cow.delete()
        url = reverse("cattle:restore", kwargs={"pk": cow.pk})
        response = cattle_auth_client.get(url)
        assert response.status_code == 200
        assert "restore" in response.content.decode().lower()

    def test_restore_view_post(self, cattle_auth_client):
        cow = baker.make(Cattle)
        cow.delete()
        url = reverse("cattle:restore", kwargs={"pk": cow.pk})
        response = cattle_auth_client.post(url)
        assert response.status_code == 302
        assert Cattle.objects.filter(pk=cow.pk).exists()

    def test_hard_delete_view_get_confirmation(self, cattle_auth_client):
        cow = baker.make(Cattle)
        cow.delete()
        url = reverse("cattle:permanent-delete", kwargs={"pk": cow.pk})
        response = cattle_auth_client.get(url)
        assert response.status_code == 200
        assert "permanently" in response.content.decode().lower()

    def test_hard_delete_view_post(self, cattle_auth_client):
        cow = baker.make(Cattle)
        cow.delete()
        url = reverse("cattle:permanent-delete", kwargs={"pk": cow.pk})
        response = cattle_auth_client.post(url)
        assert response.status_code == 302
        assert not Cattle.all_objects.filter(pk=cow.pk).exists()

    def test_hard_delete_view_exception(self, cattle_auth_client):
        cow = baker.make(Cattle)
        cow.delete()
        url = reverse("cattle:permanent-delete", kwargs={"pk": cow.pk})

        with patch.object(
            CattleService,
            "hard_delete_cattle",
            side_effect=ProtectedError("Protected", []),
        ):
            response = cattle_auth_client.post(url)

        assert response.status_code == 200
        assert (
            "cannot delete" in response.content.decode().lower()
            or "referenced" in response.content.decode().lower()
        )
