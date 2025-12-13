import uuid

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from model_bakery import baker

from apps.purchases.models import Purchase


@pytest.mark.django_db
class TestPurchaseTrashViews:
    """Tests for Purchase trash, restore, and hard delete views."""

    def test_delete_view_get_confirmation(self, client, user):
        """Test GET request to delete view shows confirmation."""
        client.force_login(user)
        purchase = baker.make(Purchase)

        url = reverse("purchases:delete", kwargs={"pk": purchase.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "delete" in response.content.decode().lower()

    def test_delete_view_post(self, client, user):
        """Test soft deleting a purchase."""

    def test_trash_list_view(self, client, user):
        """Test PurchaseTrashListView (line 103)."""
        client.force_login(user)
        # Create deleted purchase (soft deleted)
        deleted_purchase = baker.make(Purchase)
        deleted_purchase.delete()

        # Create active purchase
        active_purchase = baker.make(Purchase)

        url = reverse("purchases:trash")
        response = client.get(url)

        assert response.status_code == 200
        # Should contain deleted only
        assert deleted_purchase in response.context["purchases"]
        assert active_purchase not in response.context["purchases"]

    def test_permanent_delete_post_not_found(self, client, user):
        """Test PurchasePermanentDeleteView POST handles non-existent pk."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("purchases:permanent-delete", kwargs={"pk": fake_uuid})

        response = client.post(url)
        assert response.status_code == 404

    def test_permanent_delete_get_not_found(self, client, user):
        """Test PurchasePermanentDeleteView GET handles non-existent pk."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("purchases:permanent-delete", kwargs={"pk": fake_uuid})

        response = client.get(url)
        assert response.status_code == 404

    def test_restore_view_post_not_found(self, client, user):
        """Test PurchaseRestoreView POST handles non-existent pk."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("purchases:restore", kwargs={"pk": fake_uuid})

        response = client.post(url)
        assert response.status_code == 404

    def test_restore_view_get_not_found(self, client, user):
        """Test PurchaseRestoreView GET handles non-existent pk."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("purchases:restore", kwargs={"pk": fake_uuid})

        response = client.get(url)
        assert response.status_code == 404

    def test_restore_view_post(self, client, user):
        """Test restoring a deleted purchase."""
        client.force_login(user)
        purchase = baker.make(Purchase)
        purchase.delete()

        restore_url = reverse("purchases:restore", kwargs={"pk": purchase.pk})
        response = client.post(restore_url, follow=True)

        assert response.status_code == 200
        assert Purchase.objects.filter(pk=purchase.pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("restored" in str(m).lower() for m in messages)

    def test_restore_view_get_confirmation(self, client, user):
        """Test GET request to restore view shows confirmation."""
        client.force_login(user)
        purchase = baker.make(Purchase)
        purchase.delete()

        restore_url = reverse("purchases:restore", kwargs={"pk": purchase.pk})
        response = client.get(restore_url)

        assert response.status_code == 200
        assert "confirm" in response.content.decode().lower()

    def test_hard_delete_view_post(self, client, user):
        """Test permanently deleting a purchase."""
        client.force_login(user)
        purchase = baker.make(Purchase)
        purchase.delete()  # Soft delete first

        delete_url = reverse("purchases:permanent-delete", kwargs={"pk": purchase.pk})
        response = client.post(delete_url, follow=True)

        assert response.status_code == 200
        assert not Purchase.all_objects.filter(pk=purchase.pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("permanently deleted" in str(m).lower() for m in messages)

    def test_hard_delete_view_get_confirmation(self, client, user):
        """Test GET request to hard delete view shows confirmation."""
        client.force_login(user)
        purchase = baker.make(Purchase)
        purchase.delete()

        delete_url = reverse("purchases:permanent-delete", kwargs={"pk": purchase.pk})
        response = client.get(delete_url)

        assert response.status_code == 200
        assert "delete permanent" in response.content.decode().lower()

    def test_restore_invalid_uuid(self, client, user):
        """Test restore with invalid UUID."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())

        response = client.post(reverse("purchases:restore", kwargs={"pk": fake_uuid}))
        assert response.status_code == 404

    def test_hard_delete_invalid_uuid(self, client, user):
        """Test hard delete with invalid UUID."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())

        response = client.post(
            reverse("purchases:permanent-delete", kwargs={"pk": fake_uuid})
        )
        assert response.status_code == 404
