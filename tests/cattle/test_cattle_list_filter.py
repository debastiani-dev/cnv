import pytest
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
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
    assert response.context["selected_location"] == str(loc1.pk)

    # Test filter by loc2
    response = client.get(url, {"location": loc2.pk})
    assert response.status_code == 200
    cattle_list = response.context["cattle_list"]
    assert c1 not in cattle_list
    assert c2 in cattle_list
    assert c3 not in cattle_list
    assert response.context["selected_location"] == str(loc2.pk)

    # Test no filter (all cattle)
    response = client.get(url)
    assert response.status_code == 200
    cattle_list = response.context["cattle_list"]
    assert c1 in cattle_list
    assert c2 in cattle_list
    assert c3 in cattle_list
    assert response.context["selected_location"] == ""

    # Test context locations
    assert loc1 in response.context["locations"]
    assert loc2 in response.context["locations"]
