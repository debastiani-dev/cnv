# pylint: disable=protected-access
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.health.models import Medication, SanitaryEvent, SanitaryEventTarget
from apps.health.services import HealthService


@pytest.mark.django_db
class TestHealthCoverage:
    """Tests to cover missing lines in health models and services."""

    def test_sanitary_event_target_str(self):
        """Test SanitaryEventTarget.__str__ method (line 171)."""
        cattle = baker.make(Cattle, tag="TEST-001")
        event = baker.make(SanitaryEvent, title="Vaccination")
        target = baker.make(SanitaryEventTarget, animal=cattle, event=event)

        # Should return "Cattle - Event Title" format
        str_repr = str(target)
        assert "TEST-001" in str_repr or str(cattle) in str_repr
        assert "Vaccination" in str_repr

    def test_get_animal_health_history(self):
        """Test get_animal_health_history return statement (line 105)."""
        cattle = baker.make(Cattle)

        # Create some health events
        event1 = baker.make(SanitaryEvent, title="Event 1")
        event2 = baker.make(SanitaryEvent, title="Event 2")
        baker.make(SanitaryEventTarget, animal=cattle, event=event1)
        baker.make(SanitaryEventTarget, animal=cattle, event=event2)

        # Get history
        history = HealthService.get_animal_health_history(cattle)

        # Should return a queryset with 2 targets
        assert history.count() == 2
        # Verify line 105 is hit (return statement)
        assert list(history)  # Force evaluation

    def test_get_active_withdrawal_count_with_duplicate_animal(self):
        """Test withdrawal count with duplicate animal (line 142 continue)."""
        med = baker.make(Medication, withdrawal_days_meat=20)
        cattle = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)

        # Create TWO events for the SAME animal, both within withdrawal
        event_date1 = timezone.localdate() - timedelta(days=5)
        event_date2 = timezone.localdate() - timedelta(days=3)

        event1 = baker.make(SanitaryEvent, date=event_date1, medication=med)
        event2 = baker.make(SanitaryEvent, date=event_date2, medication=med)

        baker.make(SanitaryEventTarget, animal=cattle, event=event1)
        baker.make(SanitaryEventTarget, animal=cattle, event=event2)

        # Get count - should be 1 (same animal, line 142 continue should be hit)
        count = HealthService.get_active_withdrawal_count()

        assert count == 1  # Only counts unique animals

    def test_restore_medication_service(self, django_user_model):
        """Test restore_medication service method (line 205)."""
        baker.make(django_user_model)
        medication = baker.make(Medication, name="Test Med")
        medication.delete()  # Soft delete

        # Restore via service
        HealthService.restore_medication(str(medication.pk))

        # Should be restored
        medication.refresh_from_db()
        assert medication.is_deleted is False

    def test_hard_delete_medication_service(self, django_user_model):
        """Test hard_delete_medication service method (line 214)."""
        baker.make(django_user_model)
        medication = baker.make(Medication, name="Test Med")
        medication.delete()  # Soft delete first
        pk = str(medication.pk)

        # Hard delete via service
        HealthService.hard_delete_medication(pk)

        # Should be permanently deleted
        assert not Medication.all_objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestMedicationViewsCoverage:
    """Tests to cover missing lines in medication views."""

    def test_medication_restore_post_success(self, client, django_user_model):
        """Test MedicationRestoreView POST success (line 102)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        medication = baker.make(Medication, name="Test Med")
        medication.delete()  # Soft delete

        url = reverse("health:medication-restore", kwargs={"pk": medication.pk})
        response = client.post(url)

        # Should redirect with success message
        assert response.status_code == 302
        messages = list(response.wsgi_request._messages)
        assert any("restored successfully" in str(m).lower() for m in messages)

    def test_medication_restore_get_confirmation(self, client, django_user_model):
        """Test MedicationRestoreView GET confirmation (line 113)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        medication = baker.make(Medication, name="Test Med")
        medication.delete()  # Soft delete

        url = reverse("health:medication-restore", kwargs={"pk": medication.pk})
        response = client.get(url)

        # Should render confirmation template (line 113)
        assert response.status_code == 200
        assert "health/medication_confirm_restore.html" in [
            t.name for t in response.templates
        ]
        assert response.context["medication"] == medication

    def test_medication_hard_delete_post_success(self, client, django_user_model):
        """Test MedicationPermanentDeleteView POST success (line 127)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        medication = baker.make(Medication, name="Test Med")
        medication.delete()  # Soft delete first

        url = reverse(
            "health:medication-permanent-delete", kwargs={"pk": medication.pk}
        )
        response = client.post(url)

        # Should redirect with success message (line 127)
        assert response.status_code == 302
        messages = list(response.wsgi_request._messages)
        assert any("permanently deleted" in str(m).lower() for m in messages)

    def test_medication_hard_delete_post_protected_then_not_exist(
        self, client, django_user_model
    ):
        """Test MedicationPermanentDeleteView POST nested DoesNotExist (lines 144-145)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        medication = baker.make(Medication)
        medication.delete()  # Soft delete
        pk = medication.pk

        url = reverse("health:medication-permanent-delete", kwargs={"pk": pk})

        # Mock service to raise ProtectedError, then mock get() to raise DoesNotExist
        with patch(
            "apps.health.services.health_service.HealthService.hard_delete_medication",
            side_effect=ProtectedError("Protected", []),
        ):
            with patch(
                "apps.health.models.health.Medication.all_objects.get",
                side_effect=Medication.DoesNotExist,
            ):
                response = client.post(url)

                # Should redirect to trash (lines 144-145, pass statement)
                assert response.status_code == 302
                assert response.url == reverse("health:medication-trash")

    def test_medication_hard_delete_get_confirmation(self, client, django_user_model):
        """Test MedicationPermanentDeleteView GET confirmation (line 152)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        medication = baker.make(Medication, name="Test Med")
        medication.delete()  # Soft delete

        url = reverse(
            "health:medication-permanent-delete", kwargs={"pk": medication.pk}
        )
        response = client.get(url)

        # Should render confirmation template (line 152)
        assert response.status_code == 200
        assert "health/medication_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]
        assert response.context["medication"] == medication
