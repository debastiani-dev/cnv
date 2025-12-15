# pylint: disable=unused-argument
import pytest
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.cattle.services.cattle_service import CattleService
from apps.locations.models import Location, LocationStatus


@pytest.mark.django_db
def test_cattle_list_location_filter(client, django_user_model):
    # Setup user
    user = baker.make(django_user_model)
    client.force_login(user)

    # Setup locations
    loc1 = baker.make(Location, name="Pasture A", status=LocationStatus.ACTIVE)
    loc2 = baker.make(Location, name="Pasture B", status=LocationStatus.ACTIVE)

    # Setup cattle
    c1 = baker.make(Cattle, location=loc1, tag="COW001", status=Cattle.STATUS_AVAILABLE)
    c2 = baker.make(Cattle, location=loc2, tag="COW002", status=Cattle.STATUS_AVAILABLE)
    c3 = baker.make(Cattle, location=None, tag="COW003", status=Cattle.STATUS_AVAILABLE)

    url = reverse("cattle:list")

    # Test filter by loc1
    response = client.get(url, {"location": loc1.pk})
    assert response.status_code == 200
    cattle_list = response.context["cattle_list"]
    assert c1 in cattle_list
    assert c2 not in cattle_list
    assert c3 not in cattle_list
    # Verify filter form state instead of raw context variable
    assert str(response.context["filter"].form["location"].value()[0]) == str(loc1.pk)

    # Test filter by loc2
    response = client.get(url, {"location": loc2.pk})
    assert response.status_code == 200
    cattle_list = response.context["cattle_list"]
    assert c1 not in cattle_list
    assert c2 in cattle_list
    assert c3 not in cattle_list
    assert str(response.context["filter"].form["location"].value()[0]) == str(loc2.pk)

    # Test no filter (all cattle)
    response = client.get(url)
    assert response.status_code == 200
    cattle_list = response.context["cattle_list"]
    assert c1 in cattle_list
    assert c2 in cattle_list
    assert c3 in cattle_list
    # Verify no location is selected
    assert not response.context["filter"].form["location"].value()

    # Test context locations (via filter field queryset)
    # The filter's field queryset is what populates the dropdown now
    filter_locs = list(response.context["filter"].form.fields["location"].queryset)
    assert loc1 in filter_locs
    assert loc2 in filter_locs


@pytest.mark.django_db
def test_cattle_service_coverage(user):
    # Setup locations
    loc1 = baker.make(Location, name="Pasture A", status=LocationStatus.ACTIVE)
    baker.make(Cattle, location=loc1, tag="COW001")
    baker.make(Cattle, location=None, tag="COW002")

    qs = CattleService.get_all_cattle(location_id=str(loc1.pk))
    assert qs.count() == 1
    assert qs.first().location == loc1


@pytest.mark.django_db
def test_filter_empty_search(client, user):
    """Test that empty search query returns all results (covers line 31-32 in filters.py)"""
    client.force_login(user)
    baker.make(Cattle, tag="TEST1")
    url = reverse("cattle:list")

    # Pass empty q param
    response = client.get(url, {"q": ""})
    assert len(response.context["cattle_list"]) == 1
