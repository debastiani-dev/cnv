import pytest
from model_bakery import baker

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

    def test_get_all_cattle_filters(self):
        """Verify sorting by filters works."""
        Cattle.objects.create(
            tag="A1", breed=Cattle.BREED_ANGUS, status=Cattle.STATUS_AVAILABLE
        )
        Cattle.objects.create(
            tag="A2", breed=Cattle.BREED_NELORE, status=Cattle.STATUS_SOLD
        )
        Cattle.objects.create(
            tag="A3", breed=Cattle.BREED_ANGUS, status=Cattle.STATUS_DEAD
        )

        # Filter by Breed
        qs = CattleService.get_all_cattle(breed=Cattle.BREED_ANGUS)
        assert qs.count() == 2
        assert list(qs.values_list("tag", flat=True)) == ["A1", "A3"]

        # Filter by Status
        qs = CattleService.get_all_cattle(status=Cattle.STATUS_AVAILABLE)
        assert qs.count() == 1
        assert qs.first().tag == "A1"

        # Combine
        qs = CattleService.get_all_cattle(
            breed=Cattle.BREED_ANGUS, status=Cattle.STATUS_DEAD
        )
        assert qs.count() == 1
        assert qs.first().tag == "A3"

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

    def test_get_productivity_stats(self):
        """Verify calculations for pregnancy and mortality rates."""
        # Pregnancy Rate Setup
        # 10 Eligible cows: 5 Pregnant, 5 Open/Bred
        # We use baker to avoid unique constraint issues on 'tag'
        baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
            _quantity=5,
        )
        baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            status=Cattle.STATUS_AVAILABLE,
            _quantity=5,
        )

        # Ignored for Pregnancy Rate (Males, Dead, Sold, or Calves if filtered strictly but code checks sex=Female)
        baker.make(Cattle, sex=Cattle.SEX_MALE, status=Cattle.STATUS_AVAILABLE)

        # Mortality Rate Setup
        # Total Ever: 11 active (10 cows + 1 bull) + 1 Dead = 12 Total
        baker.make(Cattle, status=Cattle.STATUS_DEAD, sex=Cattle.SEX_FEMALE)

        stats = CattleService.get_productivity_stats()

        # Pregnancy Rate: 5 Pregnant / 10 Eligible = 50.0%
        assert stats["pregnancy_rate"] == pytest.approx(50.0)
        assert stats["pregnant_count"] == 5

        # Mortality Rate: 1 Dead / 12 Total Ever = 8.3%
        assert stats["mortality_rate"] == pytest.approx(8.3)
        assert stats["dead_count"] == 1
