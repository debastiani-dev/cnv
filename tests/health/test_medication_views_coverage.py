from unittest.mock import patch

import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.health.models import Medication
from apps.health.models.health import MedicationType


@pytest.mark.django_db
class TestMedicationViewsCoverage:

    def test_list_view_filters(self, client, django_user_model):
        """Test search and type filters in MedicationListView."""
        user = baker.make(django_user_model)
        client.force_login(user)

        med1 = baker.make(
            Medication, name="Alpha Med", medication_type=MedicationType.VACCINE
        )
        med2 = baker.make(
            Medication, name="Beta drug", medication_type=MedicationType.ANTIBIOTIC
        )

        url = reverse("health:medication-list")

        # Test Search (Name)
        response = client.get(url, {"q": "Alpha"})
        assert med1 in response.context["medications"]
        assert med2 not in response.context["medications"]

        # Test Filter (Type)
        response = client.get(url, {"type": MedicationType.ANTIBIOTIC})
        assert med1 not in response.context["medications"]
        assert med2 in response.context["medications"]

    def test_create_and_update_view_context(self, client, django_user_model):
        """Test context data in Create/Update views."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Create View
        url_create = reverse("health:medication-create")
        response = client.get(url_create)
        assert response.context["title"] == "Add Medication"

        # Update View
        med = baker.make(Medication)
        url_update = reverse("health:medication-update", kwargs={"pk": med.pk})
        response = client.get(url_update)
        assert response.context["title"] == "Edit Medication"

    def test_trash_list_view(self, client, django_user_model):
        """Test MedicationTrashListView."""
        user = baker.make(django_user_model)
        client.force_login(user)

        med = baker.make(Medication)
        med.delete()

        url = reverse("health:medication-trash")
        response = client.get(url)
        assert med in response.context["medications"]

    def test_restore_view_get_exception(self, client, django_user_model):
        """Test restore view GET with invalid PK."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "health:medication-restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)
        # Should redirect to list and show error
        assert response.status_code == 302
        assert response.url == reverse("health:medication-list")

    def test_restore_view_post_exception(self, client, django_user_model):
        """Test restore view POST with service error."""
        user = baker.make(django_user_model)
        client.force_login(user)
        med = baker.make(Medication)
        med.delete()

        url = reverse("health:medication-restore", kwargs={"pk": med.pk})

        # Mock service to raise ValueError
        with patch(
            "apps.health.services.HealthService.restore_medication",
            side_effect=ValueError("Restore Error"),
        ):
            response = client.post(url)
            assert response.status_code == 302
            # Should have error message (cannot easily check messages without scanning response content fully or checking storage, but 302 implies handled)

        # Mock DoesNotExist
        url_invalid = reverse(
            "health:medication-restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url_invalid)
        assert response.status_code == 302

    def test_permanent_delete_view_get_exception(self, client, django_user_model):
        """Test permanent delete GET with invalid PK."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "health:medication-permanent-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("health:medication-trash")

    def test_permanent_delete_view_post_exceptions(self, client, django_user_model):
        """Test permanent delete POST with exceptions."""
        user = baker.make(django_user_model)
        client.force_login(user)
        med = baker.make(Medication)
        med.delete()

        url = reverse("health:medication-permanent-delete", kwargs={"pk": med.pk})

        # 1. ProtectedError
        with patch(
            "apps.health.services.HealthService.hard_delete_medication",
            side_effect=ProtectedError("Protected", []),
        ):
            # Mock all_objects.get to return med for template
            with patch(
                "apps.health.models.Medication.all_objects.get", return_value=med
            ):
                response = client.post(url)
                assert response.status_code == 200  # Renders error template
                assert "error" in response.context

        # 2. DoesNotExist
        url_invalid = reverse(
            "health:medication-permanent-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url_invalid)
        assert response.status_code == 302
