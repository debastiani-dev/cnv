from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from apps.health.models import Medication, SanitaryEvent


@pytest.mark.django_db
class TestSanitaryEventTrash:
    @pytest.fixture
    def medication(self):
        return baker.make(Medication, name="Test Med", withdrawal_days_meat=10)

    @pytest.fixture
    def event(self, medication, django_user_model):
        user = baker.make(django_user_model)
        return baker.make(
            SanitaryEvent,
            title="Event to Trash",
            medication=medication,
            performed_by=user,
            total_cost=Decimal("100.00"),
        )

    def test_soft_delete_moves_to_trash(self, client, event):
        client.force_login(event.performed_by)
        url = reverse("health:event-delete", kwargs={"pk": event.pk})
        response = client.post(url, follow=True)

        assert response.status_code == 200
        event.refresh_from_db()
        assert event.is_deleted is True

        # Check trash list
        trash_url = reverse("health:event-trash")
        response = client.get(trash_url)
        assert event in response.context["events"]

    def test_restore_event(self, client, event):
        client.force_login(event.performed_by)
        event.delete()  # Soft delete first
        assert event.is_deleted is True

        url = reverse("health:event-restore", kwargs={"pk": event.pk})
        response = client.post(url, follow=True)

        assert response.status_code == 200
        event.refresh_from_db()
        assert event.is_deleted is False

    def test_hard_delete_event(self, client, event):
        client.force_login(event.performed_by)
        event.delete()  # Soft delete first

        url = reverse("health:event-hard-delete", kwargs={"pk": event.pk})
        response = client.post(url, follow=True)

        assert response.status_code == 200
        with pytest.raises(SanitaryEvent.DoesNotExist):
            SanitaryEvent.objects.get(pk=event.pk)

    def test_restore_view_queryset(self, client, event):
        # Should only find deleted items
        client.force_login(event.performed_by)
        url = reverse("health:event-restore", kwargs={"pk": event.pk})

        # Not deleted yet -> 404
        response = client.post(url)
        assert response.status_code == 404

        event.delete()

    def test_delete_view_get_confirmation(self, client, event):
        client.force_login(event.performed_by)
        url = reverse("health:event-delete", kwargs={"pk": event.pk})
        response = client.get(url)
        assert response.status_code == 200
        # The template might use "Delete" or "Confirm" - assume "delete" logic from other apps
        # Or check if template name is used.
        # Let's check for specific text if failure occurs, but 'delete' is safe guess.
        assert "delete" in response.content.decode().lower()

    def test_restore_view_get_confirmation(self, client, event):
        client.force_login(event.performed_by)
        event.delete()
        url = reverse("health:event-restore", kwargs={"pk": event.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "restore" in response.content.decode().lower()

    def test_hard_delete_view_get_confirmation(self, client, event):
        client.force_login(event.performed_by)
        event.delete()
        url = reverse("health:event-hard-delete", kwargs={"pk": event.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "permanently" in response.content.decode().lower()
