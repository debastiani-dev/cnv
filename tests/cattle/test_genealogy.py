import pytest
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.cattle.services.genealogy import GenealogyService


@pytest.mark.django_db
class TestGenealogyService:
    def test_full_pedigree_depth_20(self):
        """
        Verify that the service can fetch a deep lineage (20 generations)
        using the iterative batch fetching strategy.
        """
        # Create a chain of 20 animals: Gen 20 -> ... -> Gen 1 (Root)
        # Gen 20 is the oldest ancestor.
        current_ancestor = baker.make(Cattle, name="Gen 20", sex=Cattle.SEX_MALE)

        for i in range(19, 0, -1):
            # Each subsequent animal has the previous one as Sire
            child = baker.make(
                Cattle, name=f"Gen {i}", sex=Cattle.SEX_MALE, sire=current_ancestor
            )
            current_ancestor = child

        root_animal = current_ancestor  # Gen 1

        # Structure should be nest of 20 levels
        tree = GenealogyService.get_full_pedigree(root_animal)

        # Verify depth by traversing
        depth = 0
        node = tree
        while node:
            depth += 1
            node = node.get("sire")

        assert depth == 20
        assert tree["animal"].name == "Gen 1"

    def test_pedigree_cycle_detection(self):
        """
        Verify that the service detects cycles and stops infinite recursion.
        Note: Django models usually prevent self-referencing save, but complex loops might exist.
        We force a loop by manually setting IDs if needed, or relying on bakery.
        """
        # A -> B -> A
        a = baker.make(Cattle, name="A")
        b = baker.make(Cattle, name="B", sire=a)

        # Django doesn't allow A.sire = B easily if B depends on A (circular dependency on delete/etc),
        # but for simple FK update it allows it.
        a.sire = b
        a.save()

        tree = GenealogyService.get_full_pedigree(a)

        # Expected: A -> B -> A (Cycle)
        assert tree["animal"] == a
        assert tree["sire"]["animal"] == b
        assert tree["sire"]["sire"]["is_cycle"] is True
        assert tree["sire"]["sire"]["animal"] == a

    def test_progeny_stats(self):
        """
        Verify progeny statistics aggregation.
        """
        bull = baker.make(Cattle, sex=Cattle.SEX_MALE)

        # 3 Male calves, weights 30, 40, 50 (Avg 40)
        baker.make(
            Cattle,
            sire=bull,
            sex=Cattle.SEX_MALE,
            weight_kg=30,
            current_weight=200,
            _quantity=1,
        )
        baker.make(
            Cattle,
            sire=bull,
            sex=Cattle.SEX_MALE,
            weight_kg=40,
            current_weight=300,
            _quantity=1,
        )
        baker.make(
            Cattle,
            sire=bull,
            sex=Cattle.SEX_MALE,
            weight_kg=50,
            current_weight=400,
            _quantity=1,
        )

        # 2 Female calves, weights 25, 35 (Avg 30)
        baker.make(
            Cattle,
            sire=bull,
            sex=Cattle.SEX_FEMALE,
            weight_kg=25,
            current_weight=220,
            _quantity=1,
        )
        baker.make(
            Cattle,
            sire=bull,
            sex=Cattle.SEX_FEMALE,
            weight_kg=35,
            current_weight=380,
            _quantity=1,
        )

        stats = GenealogyService.get_progeny_stats(bull)

        assert stats["total_offspring"] == 5
        # Avg birth weight: (30+40+50+25+35)/5 = 180/5 = 36
        assert stats["avg_birth_weight"] == pytest.approx(36.0, 0.01)
        # Avg current weight: (200+300+400+220+380)/5 = 1500/5 = 300
        assert stats["avg_current_weight"] == pytest.approx(300.0, 0.01)

        # Check distribution
        # [{'sex': 'female', 'count': 2}, {'sex': 'male', 'count': 3}] (ordered by sex)
        dist = stats["sex_distribution"]
        female_stat = next(d for d in dist if d["sex"] == Cattle.SEX_FEMALE)
        male_stat = next(d for d in dist if d["sex"] == Cattle.SEX_MALE)

        assert female_stat["count"] == 2
        assert male_stat["count"] == 3
