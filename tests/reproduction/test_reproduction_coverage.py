# pylint: disable=protected-access


import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from tests.test_utils import create_pregnant_dam, verify_post_with_mocked_exception


@pytest.mark.django_db
class TestReproductionCoverage:

    # --- Breeding Views Coverage ---

    def test_breeding_restore_post_does_not_exist(self, client, django_user_model):
        """Test restore breeding event POST when DoesNotExist (lines 95-96)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Invalid UUID
        url = reverse(
            "reproduction:breeding_restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        # Should redirect to list with error
        assert response.status_code == 302
        assert response.url == reverse("reproduction:breeding_list")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m) for m in messages)

    def test_breeding_hard_delete_post_does_not_exist(self, client, django_user_model):
        """Test hard delete breeding event POST when DoesNotExist (lines 118-119)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "reproduction:breeding_permanent_delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("reproduction:breeding_trash")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m) for m in messages)

    def test_breeding_delete_post_does_not_exist(self, client, django_user_model):
        """Test delete breeding event POST when DoesNotExist (lines 142-143)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "reproduction:breeding_delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("reproduction:breeding_list")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m) for m in messages)

    # --- Calving Views Coverage ---

    def test_calving_create_service_exception(self, client, django_user_model):
        """Test CalvingCreateView exception handling (lines 79-81)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        dam, breeding = create_pregnant_dam()

        url = reverse("reproduction:calving_add")
        data = {
            "dam": dam.pk,
            "date": "2024-01-01",
            "breeding_event": breeding.pk,
            # Calf Data
            "calf_tag": "CALF001",
            "calf_name": "Test Calf",
            "calf_sex": Cattle.SEX_MALE,
            "calf_weight": "40.0",
            "ease_of_birth": "EASY",
            "notes": "Test notes",
        }

        # Mock ReproductionService.register_birth to raise ValidationError
        verify_post_with_mocked_exception(
            client,
            url,
            data,
            "apps.reproduction.services.reproduction_service.ReproductionService.register_birth",
            ValidationError("Service Error"),
        )

    # --- Diagnosis Views Coverage ---

    def test_diagnosis_delete_get_does_not_exist(self, client, django_user_model):
        """Test DiagnosisDeleteView GET DoesNotExist (lines 110-112)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "reproduction:diagnosis_delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("reproduction:diagnosis_list")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m) for m in messages)

    def test_diagnosis_restore_get_does_not_exist(self, client, django_user_model):
        """Test DiagnosisRestoreView GET DoesNotExist (lines 144-146)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "reproduction:diagnosis_restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("reproduction:diagnosis_list")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m) for m in messages)

    def test_diagnosis_hard_delete_get_does_not_exist(self, client, django_user_model):
        """Test DiagnosisPermanentDeleteView GET DoesNotExist (lines 167-169)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "reproduction:diagnosis_permanent_delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("reproduction:diagnosis_trash")
        messages = list(response.wsgi_request._messages)
        assert any("not found" in str(m) for m in messages)
