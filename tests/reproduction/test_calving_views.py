from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.models import BreedingEvent, Calving
from tests.test_utils import create_pregnant_dam


@pytest.mark.django_db
class TestCalvingListView:
    """Tests for CalvingListView filtering and search."""

    def test_list_view_displays_calvings(self, client, user):
        """Test that list view displays calving records."""
        client.force_login(user)
        dam = baker.make(Cattle, tag="COW001", sex=Cattle.SEX_FEMALE)
        calf = baker.make(Cattle, tag="CALF001")
        calving = baker.make(Calving, dam=dam, calf=calf)

        response = client.get(reverse("reproduction:calving_list"))

        assert response.status_code == 200
        assert calving in response.context["calvings"]

    def test_search_by_dam_tag(self, client, user):
        """Test search by dam tag."""
        client.force_login(user)
        dam1 = baker.make(Cattle, tag="COW001", sex=Cattle.SEX_FEMALE)
        dam2 = baker.make(Cattle, tag="COW002", sex=Cattle.SEX_FEMALE)
        calving1 = baker.make(Calving, dam=dam1)
        calving2 = baker.make(Calving, dam=dam2)

        response = client.get(reverse("reproduction:calving_list") + "?q=COW001")

        assert calving1 in response.context["calvings"]
        assert calving2 not in response.context["calvings"]

    def test_search_by_calf_tag(self, client, user):
        """Test search by calf tag."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calf1 = baker.make(Cattle, tag="CALF001")
        calf2 = baker.make(Cattle, tag="CALF002")
        calving1 = baker.make(Calving, dam=dam, calf=calf1)
        calving2 = baker.make(Calving, dam=dam, calf=calf2)

        response = client.get(reverse("reproduction:calving_list") + "?q=CALF001")

        assert calving1 in response.context["calvings"]
        assert calving2 not in response.context["calvings"]

    def test_filter_by_ease(self, client, user):
        """Test filtering by ease of birth."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving_easy = baker.make(Calving, dam=dam, ease_of_birth=Calving.EASE_EASY)
        calving_hard = baker.make(Calving, dam=dam, ease_of_birth=Calving.EASE_ASSISTED)

        response = client.get(
            reverse("reproduction:calving_list") + f"?ease={Calving.EASE_EASY}"
        )

        assert calving_easy in response.context["calvings"]
        assert calving_hard not in response.context["calvings"]
        assert response.context["selected_ease"] == Calving.EASE_EASY

    def test_filter_by_date_range(self, client, user):
        """Test filtering by date range."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving_old = baker.make(Calving, dam=dam, date="2024-01-01")
        calving_new = baker.make(Calving, dam=dam, date="2024-12-01")

        response = client.get(
            reverse("reproduction:calving_list")
            + "?date_after=2024-11-01&date_before=2024-12-31"
        )

        assert calving_new in response.context["calvings"]
        assert calving_old not in response.context["calvings"]

    def test_pagination(self, client, user):
        """Test pagination works correctly."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        # Create 25 calvings (paginate_by=20)
        baker.make(Calving, dam=dam, _quantity=25)

        response = client.get(reverse("reproduction:calving_list"))

        assert response.context["is_paginated"]
        assert len(response.context["calvings"]) == 20


