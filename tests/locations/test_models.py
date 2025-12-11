import pytest

from apps.locations.models import LocationStatus, Movement


@pytest.mark.django_db
class TestLocationModels:
    def test_location_creation(self, location):
        assert location.name == "Pasture A"
        assert location.area_hectares == 10.0
        assert location.status == LocationStatus.ACTIVE

    def test_movement_creation(self, location, location_b, user):
        movement = Movement.objects.create(
            origin=location,
            destination=location_b,
            performed_by=user,
            reason="ROTATION",
        )
        assert movement.pk is not None
        assert movement.origin == location
        assert movement.destination == location_b

    def test_movement_string_representation(self, location, location_b):
        movement = Movement.objects.create(
            origin=location, destination=location_b, reason="ROTATION"
        )
        # Should contain date and locations
        assert str(movement.date.date()) in str(movement)
        assert location.name in str(movement)
        assert location_b.name in str(movement)
