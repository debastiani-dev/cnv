import uuid

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from model_bakery import baker

from apps.sales.models import Sale


@pytest.mark.django_db
class TestSaleTrashViews:
    """Tests for Sale trash, restore, and hard delete views."""

    def test_delete_view_get_confirmation(self, client, user):
        """Test GET request to delete view shows confirmation."""
        client.force_login(user)
        sale = baker.make(Sale)

        url = reverse("sales:delete", kwargs={"pk": sale.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "delete" in response.content.decode().lower()

    def test_delete_view_post(self, client, user):
        """Test soft deleting a sale."""
        client.force_login(user)
        sale = baker.make(Sale)

        url = reverse("sales:delete", kwargs={"pk": sale.pk})
        response = client.post(url, follow=True)

        assert response.status_code == 200
        assert not Sale.objects.filter(pk=sale.pk).exists()
        assert Sale.all_objects.filter(pk=sale.pk, is_deleted=True).exists()

    def test_trash_list_view(self, client, user):
        """Test that trash list view displays deleted sales."""
        client.force_login(user)
        active_sale = baker.make(Sale)
        deleted_sale = baker.make(Sale)
        deleted_sale.delete()  # Soft delete

        response = client.get(reverse("sales:trash"))

        assert response.status_code == 200
        assert deleted_sale in response.context["sales"]
        assert active_sale not in response.context["sales"]

    def test_restore_view_post(self, client, user):
        """Test restoring a deleted sale."""
        client.force_login(user)
        sale = baker.make(Sale)
        sale.delete()

        restore_url = reverse("sales:restore", kwargs={"pk": sale.pk})
        response = client.post(restore_url, follow=True)

        assert response.status_code == 200
        assert Sale.objects.filter(pk=sale.pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("restored" in str(m).lower() for m in messages)

    def test_restore_view_get_confirmation(self, client, user):
        """Test GET request to restore view shows confirmation."""
        client.force_login(user)
        sale = baker.make(Sale)
        sale.delete()

        restore_url = reverse("sales:restore", kwargs={"pk": sale.pk})
        response = client.get(restore_url)

        assert response.status_code == 200
        assert (
            "confirm" in response.content.decode().lower()
            or "restore" in response.content.decode().lower()
        )

    def test_hard_delete_view_post(self, client, user):
        """Test permanently deleting a sale."""
        client.force_login(user)
        sale = baker.make(Sale)
        sale.delete()  # Soft delete first

        delete_url = reverse("sales:permanent-delete", kwargs={"pk": sale.pk})
        response = client.post(delete_url, follow=True)

        assert response.status_code == 200
        assert not Sale.all_objects.filter(pk=sale.pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("permanently deleted" in str(m).lower() for m in messages)

    def test_hard_delete_view_get_confirmation(self, client, user):
        """Test GET request to hard delete view shows confirmation."""
        client.force_login(user)
        sale = baker.make(Sale)
        sale.delete()

        delete_url = reverse("sales:permanent-delete", kwargs={"pk": sale.pk})
        response = client.get(delete_url)

        assert response.status_code == 200
        # Check for title or button text as observed in purchases
        assert (
            "delete permanent" in response.content.decode().lower()
            or "cannot be undone" in response.content.decode().lower()
        )

    def test_restore_invalid_uuid(self, client, user):
        """Test restore with invalid UUID."""
        client.force_login(user)
        fake_uuid = str(uuid.uuid4())

        response = client.post(reverse("sales:restore", kwargs={"pk": fake_uuid}))
        assert response.status_code == 404

    def test_hard_delete_invalid_uuid(self, client, user):
        """Test hard delete with invalid UUID."""
        client.force_login(user)
        fake_uuid = str(uuid.uuid4())

        response = client.post(
            reverse("sales:permanent-delete", kwargs={"pk": fake_uuid})
        )
        assert response.status_code == 404
