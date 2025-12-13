# pylint: disable=protected-access
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.locations.models import Location


@pytest.mark.django_db
class TestLocationViewsCoverage:

    def test_restore_post_does_not_exist(self, client, django_user_model):
        """Test LocationRestoreView POST DoesNotExist (lines 157-158)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Invalid UUID
        url = reverse(
            "locations:restore", kwargs={"pk": "00000000-0000-0000-0000-000000000000"}
        )
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("locations:list")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m).lower() for m in messages)

    def test_restore_get_does_not_exist(self, client, django_user_model):
        """Test LocationRestoreView GET DoesNotExist (lines 170-172)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "locations:restore", kwargs={"pk": "00000000-0000-0000-0000-000000000000"}
        )
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("locations:list")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m).lower() for m in messages)

    def test_hard_delete_post_does_not_exist(self, client, django_user_model):
        """Test LocationPermanentDeleteView POST DoesNotExist (line 181)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "locations:hard-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("locations:trash")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m).lower() for m in messages)

    def test_hard_delete_post_nested_does_not_exist(self, client, django_user_model):
        """Test LocationPermanentDeleteView POST nested DoesNotExist (lines 192-193)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Create and soft delete a location
        location = baker.make(Location)
        location_pk = location.pk
        location.delete()  # Soft delete

        url = reverse("locations:hard-delete", kwargs={"pk": location_pk})

        # Mock service to raise ValidationError, then mock get() to raise DoesNotExist
        with patch(
            "apps.locations.services.location_service.LocationService.hard_delete_location",
            side_effect=ValidationError("Error"),
        ):
            with patch(
                "apps.locations.models.location.Location.all_objects.get",
                side_effect=Location.DoesNotExist,
            ):
                response = client.post(url)

                # Should redirect to trash despite nested DoesNotExist (lines 192-193)
                assert response.status_code == 302
                assert response.url == reverse("locations:trash")

    def test_hard_delete_get_does_not_exist(self, client, django_user_model):
        """Test LocationPermanentDeleteView GET DoesNotExist (lines 205-207)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "locations:hard-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("locations:trash")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m).lower() for m in messages)
