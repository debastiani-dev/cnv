from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.authentication.models.user import User
from apps.cattle.models import Cattle


@pytest.mark.django_db
class TestCattleDeleteViewValidation:

    def test_delete_view_handles_validation_error(self, client):
        user = baker.make(User)
        client.force_login(user)
        cattle = baker.make(Cattle)
        url = reverse("cattle:delete", kwargs={"pk": cattle.pk})

        # Patch the service to raise ValidationError
        with patch("apps.cattle.views.CattleService.delete_cattle") as mock_delete:
            mock_delete.side_effect = ValidationError("Cannot delete linked cattle")

            response = client.post(url)

            # Should re-render the page (200), not redirect (302)
            assert response.status_code == 200
            assert "cattle/cattle_confirm_delete.html" in [
                t.name for t in response.templates
            ]
            assert "error" in response.context
            assert response.context["error"] == "Cannot delete linked cattle"

    def test_permanent_delete_view_handles_validation_error(self, client):
        user = baker.make(User)
        client.force_login(user)
        # Create soft-deleted cattle
        cattle = baker.make(Cattle, is_deleted=True)
        url = reverse("cattle:permanent-delete", kwargs={"pk": cattle.pk})

        with patch("apps.cattle.views.CattleService.hard_delete_cattle") as mock_delete:
            mock_delete.side_effect = ValidationError("Cannot delete linked cattle")

            response = client.post(url)

            assert response.status_code == 200
            # Template might be tricky to match exactly depending on inheritance, but checking context is key
            assert "error" in response.context
            assert response.context["error"] == "Cannot delete linked cattle"
