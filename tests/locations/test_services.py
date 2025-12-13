# pylint: disable=unused-argument
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from model_bakery import baker

from apps.locations.models import Location, LocationStatus
from apps.locations.services import LocationService, MovementService


@pytest.mark.django_db
class TestLocationServices:
    def test_move_cattle(self, location, location_b, cattle_list, user):
        # Initial State
        for c in cattle_list:
            c.location = location
            c.save()

        # Action
        movement = MovementService.move_cattle(
            cattle_list=cattle_list,
            destination=location_b,
            performed_by=user,
            reason="ROTATION",
            notes="Test move",
        )

        # Verification
        assert movement.pk is not None
        assert movement.animals.count() == 2

        # Check cattle location updated
        for c in cattle_list:
            c.refresh_from_db()
            assert c.location == location_b

    def test_calculate_stocking_rate(self, location, cattle_list):
        # Assign cattle to location
        for c in cattle_list:
            c.location = location
            # Mock weight caching if service relies on 'current_weight'
            c.current_weight = c.weight_kg
            c.save()

        # cattle weights: 300 + 400 = 700kg
        # location area: 10 ha
        # kg/ha = 70.0
        # AU = 700 / 450 = 1.55 AU
        # AU/ha = 0.155

        stats = LocationService.calculate_stocking_rate(location)

        assert stats["head_count"] == 2
        assert stats["total_weight"] == Decimal("700.00")
        assert stats["kg_per_ha"] == Decimal("70.00")
        assert stats["au_per_ha"] == round(
            Decimal("0.16"), 2
        )  # 1.555... / 10 = 0.1555 -> 0.16?
        # Wait, math:
        # Total Weight = 700
        # Kg/Ha = 700 / 10 = 70
        # AU/Ha = 70 / 450 = 0.15555...
        # Round(0.1555, 2) -> 0.16

        # Occupancy: Capacity 20. 2/20 = 10%
        assert stats["occupancy_rate"] == 10.0

    def test_dashboard_stats_resting_violation(self, location, cattle_list):
        location.status = LocationStatus.RESTING
        location.save()

        # No cattle yet
        stats = LocationService.get_dashboard_stats()
        assert location not in stats["resting_violations"]

        # Add cattle
        for c in cattle_list:
            c.location = location
            c.save()

        stats = LocationService.get_dashboard_stats()
        assert location in stats["resting_violations"]
        violation = stats["resting_violations"].get(pk=location.pk)
        assert violation.current_head_count == 2

    def test_calculate_stocking_rate_zero_area(self, location, cattle_list):
        """Test calculate_stocking_rate with zero area_hectares (line 27)."""
        # Create location with 0 area_hectares
        location_zero_area = baker.make(Location, area_hectares=0, capacity_head=10)

        # Add cattle
        for c in cattle_list:
            c.location = location_zero_area
            c.current_weight = c.weight_kg
            c.save()

        # Should return zeros (line 27)
        stats = LocationService.calculate_stocking_rate(location_zero_area)

        assert stats["total_weight"] == Decimal("0")
        assert stats["kg_per_ha"] == Decimal("0")
        assert stats["au_per_ha"] == Decimal("0")
        assert stats["occupancy_rate"] == 0.0

    def test_move_cattle_inactive_destination(
        self, location, location_b, cattle_list, user
    ):
        """Test move_cattle with inactive destination (line 52)."""

        # Set destination as inactive
        location_b.is_active = False
        location_b.save()

        # Attempt to move cattle
        with pytest.raises(ValidationError) as exc_info:
            MovementService.move_cattle(
                cattle_list=cattle_list,
                destination=location_b,
                performed_by=user,
                reason="ROTATION",
            )

        assert "inactive" in str(exc_info.value).lower()

    def test_move_cattle_resting_destination(
        self, location, location_b, cattle_list, user
    ):
        """Test move_cattle with RESTING destination (line 58)."""
        # Set destination as RESTING
        location_b.status = (
            "RESTING"  # Should be LocationStatus.RESTING but using string
        )
        location_b.save()

        # Should allow move (just passes through line 58)
        movement = MovementService.move_cattle(
            cattle_list=cattle_list,
            destination=location_b,
            performed_by=user,
            reason="ROTATION",
        )

        assert movement.pk is not None
        assert movement.destination == location_b
