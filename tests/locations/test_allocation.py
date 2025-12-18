import pytest
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.locations.models import Location, LocationType
from apps.locations.services.allocation import AllocationService


@pytest.mark.django_db
class TestAllocationService:

    def test_allocation_conflict(self):
        """Test that validating a move to an occupied paddock returns an error."""
        paddock = baker.make(Location, type=LocationType.PASTURE, area_hectares=10)

        # Occupy it (status=AVAILABLE means active in paddock)
        baker.make(Cattle, location=paddock, status=Cattle.STATUS_AVAILABLE)

        # Try to move new batch
        incoming = [baker.make(Cattle) for _ in range(5)]

        result = AllocationService.validate_move(paddock, incoming)

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "occupied" in result["errors"][0].lower()

    def test_capacity_warning(self):
        """Test that overstocking returns a warning but valid=True (if allowed)."""
        # Small paddock (1 ha). Max capacity 1.5 AU.
        paddock = baker.make(Location, type=LocationType.PASTURE, area_hectares=1.0)

        # Move 2 cows (approx 2 AU if 450kg, or 2.0 default).
        # Using default 1.0 AU per cow -> 2 AU > 1.5 -> Warning
        incoming = [baker.make(Cattle) for _ in range(2)]

        result = AllocationService.validate_move(paddock, incoming)

        # Should be valid (warnings don't block by default in this logic)
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert "overstock" in result["warnings"][0].lower()

    def test_suggest_paddocks(self):
        """Test that service suggests compatible empty paddocks."""
        # Active Occupied Paddock (Invalid)
        occupied = baker.make(
            Location, type=LocationType.PASTURE, area_hectares=10, is_active=True
        )
        baker.make(Cattle, location=occupied, status=Cattle.STATUS_AVAILABLE)

        # Inactive Paddock (Invalid)
        inactive = baker.make(
            Location, type=LocationType.PASTURE, area_hectares=10, is_active=False
        )

        # Small Empty (Valid but capacity check)
        # 2 ha * 1.5 = 3.0 AU capacity.
        small = baker.make(
            Location, type=LocationType.PASTURE, area_hectares=2, is_active=True
        )

        # Large Empty (Valid)
        # 20 ha * 1.5 = 30 AU capacity.
        large = baker.make(
            Location, type=LocationType.PASTURE, area_hectares=20, is_active=True
        )

        # Request suggestions for 10 AU
        suggestions = AllocationService.suggest_paddocks(required_au=10)

        assert large in suggestions
        assert small not in suggestions  # 3.0 AU < 10 AU
        assert occupied not in suggestions
        assert inactive not in suggestions

    def test_get_au_with_weight(self):
        """Test AU calculation with weight (Line 23)."""
        # 450kg = 1.0 AU
        cow_std = baker.make(Cattle, current_weight=450)
        assert AllocationService.get_au(cow_std) == pytest.approx(1.0)

        # 900kg = 2.0 AU
        cow_heavy = baker.make(Cattle, current_weight=900)
        assert AllocationService.get_au(cow_heavy) == pytest.approx(2.0)

    def test_invalid_area(self):
        """Test validation failure when paddock has no area (Line 68)."""
        paddock = baker.make(Location, type=LocationType.PASTURE, area_hectares=0)
        animals = [baker.make(Cattle)]

        result = AllocationService.validate_move(paddock, animals)

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "no defined area" in result["errors"][0]
