# pylint: disable=redefined-outer-name
from unittest.mock import patch

import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.locations.models import Location, LocationStatus, LocationType
from apps.locations.services import LocationService
from tests.test_utils import verify_protected_error_response


@pytest.fixture
def auth_client(client, django_user_model):
    user = baker.make(django_user_model)
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestLocationCrudViews:
    def test_list_view(self, auth_client):
        loc = baker.make(Location, name="Test Loc")
        url = reverse("locations:list")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert loc in response.context["locations"]

    def test_create_view(self, auth_client):
        url = reverse("locations:create")
        data = {
            "name": "New Pasture",
            "type": LocationType.PASTURE,
            "status": LocationStatus.ACTIVE,
            "capacity_head": 50,
            "area_hectares": "100.00",
            "is_active": True,
        }
        response = auth_client.post(url, data)
        assert response.status_code == 302
        assert Location.objects.filter(name="New Pasture").exists()

    def test_update_view(self, auth_client):
        loc = baker.make(Location, name="Old Name", area_hectares=10, capacity_head=100)
        url = reverse("locations:update", kwargs={"pk": loc.pk})
        data = {
            "name": "Updated Name",
            "type": loc.type,
            "status": loc.status,
            "area_hectares": str(loc.area_hectares),
            "capacity_head": loc.capacity_head,
            "is_active": True,
        }
        response = auth_client.post(url, data)
        if response.status_code != 302:
            print(response.context["form"].errors)
        assert response.status_code == 302
        loc.refresh_from_db()
        assert loc.name == "Updated Name"

    def test_delete_view_get_confirmation(self, auth_client):
        loc = baker.make(Location)
        url = reverse("locations:delete", kwargs={"pk": loc.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "delete" in response.content.decode().lower()

    def test_delete_view_post(self, auth_client):
        loc = baker.make(Location)
        url = reverse("locations:delete", kwargs={"pk": loc.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert not Location.objects.filter(pk=loc.pk).exists()
        assert Location.all_objects.filter(pk=loc.pk, is_deleted=True).exists()

    def test_trash_list_view(self, auth_client):
        loc = baker.make(Location)
        loc.delete()
        url = reverse("locations:trash")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert loc in response.context["locations"]

    def test_restore_view_get_confirmation(self, auth_client):
        loc = baker.make(Location)
        loc.delete()
        url = reverse("locations:restore", kwargs={"pk": loc.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "restore" in response.content.decode().lower()

    def test_restore_view_post(self, auth_client):
        loc = baker.make(Location)
        loc.delete()
        url = reverse("locations:restore", kwargs={"pk": loc.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert Location.objects.filter(pk=loc.pk).exists()

    def test_hard_delete_view_get_confirmation(self, auth_client):
        loc = baker.make(Location)
        loc.delete()
        url = reverse("locations:hard-delete", kwargs={"pk": loc.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "permanently" in response.content.decode().lower()

    def test_hard_delete_view_post(self, auth_client):
        loc = baker.make(Location)
        loc.delete()
        url = reverse("locations:hard-delete", kwargs={"pk": loc.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert not Location.all_objects.filter(pk=loc.pk).exists()

    def test_hard_delete_view_exception(self, auth_client):
        loc = baker.make(Location)
        loc.delete()
        url = reverse("locations:hard-delete", kwargs={"pk": loc.pk})

        with patch.object(
            LocationService,
            "hard_delete_location",
            side_effect=ProtectedError("Protected", []),
        ):
            verify_protected_error_response(auth_client, url, "cannot delete")

    def test_detail_view(self, auth_client):
        loc = baker.make(Location, name="Detail Loc", area_hectares=100)
        c1 = baker.make(Cattle, location=loc)
        url = reverse("locations:detail", kwargs={"pk": loc.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.context["location"] == loc
        assert c1 in response.context["cattle_list"]
        assert "stats" in response.context


@pytest.mark.django_db
class TestLocationListLogic:
    def test_filters(self, auth_client):
        l1 = baker.make(
            Location,
            name="Alpha",
            type=LocationType.PASTURE,
            status=LocationStatus.ACTIVE,
        )
        l2 = baker.make(
            Location,
            name="Beta",
            type=LocationType.FEEDLOT,
            status=LocationStatus.RESTING,
        )
        url = reverse("locations:list")

        # Search
        resp = auth_client.get(url, {"q": "Alpha"})
        assert l1 in resp.context["locations"]
        assert l2 not in resp.context["locations"]

        # Type
        resp = auth_client.get(url, {"type": LocationType.FEEDLOT})
        assert l1 not in resp.context["locations"]
        assert l2 in resp.context["locations"]

        # Status
        resp = auth_client.get(url, {"status": LocationStatus.RESTING})
        assert l1 not in resp.context["locations"]
        assert l2 in resp.context["locations"]

    def test_status_color_logic(self, auth_client):
        # 1. Normal (Green)
        loc_green = baker.make(
            Location, name="Green", status=LocationStatus.ACTIVE, capacity_head=100
        )
        baker.make(Cattle, location=loc_green, _quantity=5)

        # 2. Over Capacity (Red)
        loc_red_cap = baker.make(
            Location, name="RedCap", status=LocationStatus.ACTIVE, capacity_head=2
        )
        baker.make(Cattle, location=loc_red_cap, _quantity=5)

        # 3. Resting Empty (Yellow)
        loc_yellow = baker.make(
            Location, name="Yellow", status=LocationStatus.RESTING, capacity_head=100
        )

        # 4. Resting with Animals (Red)
        loc_red_rest = baker.make(
            Location, name="RedRest", status=LocationStatus.RESTING, capacity_head=100
        )
        baker.make(Cattle, location=loc_red_rest, _quantity=1)

        url = reverse("locations:list")
        resp = auth_client.get(url)
        stats = resp.context["location_stats"]

        assert stats[loc_green.pk]["ui_status"] == "green"
        assert stats[loc_red_cap.pk]["ui_status"] == "red"
        assert stats[loc_yellow.pk]["ui_status"] == "yellow"
        assert stats[loc_red_rest.pk]["ui_status"] == "red"


@pytest.mark.django_db
class TestMovementViews:
    def test_movement_create_initial(self, auth_client):
        # Simulates selecting cattle and clicking "Move"
        c1 = baker.make(Cattle)
        c2 = baker.make(Cattle)
        url = reverse("locations:move")
        response = auth_client.post(url, {"cattle_ids": [c1.pk, c2.pk]})
        assert response.status_code == 200
        assert "locations/movement_form.html" in [t.name for t in response.templates]
        # Form should be initialized with cattle IDs
        assert str(c1.pk) in response.context["form"]["cattle_ids"].value()

    def test_movement_create_submit(self, auth_client):
        c1 = baker.make(Cattle)
        dest = baker.make(
            Location,
            name="Dest",
            status=LocationStatus.ACTIVE,
            area_hectares=10,
            capacity_head=100,
        )
        url = reverse("locations:move")
        # Submitting the actual form
        data = {
            "cattle_ids": str(c1.pk),
            "destination": dest.pk,
            "date": "2024-01-01",
            "reason": "ROTATION",
            "notes": "Moving cows",
        }
        response = auth_client.post(url, data)
        if response.status_code != 302:
            print(response.content.decode())
            if "form" in response.context:
                print(response.context["form"].errors)
        assert response.status_code == 302
        c1.refresh_from_db()
        assert c1.location == dest

    def test_movement_cattle_id_parsing(self, auth_client):
        # Test finding IDs via POST list (single checkbox)
        url = reverse("locations:move")
        c1 = baker.make(Cattle)

        # Simulates a form submission where 'cattle_ids' might be hidden field with commas
        response = auth_client.post(url, {"cattle_ids": [f"{c1.pk}"]})
        # Should render form
        assert response.status_code == 200
        assert str(c1.pk) in response.context["form"]["cattle_ids"].value()

        # Test comma separated
        c2 = baker.make(Cattle)
        response = auth_client.post(url, {"cattle_ids": [f"{c1.pk},{c2.pk}"]})
        content = response.context["form"]["cattle_ids"].value()
        assert str(c1.pk) in content
        assert str(c2.pk) in content
