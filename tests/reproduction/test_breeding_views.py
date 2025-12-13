import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.models import BreedingEvent, ReproductiveSeason
from tests.test_utils import verify_redirect_with_message


@pytest.mark.django_db
class TestBreedingListView:
    """Tests for BreedingListView filtering, search, and pagination."""

    def test_list_view_displays_breeding_events(self, client, user):
        """Test that list view displays breeding events."""
        client.force_login(user)
        dam = baker.make(Cattle, tag="COW001", sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam, sire_name="BULL-X")

        response = client.get(reverse("reproduction:breeding_list"))

        assert response.status_code == 200
        assert event in response.context["events"]
        assert "COW001" in response.content.decode()

    def test_search_by_dam_tag(self, client, user):
        """Test search by dam tag."""
        client.force_login(user)
        dam1 = baker.make(Cattle, tag="COW001", sex=Cattle.SEX_FEMALE)
        dam2 = baker.make(Cattle, tag="COW002", sex=Cattle.SEX_FEMALE)
        event1 = baker.make(BreedingEvent, dam=dam1)
        event2 = baker.make(BreedingEvent, dam=dam2)

        response = client.get(reverse("reproduction:breeding_list") + "?q=COW001")

        assert event1 in response.context["events"]
        assert event2 not in response.context["events"]

    def test_search_by_dam_name(self, client, user):
        """Test search by dam name."""
        client.force_login(user)
        dam1 = baker.make(Cattle, name="Bessie", sex=Cattle.SEX_FEMALE)
        dam2 = baker.make(Cattle, name="Daisy", sex=Cattle.SEX_FEMALE)
        event1 = baker.make(BreedingEvent, dam=dam1)
        event2 = baker.make(BreedingEvent, dam=dam2)

        response = client.get(reverse("reproduction:breeding_list") + "?q=Bessie")

        assert event1 in response.context["events"]
        assert event2 not in response.context["events"]

    def test_search_by_sire_tag(self, client, user):
        """Test search by sire tag."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        sire1 = baker.make(Cattle, tag="BULL001", sex=Cattle.SEX_MALE)
        sire2 = baker.make(Cattle, tag="BULL002", sex=Cattle.SEX_MALE)
        event1 = baker.make(BreedingEvent, dam=dam, sire=sire1)
        event2 = baker.make(BreedingEvent, dam=dam, sire=sire2)

        response = client.get(reverse("reproduction:breeding_list") + "?q=BULL001")

        assert event1 in response.context["events"]
        assert event2 not in response.context["events"]

    def test_search_by_sire_name_field(self, client, user):
        """Test search by sire_name field (external sire)."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event1 = baker.make(BreedingEvent, dam=dam, sire_name="EXTERNAL-BULL-X")
        event2 = baker.make(BreedingEvent, dam=dam, sire_name="EXTERNAL-BULL-Y")

        response = client.get(reverse("reproduction:breeding_list") + "?q=BULL-X")

        assert event1 in response.context["events"]
        assert event2 not in response.context["events"]

    def test_filter_by_method(self, client, user):
        """Test filtering by breeding method."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event_ai = baker.make(
            BreedingEvent, dam=dam, breeding_method=BreedingEvent.METHOD_AI
        )
        event_natural = baker.make(
            BreedingEvent, dam=dam, breeding_method=BreedingEvent.METHOD_NATURAL
        )

        response = client.get(
            reverse("reproduction:breeding_list") + f"?method={BreedingEvent.METHOD_AI}"
        )

        assert event_ai in response.context["events"]
        assert event_natural not in response.context["events"]
        assert response.context["selected_method"] == BreedingEvent.METHOD_AI

    def test_filter_by_date_range(self, client, user):
        """Test filtering by date range."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event_old = baker.make(BreedingEvent, dam=dam, date=date(2024, 1, 1))
        event_new = baker.make(BreedingEvent, dam=dam, date=date(2024, 12, 1))

        response = client.get(
            reverse("reproduction:breeding_list")
            + "?date_after=2024-11-01&date_before=2024-12-31"
        )

        assert event_new in response.context["events"]
        assert event_old not in response.context["events"]
        assert response.context["date_after"] == "2024-11-01"
        assert response.context["date_before"] == "2024-12-31"

    def test_pagination(self, client, user):
        """Test pagination works correctly."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        # Create 25 events (paginate_by=20)
        baker.make(BreedingEvent, dam=dam, _quantity=25)

        response = client.get(reverse("reproduction:breeding_list"))

        assert response.context["is_paginated"]
        assert len(response.context["events"]) == 20

        # Check page 2
        response_page2 = client.get(reverse("reproduction:breeding_list") + "?page=2")
        assert len(response_page2.context["events"]) == 5


@pytest.mark.django_db
class TestBreedingCreateView:
    """Tests for BreedingCreateView."""

    def test_create_breeding_event_success(self, client, user):
        """Test successful creation of breeding event."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)

        data = {
            "dam": dam.pk,
            "date": "2024-12-01",
            "breeding_method": BreedingEvent.METHOD_AI,
            "sire": sire.pk,
            "sire_name": "",
            "batch": "",
        }

        response = client.post(reverse("reproduction:breeding_add"), data)

        assert response.status_code == 302
        assert BreedingEvent.objects.filter(dam=dam).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("successfully" in str(m).lower() for m in messages)

    def test_create_with_external_sire(self, client, user):
        """Test creation with external sire name."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)

        data = {
            "dam": dam.pk,
            "date": "2024-12-01",
            "breeding_method": BreedingEvent.METHOD_NATURAL,
            "sire": "",
            "sire_name": "EXTERNAL-BULL-123",
            "batch": "",
        }

        response = client.post(reverse("reproduction:breeding_add"), data)

        assert response.status_code == 302
        event = BreedingEvent.objects.get(dam=dam)
        assert event.sire_name == "EXTERNAL-BULL-123"

    def test_create_with_batch(self, client, user):
        """Test creation with breeding batch."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        batch = baker.make(ReproductiveSeason)

        data = {
            "dam": dam.pk,
            "date": "2024-12-01",
            "breeding_method": BreedingEvent.METHOD_AI,
            "sire": "",
            "sire_name": "BULL-X",
            "batch": batch.pk,
        }

        response = client.post(reverse("reproduction:breeding_add"), data)

        assert response.status_code == 302
        event = BreedingEvent.objects.get(dam=dam)
        event = BreedingEvent.objects.get(dam=dam)
        assert event.batch == batch

    def test_create_breeding_exception(self, client, user):
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        data = {
            "dam": dam.pk,
            "date": "2024-12-01",
            "breeding_method": BreedingEvent.METHOD_AI,
            "sire": "",
            "sire_name": "BULL-X",
            "batch": "",
        }

        with patch(
            "apps.reproduction.services.reproduction_service.ReproductionService.record_breeding",
            side_effect=ValidationError("Simulated Error"),
        ):
            response = client.post(reverse("reproduction:breeding_add"), data)

        assert response.status_code == 200
        assert "Simulated Error" in response.content.decode()


