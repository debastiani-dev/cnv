from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.cattle.services.cattle_service import CattleService
from tests.test_utils import verify_redirect_with_message


@pytest.mark.django_db
class TestCattleCoverage:
    """Tests to cover missing lines in cattle models and views."""

    def test_cattle_age_with_negative_months(self):
        """Test cattle age calculation with negative months (lines 256-257)."""
        # Lines 256-257 execute when diff_months < 0
        # Meaning: today.month < birth_date.month
        #
        # Use time mocking to ensure this always works, even in December!

        # Mock today to be June 10, 2024 (month = 6)
        mock_today = date(2024, 6, 10)

        # Birth in July 2023 (month = 7)
        # diff_years = 2024 - 2023 = 1
        # diff_months = 6 - 7 = -1 (NEGATIVE!)
        # Line 256: diff_years = 1 - 1 = 0
        # Line 257: diff_months = -1 + 12 = 11
        # Result: "11m"
        birth_date = date(2023, 7, 15)

        cattle = baker.make(Cattle, birth_date=birth_date)

        # Mock date.today() to return our fixed date
        with patch("apps.cattle.models.cattle.date") as mock_date:
            mock_date.today.return_value = mock_today
            age_str = cattle.age

        # Should execute lines 256-257 and return "11m"
        assert age_str == "11m"

    def test_cattle_detail_view_context(self, client, django_user_model):
        """Test CattleDetailView get_context_data (lines 33-36)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        cattle = baker.make(Cattle)
        url = reverse("cattle:detail", kwargs={"pk": cattle.pk})
        response = client.get(url)

        # Should render with health_events and weight_history in context (lines 33-36)
        assert response.status_code == 200
        assert "health_events" in response.context
        assert "weight_history" in response.context

    def test_cattle_create_view_context(self, client, django_user_model):
        """Test CattleCreateView get_context_data (lines 79-81)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse("cattle:create")
        response = client.get(url)

        # Should render with title "Add Cattle" (lines 79-81)
        assert response.status_code == 200
        assert response.context["title"] == "Add Cattle"

    def test_cattle_update_view_context(self, client, django_user_model):
        """Test CattleUpdateView get_context_data (lines 95-97)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        cattle = baker.make(Cattle)
        url = reverse("cattle:update", kwargs={"pk": cattle.pk})
        response = client.get(url)

        # Should render with title "Edit Cattle" (lines 95-97)
        assert response.status_code == 200
        assert response.context["title"] == "Edit Cattle"

    def test_cattle_delete_view_delete_method(self, client, django_user_model):
        """Test CattleDeleteView delete method (line 111)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        cattle = baker.make(Cattle)
        url = reverse("cattle:delete", kwargs={"pk": cattle.pk})

        # Calling DELETE method should delegate to POST (line 111)
        response = client.delete(url)

        # Should redirect after soft delete
        assert response.status_code == 302

    def test_cattle_restore_post_value_error(self, client, django_user_model):
        """Test CattleRestoreView POST ValueError handler (lines 136-137)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        cattle = baker.make(Cattle)
        cattle.delete()

        url = reverse("cattle:restore", kwargs={"pk": cattle.pk})

        # Mock service to raise ValueError
        with patch.object(
            CattleService, "restore_cattle", side_effect=ValueError("Cannot restore")
        ):
            response = client.post(url)

            # Should redirect with error message (lines 136-137)
            assert response.status_code == 302
            messages = list(get_messages(response.wsgi_request))
            assert any("Cannot restore" in str(m) for m in messages)

    def test_cattle_restore_post_does_not_exist(self, client, django_user_model):
        """Test CattleRestoreView POST DoesNotExist handler (lines 138-139)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Use a UUID that doesn't exist
        fake_uuid = "00000000-0000-0000-0000-000000000001"
        url = reverse("cattle:restore", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="post")

    def test_cattle_restore_get_does_not_exist(self, client, django_user_model):
        """Test CattleRestoreView GET DoesNotExist handler (lines 149-151)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Use a UUID that doesn't exist
        fake_uuid = "00000000-0000-0000-0000-000000000001"
        url = reverse("cattle:restore", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="get")

    def test_cattle_hard_delete_post_does_not_exist(self, client, django_user_model):
        """Test CattlePermanentDeleteView POST DoesNotExist (line 160)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Use a UUID that doesn't exist
        fake_uuid = "00000000-0000-0000-0000-000000000001"
        url = reverse("cattle:permanent-delete", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="post")

    def test_cattle_hard_delete_get_does_not_exist(self, client, django_user_model):
        """Test CattlePermanentDeleteView GET DoesNotExist (lines 183-185)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Use a UUID that doesn't exist
        fake_uuid = "00000000-0000-0000-0000-000000000001"
        url = reverse("cattle:permanent-delete", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="get")
