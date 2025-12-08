import pytest

from apps.cattle.models import Cattle
from apps.cattle.services.cattle_service import CattleService


@pytest.mark.django_db
class TestCattleService:
    def test_get_cattle_stats_active_only(self):
        """Verify stats only count active cattle for total and breed breakdown."""
        # Create Active Cattle
        Cattle.objects.create(
            tag="A1",
            breed=Cattle.BREED_ANGUS,
            status=Cattle.STATUS_AVAILABLE,
            weight_kg=100,
        )
        Cattle.objects.create(
            tag="A2",
            breed=Cattle.BREED_NELORE,
            status=Cattle.STATUS_AVAILABLE,
            weight_kg=100,
        )
        Cattle.objects.create(
            tag="A3",
            breed=Cattle.BREED_ANGUS,
            status=Cattle.STATUS_AVAILABLE,
            weight_kg=100,
        )

        # Create Inactive Cattle
        Cattle.objects.create(
            tag="S1", breed=Cattle.BREED_ANGUS, status=Cattle.STATUS_SOLD, weight_kg=100
        )
        Cattle.objects.create(
            tag="D1",
            breed=Cattle.BREED_NELORE,
            status=Cattle.STATUS_DEAD,
            weight_kg=100,
        )

        stats = CattleService.get_cattle_stats()

        # Check Total (Should be 3 active)
        assert stats["total"] == 3

        # Check specific status counts
        assert stats["available"] == 3
        assert stats["sold"] == 1
        assert stats["dead"] == 1

        # Check Breed Breakdown (Should only include the 3 active cattle)
        # Angus: 2 active (A1, A3), 1 sold (excluded) -> Total 2
        # Nelore: 1 active (A2), 1 dead (excluded) -> Total 1
        breakdown = stats["breed_breakdown"]
        assert breakdown["Angus"] == 2
        assert breakdown["Nelore"] == 1
        assert sum(breakdown.values()) == 3

    def test_breed_label_mapping(self):
        """Verify breed codes are mapped to title-cased labels."""
        Cattle.objects.create(
            tag="B1",
            breed=Cattle.BREED_BRAHMAN,
            status=Cattle.STATUS_AVAILABLE,
            weight_kg=100,
        )
        Cattle.objects.create(
            tag="O1",
            breed=Cattle.BREED_OTHER,
            status=Cattle.STATUS_AVAILABLE,
            weight_kg=100,
        )
        # Undefined/custom breed (fallback check) - though model enforces choices now, good to verify robustness if manual insertion
        Cattle.objects.create(
            tag="U1",
            breed="unknown_breed",
            status=Cattle.STATUS_AVAILABLE,
            weight_kg=100,
        )

        stats = CattleService.get_cattle_stats()
        breakdown = stats["breed_breakdown"]

        assert breakdown["Brahman"] == 1
        assert breakdown["Other"] == 1
        # Fallback for unknown should be title cased code
        assert breakdown["Unknown_Breed"] == 1