@pytest.mark.django_db
class TestBreedingTrashViews:
    """Tests for breeding trash, restore, and delete views."""

    def test_trash_list_shows_deleted_events(self, client, user):
        """Test that trash list shows soft-deleted events."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)
        event.delete()  # Soft delete

        response = client.get(reverse("reproduction:breeding_trash"))

        assert response.status_code == 200
        assert event in response.context["events"]

    def test_delete_view_soft_deletes_event(self, client, user):
        """Test that delete view performs soft delete."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)

        response = client.post(
            reverse("reproduction:breeding_delete", kwargs={"pk": event.pk})
        )

        assert response.status_code == 302
        assert not BreedingEvent.objects.filter(pk=event.pk).exists()
        assert BreedingEvent.all_objects.filter(pk=event.pk, is_deleted=True).exists()

    def test_delete_view_get_shows_confirmation(self, client, user):
        """Test that GET request shows confirmation page."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)

        response = client.get(
            reverse("reproduction:breeding_delete", kwargs={"pk": event.pk})
        )

        assert response.status_code == 200
        assert event == response.context["object"]

    def test_delete_view_handles_not_found(self, client, user):
        """Test delete view handles non-existent event."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("reproduction:breeding_delete", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="get")

    def test_restore_view_restores_event(self, client, user):
        """Test that restore view restores soft-deleted event."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)
        event.delete()

        response = client.post(
            reverse("reproduction:breeding_restore", kwargs={"pk": event.pk})
        )

        assert response.status_code == 302
        assert BreedingEvent.objects.filter(pk=event.pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("restored" in str(m).lower() for m in messages)

    def test_restore_view_get_shows_confirmation(self, client, user):
        """Test that GET request shows restore confirmation page."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)
        event.delete()

        response = client.get(
            reverse("reproduction:breeding_restore", kwargs={"pk": event.pk})
        )

        assert response.status_code == 200
        assert event.pk == response.context["event"].pk

    def test_restore_view_handles_not_found(self, client, user):
        """Test restore view handles non-existent event."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("reproduction:breeding_restore", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="get")

    def test_restore_exception(self, client, user):
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)
        event.delete()

        with patch(
            "apps.reproduction.services.reproduction_service.ReproductionService.restore_breeding_event",
            side_effect=ValueError("Restore Error"),
        ):
            response = client.post(
                reverse("reproduction:breeding_restore", kwargs={"pk": event.pk})
            )

        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("Restore Error" in str(m) for m in messages)

    def test_permanent_delete_view_deletes_from_db(self, client, user):
        """Test that permanent delete removes event from database."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)
        event.delete()  # Soft delete first
        event_pk = event.pk

        response = client.post(
            reverse("reproduction:breeding_permanent_delete", kwargs={"pk": event_pk})
        )

        assert response.status_code == 302
        assert not BreedingEvent.all_objects.filter(pk=event_pk).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("permanently deleted" in str(m).lower() for m in messages)

    def test_permanent_delete_view_get_shows_confirmation(self, client, user):
        """Test that GET request shows permanent delete confirmation."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        event = baker.make(BreedingEvent, dam=dam)
        event.delete()

        response = client.get(
            reverse("reproduction:breeding_permanent_delete", kwargs={"pk": event.pk})
        )

        assert response.status_code == 200
        assert event.pk == response.context["event"].pk

    def test_permanent_delete_handles_not_found(self, client, user):
        """Test permanent delete handles non-existent event."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse(
            "reproduction:breeding_permanent_delete", kwargs={"pk": fake_uuid}
        )
        verify_redirect_with_message(client, url, "not found", method="get")
