from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.health.models import Medication, SanitaryEvent
from apps.health.models.health import MedicationType


@pytest.mark.django_db
class TestSanitaryEventViewsCoverage:

    def test_create_view_initial_get(self, client, django_user_model):
        """Test GET request (not really used but standard access)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        url = reverse("health:event-create")
        response = client.get(url)
        # FormView GET usually renders empty form
        assert response.status_code == 200

    def test_create_view_post_initial_valid(self, client, django_user_model):
        """Test POST with cattle_ids only (rendering initial form)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        cattle = baker.make(Cattle, _quantity=2)
        cattle_ids = [str(c.pk) for c in cattle]

        url = reverse("health:event-create")
        response = client.post(url, {"cattle_ids": cattle_ids})

        assert response.status_code == 200
        assert "cattle_ids" in response.context
        assert len(response.context["selected_cattle"]) == 2

    def test_create_view_post_no_cattle(self, client, django_user_model):
        """Test POST with no cattle_ids redirects."""
        user = baker.make(django_user_model)
        client.force_login(user)
        url = reverse("health:event-create")
        response = client.post(url, {})  # No cattle_ids

        assert response.status_code == 302
        assert response.url == reverse("cattle:list")
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0

    def test_create_view_post_save_action_valid(self, client, django_user_model):
        """Test actual creation submission."""
        user = baker.make(django_user_model)
        client.force_login(user)
        cattle = baker.make(Cattle)
        med = baker.make(Medication, name="TestMeds")

        url = reverse("health:event-create")
        data = {
            "cattle_ids": [str(cattle.pk)],
            "action": "save_event",
            "date": "2024-01-01",
            "title": "Test Event",
            "medication": med.pk,
            "total_cost": "100.00",
        }

        with patch(
            "apps.health.services.HealthService.create_batch_event"
        ) as mock_create:
            response = client.post(url, data)
            assert response.status_code == 302  # Success redirect
            mock_create.assert_called_once()
            # Verify user was injected
            args, kwargs = mock_create.call_args
            assert kwargs["event_data"]["performed_by"] == user

    def test_create_view_post_save_action_invalid(self, client, django_user_model):
        """Test actual creation submission invalid form."""
        user = baker.make(django_user_model)
        client.force_login(user)
        cattle = baker.make(Cattle)

        url = reverse("health:event-create")
        data = {
            "cattle_ids": [str(cattle.pk)],
            "action": "save_event",
            # Missing required fields
        }

        response = client.post(url, data)
        assert response.status_code == 200
        assert response.context["form"].errors
        assert "cattle_ids" in response.context  # Context preserved

    def test_create_view_exception_handling(self, client, django_user_model):
        """Test exception handling during creation service call."""
        user = baker.make(django_user_model)
        client.force_login(user)
        cattle = baker.make(Cattle)
        med = baker.make(Medication)

        url = reverse("health:event-create")
        data = {
            "cattle_ids": [str(cattle.pk)],
            "action": "save_event",
            "date": "2024-01-01",
            "title": "Test Event",
            "medication": med.pk,
            "total_cost": "100.00",
        }

        with patch(
            "apps.health.services.HealthService.create_batch_event",
            side_effect=Exception("Service Fail"),
        ):
            response = client.post(url, data)
            assert response.status_code == 200  # Re-renders form
            messages = list(get_messages(response.wsgi_request))
            assert str(messages[0]) == "Service Fail"

    def test_list_view_filters(self, client, django_user_model):
        """Test list view filters."""
        user = baker.make(django_user_model)
        client.force_login(user)

        med_vac = baker.make(Medication, medication_type=MedicationType.VACCINE)
        med_ant = baker.make(Medication, medication_type=MedicationType.ANTIBIOTIC)

        ev1 = baker.make(
            SanitaryEvent,
            title="Vaccination A",
            medication=med_vac,
            notes="Note A",
            performed_by=user,
        )
        ev2 = baker.make(
            SanitaryEvent,
            title="Treatment B",
            medication=med_ant,
            notes="Note B",
            performed_by=user,
        )

        url = reverse("health:event-list")

        # Test Search (Title)
        response = client.get(url, {"q": "Vaccination"})
        assert ev1 in response.context["events"]
        assert ev2 not in response.context["events"]

        # Test Filter (Medication Type)
        response = client.get(url, {"medication_type": MedicationType.ANTIBIOTIC})
        assert ev1 not in response.context["events"]
        assert ev2 in response.context["events"]

    def test_detail_view_context(self, client, django_user_model):
        """Test detail view context includes targets."""
        user = baker.make(django_user_model)
        client.force_login(user)
        event = baker.make(SanitaryEvent, performed_by=user)

        url = reverse("health:event-detail", kwargs={"pk": event.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "targets" in response.context

    def test_update_view_context(self, client, django_user_model):
        """Test update view context includes targets."""
        user = baker.make(django_user_model)
        client.force_login(user)
        event = baker.make(SanitaryEvent, performed_by=user)

        url = reverse("health:event-update", kwargs={"pk": event.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "targets" in response.context

    def test_delete_view_exception(self, client, django_user_model):
        """Test exceptions in DeleteView logic."""
        user = baker.make(django_user_model)
        client.force_login(user)
        event = baker.make(SanitaryEvent, performed_by=user)

        url = reverse("health:event-delete", kwargs={"pk": event.pk})

        # Mocking super().form_valid to raise exception (simulate delete failure)
        # Since we can't easily patch super(), we patch the object delete method which it calls?
        # Standard DeleteView calls self.object.delete().
        # BUT SanitaryEvent uses SoftDelete, so delete() just sets flag.
        # Let's patch SanitaryEvent.delete

        with patch.object(
            SanitaryEvent, "delete", side_effect=Exception("Delete Fail")
        ):
            # We need to bypass get_object or ensure it returns our patched object?
            # Easier is to patch HealthService.create_batch_event or similar if it was a service call,
            # but here it is standard view.
            # Actually, simpler: patch DeleteView.form_valid ? No, that's what we are testing.
            # Patching the model delete method on the CLASS should work for the instance fetched by view.
            response = client.post(url)
            assert response.status_code == 302
            assert response.url == reverse("health:event-list")
            # Verify message?

    def test_hard_delete_view_exception(self, client, django_user_model):
        """Test exceptions in HardDeleteView."""
        user = baker.make(django_user_model)
        client.force_login(user)
        event = baker.make(SanitaryEvent, performed_by=user)
        event.delete()  # Soft delete first

        url = reverse("health:event-hard-delete", kwargs={"pk": event.pk})

        with patch(
            "apps.health.services.HealthService.hard_delete_event",
            side_effect=Exception("Hard Delete Fail"),
        ):
            response = client.post(url)
            assert response.status_code == 200  # Renders error template
            assert "error" in response.context