@pytest.mark.django_db
class TestCalvingCreateView:
    """Tests for CalvingCreateView."""

    def test_create_calving_success(self, client, user):
        """Test successful creation of calving record."""
        client.force_login(user)
        dam, breeding = create_pregnant_dam()

        data = {
            "dam": dam.pk,
            "breeding_event": breeding.pk,
            "date": "2024-12-01",
            "calf_tag": "CALF123",
            "calf_name": "Newborn",
            "calf_sex": Cattle.SEX_MALE,
            "calf_weight": 35,
            "ease_of_birth": Calving.EASE_EASY,
            "notes": "",
        }

        response = client.post(reverse("reproduction:calving_add"), data)

        assert response.status_code == 302
        assert Calving.objects.filter(dam=dam).exists()
        assert Cattle.objects.filter(tag="CALF123").exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("recorded" in str(m).lower() for m in messages)

    def test_create_with_difficult_birth(self, client, user):
        """Test creation with difficult birth."""
        client.force_login(user)
        dam = baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
        )
        breeding = baker.make(BreedingEvent, dam=dam)

        data = {
            "dam": dam.pk,
            "breeding_event": breeding.pk,
            "date": "2024-12-01",
            "calf_tag": "CALF456",
            "calf_name": "",
            "calf_sex": Cattle.SEX_FEMALE,
            "calf_weight": 30,
            "ease_of_birth": Calving.EASE_ASSISTED,
            "notes": "Required assistance",
        }

        response = client.post(reverse("reproduction:calving_add"), data)

        assert response.status_code == 302
        calving = Calving.objects.get(dam=dam)
        assert calving.ease_of_birth == Calving.EASE_ASSISTED
        assert "assistance" in calving.notes


@pytest.mark.django_db
class TestCalvingTrashViews:
    """Tests for calving trash, restore, and delete views."""

    def test_trash_list_shows_deleted_calvings(self, client, user):
        """Test that trash list shows soft-deleted calving records."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)
        calving.delete()  # Soft delete

        response = client.get(reverse("reproduction:calving_trash"))

        assert response.status_code == 200
        assert calving in response.context["records"]

    def test_delete_view_get_shows_confirmation(self, client, user):
        """Test that GET request shows confirmation page."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)

        response = client.get(
            reverse("reproduction:calving_delete", kwargs={"pk": calving.pk})
        )

        assert response.status_code == 200
        assert calving == response.context["object"]
        assert "confirm" in response.content.decode().lower()

    def test_delete_view_protected_error(self, client, user):
        """Test delete view handles ProtectedError."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)

        with patch.object(
            Calving, "delete", side_effect=ProtectedError("Protected", [])
        ):
            response = client.post(
                reverse("reproduction:calving_delete", kwargs={"pk": calving.pk})
            )

        assert response.status_code == 200
        assert "cannot delete" in response.content.decode().lower()

    def test_delete_view_soft_deletes_calving(self, client, user):
        """Test that delete view performs soft delete."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)

        response = client.post(
            reverse("reproduction:calving_delete", kwargs={"pk": calving.pk})
        )

        assert response.status_code == 302
        assert not Calving.objects.filter(pk=calving.pk).exists()
        assert Calving.all_objects.filter(pk=calving.pk, is_deleted=True).exists()

    def test_restore_view_restores_calving(self, client, user):
        """Test that restore view restores soft-deleted calving."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)
        calving.delete()

        response = client.post(
            reverse("reproduction:calving_restore", kwargs={"pk": calving.pk})
        )

        assert response.status_code == 302
        assert Calving.objects.filter(pk=calving.pk).exists()

    def test_permanent_delete_view_deletes_from_db(self, client, user):
        """Test that permanent delete removes calving from database."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)
        calving.delete()  # Soft delete first
        calving_pk = calving.pk

        response = client.post(
            reverse("reproduction:calving_permanent_delete", kwargs={"pk": calving_pk})
        )

        assert response.status_code == 302
        assert not Calving.all_objects.filter(pk=calving_pk).exists()

    def test_restore_view_get_shows_confirmation(self, client, user):
        """Test restore view GET request."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)
        calving.delete()

        response = client.get(
            reverse("reproduction:calving_restore", kwargs={"pk": calving.pk})
        )

        assert response.status_code == 200
        assert calving.pk == response.context["object"].pk

    def test_permanent_delete_view_get_shows_confirmation(self, client, user):
        """Test permanent delete view GET request."""
        client.force_login(user)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        calving = baker.make(Calving, dam=dam)
        calving.delete()

        response = client.get(
            reverse("reproduction:calving_permanent_delete", kwargs={"pk": calving.pk})
        )

        assert response.status_code == 200
        assert calving.pk == response.context["object"].pk
