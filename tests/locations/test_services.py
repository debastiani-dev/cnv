from decimal import Decimal

import pytest

from apps.locations.models import LocationStatus
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
