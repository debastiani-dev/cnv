# pylint: disable=unused-argument
import pytest

from apps.cattle.models.cattle import Cattle
from apps.locations.models import Location, LocationStatus, LocationType


@pytest.fixture
def user(db, django_user_model):
    """
    Creates a test user.
    """
    return django_user_model.objects.create_user(
        username="testuser", password="password123", email="test@example.com"
    )


@pytest.fixture
def cattle(db):
    """
    Creates a single default cattle.
    """
    return Cattle.objects.create(tag="TEST001", sex="female", weight_kg=350)


@pytest.fixture
def cattle_list(db):
    """
    Creates a list of cattle for batch testing.
    """
    c1 = Cattle.objects.create(tag="LOC001", sex="male", weight_kg=300)
    c2 = Cattle.objects.create(tag="LOC002", sex="female", weight_kg=400)
    return [c1, c2]


@pytest.fixture
def location(db):
    return Location.objects.create(
        name="Pasture A",
        type=LocationType.PASTURE,
        area_hectares=10.0,
        capacity_head=20,
        status=LocationStatus.ACTIVE,
    )


@pytest.fixture
def location_b(db):
    return Location.objects.create(
        name="Pasture B",
        type=LocationType.PASTURE,
        area_hectares=15.0,
        capacity_head=30,
        status=LocationStatus.ACTIVE,
    )
