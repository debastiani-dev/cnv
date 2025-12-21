import pytest
from django.urls import reverse
from model_bakery import baker

from apps.commercial.models import SalesEvent


@pytest.fixture(autouse=True)
def override_static_storage(settings):
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }


@pytest.mark.django_db
class TestSalesEventTrash:
    def test_soft_delete_event(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        event = baker.make(SalesEvent, name="Test Auction")

        # Verify it exists in main list
        url_list = reverse("commercial:event_list")
        response = client.get(url_list)
        assert event.name in str(response.content)

        # Soft delete via view
        url_delete = reverse("commercial:event_delete", kwargs={"pk": event.pk})
        # GET page
        response = client.get(url_delete)
        assert response.status_code == 200

        # POST to delete
        response = client.post(url_delete, follow=True)
        assert response.status_code == 200

        # Verify it is GONE from main list
        response = client.get(url_list)
        assert event.name not in str(response.content)

        # Verify it is in Trash
        event.refresh_from_db()
        assert event.is_deleted is True

        url_trash = reverse("commercial:event_trash")
        response = client.get(url_trash)
        assert event.name in str(response.content)

    def test_restore_event(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        event = baker.make(SalesEvent, name="Deleted Auction", is_deleted=True)

        # Restore via view
        url_restore = reverse("commercial:event_restore", kwargs={"pk": event.pk})
        response = client.post(url_restore, follow=True)
        assert response.status_code == 200

        event.refresh_from_db()
        assert event.is_deleted is False

        # Verify back in main list
        url_list = reverse("commercial:event_list")
        response = client.get(url_list)
        assert event.name in str(response.content)

    def test_permanent_delete_event(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        event = baker.make(SalesEvent, name="To Delete Forever", is_deleted=True)

        # Hard delete via view
        url_perm_delete = reverse(
            "commercial:event_permanent_delete", kwargs={"pk": event.pk}
        )
        response = client.post(url_perm_delete, follow=True)
        assert response.status_code == 200

        # Verify it is GONE from DB
        assert not SalesEvent.all_objects.filter(pk=event.pk).exists()
