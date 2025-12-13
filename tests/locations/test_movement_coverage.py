# pylint: disable=protected-access
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.locations.models import Location


@pytest.mark.django_db
class TestMovementViewsCoverage:

    def test_move_no_cattle_selected(self, client, django_user_model):
        """Test MovementCreateView no cattle selected (lines 40-41)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        location = baker.make(Location)

        url = reverse("locations:move")
        # Don't provide cattle_ids at all - will be None/empty in cleaned_data
        # Form validation will pass because cattle_ids is not required
        # But form_valid will catch it on line 39
        data = {
            "destination": location.pk,
            "reason": "ROTATION",  # Fixed: use valid reason value
            "date": "2024-01-01",
            # cattle_ids intentionally omitted
        }

        response = client.post(url, data)

        # Should return 200 with form_invalid (lines 40-41)
        assert response.status_code == 200
        messages = list(response.wsgi_request._messages)
        assert any("No cattle selected" in str(m) for m in messages)

    def test_move_invalid_cattle_selection(self, client, django_user_model):
        """Test MovementCreateView invalid cattle selection (lines 47-48)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        location = baker.make(Location)

        url = reverse("locations:move")
        # Provide UUIDs that don't exist in the database
        # Form will be valid, but cattle query will return empty list
        data = {
            "destination": location.pk,
            "reason": "ROTATION",  # Fixed: use valid reason value
            "date": "2024-01-01",
            "cattle_ids": (
                "00000000-0000-0000-0000-000000000001,00000000-0000-0000-0000-000000000002"
            ),
        }

        response = client.post(url, data)

        # Should return 200 with form_invalid (lines 47-48)
        assert response.status_code == 200
        messages_list = list(response.wsgi_request._messages)
        if not any("Invalid cattle selection" in str(m) for m in messages_list):
            # Debug: print actual messages
            print(f"Messages: {[str(m) for m in messages_list]}")
        assert any("Invalid cattle selection" in str(m) for m in messages_list)

    def test_move_service_validation_error(self, client, django_user_model):
        """Test MovementCreateView service ValidationError (lines 60-63)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        location = baker.make(Location)
        cattle = baker.make(Cattle)

        url = reverse("locations:move")
        data = {
            "destination": location.pk,
            "cattle_ids": str(cattle.pk),
            "reason": "ROTATION",  # Fixed: use valid reason value
            "date": "2024-01-01",
        }

        # Mock service to raise ValidationError
        with patch(
            "apps.locations.services.movement_service.MovementService.move_cattle",
            side_effect=ValidationError("Service Error"),
        ):
            response = client.post(url, data)

            # Should return 200 with form_invalid (lines 60-63)
            assert response.status_code == 200
            messages_list = list(response.wsgi_request._messages)
            if not any("Service Error" in str(m) for m in messages_list):
                # Debug: print actual messages
                print(f"Messages: {[str(m) for m in messages_list]}")
            assert any("Service Error" in str(m) for m in messages_list)

    def test_move_post_no_destination_no_cattle(self, client, django_user_model):
        """Test MovementCreateView POST without destination and no cattle (lines 73-74)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse("locations:move")
        # POST without 'destination' field and without cattle_ids
        response = client.post(url, {})

        # Should redirect to cattle list with error
        assert response.status_code == 302
        assert response.url == reverse("cattle:list")
        messages = list(response.wsgi_request._messages)
        assert any("No cattle selected" in str(m) for m in messages)

    def test_move_get_cattle_ids_from_get(self, client, django_user_model):
        """Test _get_cattle_ids from GET parameters (line 87)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        cattle = baker.make(Cattle)

        # Access with GET parameters
        url = reverse("locations:move")
        response = client.get(url, {"cattle_ids": [str(cattle.pk)]})

        # Should render the form
        assert response.status_code == 200
        assert "form" in response.context

    def test_move_get_cattle_ids_empty(self, client, django_user_model):
        """Test _get_cattle_ids returns empty list (line 103)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Access without cattle_ids
        url = reverse("locations:move")
        response = client.get(url)

        # Should still render (might show empty form or redirect based on implementation)
        assert response.status_code in [200, 302]
