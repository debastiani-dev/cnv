import uuid
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.models import BreedingEvent, PregnancyCheck
from tests.test_utils import verify_redirect_with_message


@pytest.mark.django_db
class TestDiagnosisListView:
    """Tests for DiagnosisListView (PregnancyCheck) filtering and search."""

    def test_list_view_displays_pregnancy_checks(self, client, user):
        """Test that list view displays pregnancy checks."""
        client.force_login(user)
        dam = baker.make(Cattle, tag="COW001", sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)

        response = client.get(reverse("reproduction:diagnosis_list"))

        assert response.status_code == 200
        assert check in response.context["checks"]

    def test_search_by_dam_tag(self, client, user):
        """Test search by dam tag."""
        client.force_login(user)
        dam1 = baker.make(Cattle, tag="COW001", sex=Cattle.SEX_FEMALE)
        dam2 = baker.make(Cattle, tag="COW002", sex=Cattle.SEX_FEMALE)
        breeding1 = baker.make(BreedingEvent, dam=dam1)
        breeding2 = baker.make(BreedingEvent, dam=dam2)
        check1 = baker.make(PregnancyCheck, breeding_event=breeding1)
        check2 = baker.make(PregnancyCheck, breeding_event=breeding2)

        response = client.get(reverse("reproduction:diagnosis_list") + "?q=COW001")

        assert check1 in response.context["checks"]
        assert check2 not in response.context["checks"]

    def test_filter_by_result(self, client, user):
        """Test filtering by pregnancy result."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check_pregnant = baker.make(
            PregnancyCheck,
            breeding_event=breeding,
            result=PregnancyCheck.RESULT_POSITIVE,
        )
        check_open = baker.make(
            PregnancyCheck,
            breeding_event=breeding,
            result=PregnancyCheck.RESULT_NEGATIVE,
        )

        response = client.get(
            reverse("reproduction:diagnosis_list")
            + f"?result={PregnancyCheck.RESULT_POSITIVE}"
        )

        assert check_pregnant in response.context["checks"]
        assert check_open not in response.context["checks"]
        assert response.context["selected_result"] == PregnancyCheck.RESULT_POSITIVE

    def test_filter_by_date_range(self, client, user):
        """Test filtering by date range."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check_old = baker.make(
            PregnancyCheck, breeding_event=breeding, date="2024-01-01"
        )
        check_new = baker.make(
            PregnancyCheck, breeding_event=breeding, date="2024-12-01"
        )

        response = client.get(
            reverse("reproduction:diagnosis_list")
            + "?date_after=2024-11-01&date_before=2024-12-31"
        )

        assert check_new in response.context["checks"]
        assert check_old not in response.context["checks"]

    def test_pagination(self, client, user):
        """Test pagination works correctly."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        # Create 25 checks (paginate_by=20)
        baker.make(PregnancyCheck, breeding_event=breeding, _quantity=25)

        response = client.get(reverse("reproduction:diagnosis_list"))

        assert response.context["is_paginated"]
        assert len(response.context["checks"]) == 20


@pytest.mark.django_db
class TestDiagnosisCreateView:
    """Tests for DiagnosisCreateView."""

    def test_create_diagnosis_success(self, client, user):
        """Test successful creation of pregnancy check."""
        client.force_login(user)
        dam = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_BRED
        )
        breeding = baker.make(BreedingEvent, dam=dam)

        data = {
            "breeding_event": breeding.pk,
            "date": "2024-12-01",
            "result": PregnancyCheck.RESULT_POSITIVE,
            "fetus_days": 60,
        }

        response = client.post(reverse("reproduction:diagnosis_add"), data)

        assert response.status_code == 302
        assert PregnancyCheck.objects.filter(breeding_event=breeding).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("successfully" in str(m).lower() for m in messages)

    def test_create_with_open_result(self, client, user):
        """Test creation with open (not pregnant) result."""
        client.force_login(user)
        dam = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_BRED
        )
        breeding = baker.make(BreedingEvent, dam=dam)

        data = {
            "breeding_event": breeding.pk,
            "date": "2024-12-01",
            "result": PregnancyCheck.RESULT_NEGATIVE,
            "fetus_days": "",
        }

        response = client.post(reverse("reproduction:diagnosis_add"), data)

        assert response.status_code == 302
        check = PregnancyCheck.objects.get(breeding_event=breeding)
        assert check.result == PregnancyCheck.RESULT_NEGATIVE

    def test_form_limits_to_bred_cows(self, client, user):
        """Test that form only shows breeding events for BRED cows."""
        client.force_login(user)
        dam_bred = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_BRED
        )
        dam_open = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_OPEN
        )
        breeding_bred = baker.make(BreedingEvent, dam=dam_bred)
        breeding_open = baker.make(BreedingEvent, dam=dam_open)

        response = client.get(reverse("reproduction:diagnosis_add"))

        # Check that form queryset only includes BRED cows
        form_queryset = response.context["form"].fields["breeding_event"].queryset
        assert breeding_bred in form_queryset
        assert breeding_open not in form_queryset


@pytest.mark.django_db
class TestDiagnosisTrashViews:
    """Tests for diagnosis trash, restore, and delete views."""

    def test_trash_list_shows_deleted_checks(self, client, user):
        """Test that trash list shows soft-deleted pregnancy checks."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)
        check.delete()  # Soft delete

        response = client.get(reverse("reproduction:diagnosis_trash"))

        assert response.status_code == 200
        assert check in response.context["checks"]

    def test_delete_view_soft_deletes_check(self, client, user):
        """Test that delete view performs soft delete."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)

        response = client.post(
            reverse("reproduction:diagnosis_delete", kwargs={"pk": check.pk})
        )

        assert response.status_code == 302
        assert not PregnancyCheck.objects.filter(pk=check.pk).exists()
        assert PregnancyCheck.all_objects.filter(pk=check.pk, is_deleted=True).exists()

    def test_delete_view_get_shows_confirmation(self, client, user):
        """Test that GET request shows confirmation page."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)

        response = client.get(
            reverse("reproduction:diagnosis_delete", kwargs={"pk": check.pk})
        )

        assert response.status_code == 200
        assert check == response.context["object"]

    def test_delete_view_handles_not_found(self, client, user):
        """Test delete view handles non-existent check."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("reproduction:diagnosis_delete", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="post")

    def test_restore_view_restores_check(self, client, user):
        """Test that restore view restores soft-deleted check."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)
        check.delete()

        response = client.post(
            reverse("reproduction:diagnosis_restore", kwargs={"pk": check.pk})
        )

        assert response.status_code == 302
        assert PregnancyCheck.objects.filter(pk=check.pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("restored" in str(m).lower() for m in messages)

    def test_restore_view_get_shows_confirmation(self, client, user):
        """Test that GET request shows restore confirmation page."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)
        check.delete()

        response = client.get(
            reverse("reproduction:diagnosis_restore", kwargs={"pk": check.pk})
        )

        assert response.status_code == 200
        assert check.pk == response.context["event"].pk

    def test_restore_view_handles_not_found(self, client, user):
        """Test restore view handles non-existent check."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("reproduction:diagnosis_restore", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="post")

    def test_permanent_delete_view_deletes_from_db(self, client, user):
        """Test that permanent delete removes check from database."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)
        check.delete()  # Soft delete first
        check_pk = check.pk

        response = client.post(
            reverse("reproduction:diagnosis_permanent_delete", kwargs={"pk": check_pk})
        )

        assert response.status_code == 302
        assert not PregnancyCheck.all_objects.filter(pk=check_pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("permanently deleted" in str(m).lower() for m in messages)

    def test_permanent_delete_view_get_shows_confirmation(self, client, user):
        """Test that GET request shows permanent delete confirmation."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        breeding = baker.make(BreedingEvent, dam=dam)
        check = baker.make(PregnancyCheck, breeding_event=breeding)
        check.delete()

        response = client.get(
            reverse("reproduction:diagnosis_permanent_delete", kwargs={"pk": check.pk})
        )

        assert response.status_code == 200
        assert check.pk == response.context["event"].pk

    def test_permanent_delete_handles_not_found(self, client, user):
        """Test permanent delete handles non-existent check."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse(
            "reproduction:diagnosis_permanent_delete", kwargs={"pk": fake_uuid}
        )
        verify_redirect_with_message(client, url, "not found", method="post")

    def test_create_diagnosis_exception(self, client, user):
        """Test handling of service exceptions during creation."""
        client.force_login(user)
        dam = baker.make(
            Cattle, reproduction_status=Cattle.REP_STATUS_BRED, sex=Cattle.SEX_FEMALE
        )
        breeding = baker.make(BreedingEvent, dam=dam)
        data = {
            "breeding_event": breeding.pk,
            "date": "2024-12-01",
            "result": PregnancyCheck.RESULT_POSITIVE,
            "fetus_days": 60,
        }

        with patch(
            "apps.reproduction.services.reproduction_service.ReproductionService.record_diagnosis",
            side_effect=ValidationError("Simulated Error"),
        ):
            response = client.post(reverse("reproduction:diagnosis_add"), data)

        assert response.status_code == 200  # Form invalid re-render
        assert "Simulated Error" in response.content.decode()


@pytest.mark.django_db
class TestDiagnosisExceptionViews:
    def test_delete_protected_error(self, client, user):
        client.force_login(user)
        check = baker.make(PregnancyCheck)

        with patch.object(
            PregnancyCheck, "delete", side_effect=ProtectedError("Protected", [])
        ):
            response = client.post(
                reverse("reproduction:diagnosis_delete", kwargs={"pk": check.pk})
            )

        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("Protected" in str(m) for m in messages)

    def test_restore_exception(self, client, user):
        client.force_login(user)
        check = baker.make(PregnancyCheck)
        check.delete()

        with patch(
            "apps.reproduction.services.reproduction_service.ReproductionService.restore_pregnancy_check",
            side_effect=ValueError("Restore Error"),
        ):
            response = client.post(
                reverse("reproduction:diagnosis_restore", kwargs={"pk": check.pk})
            )

        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("Restore Error" in str(m) for m in messages)
