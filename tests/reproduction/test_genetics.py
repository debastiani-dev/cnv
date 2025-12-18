import pytest
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.services.genetics import InbreedingService


@pytest.mark.django_db
class TestInbreedingService:
    def test_clean_match(self):
        """Test unrelated animals return SAFE."""
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE, name="Bull A")
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE, name="Cow B")

        _, risk_level, _ = InbreedingService.calculate_coefficient(sire, dam)
        assert risk_level == InbreedingService.RISK_SAFE

    def test_parent_child_risk(self):
        """Test mating a Sire with his Daughter returns CRITICAL."""
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE, name="Daddy Bull")
        daughter = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, sire=sire, name="Daughter Cow"
        )

        _, risk_level, reason = InbreedingService.calculate_coefficient(sire, daughter)
        assert risk_level == InbreedingService.RISK_CRITICAL
        assert "direct ancestor" in reason.lower()

    def test_sibling_detection(self):
        """Test Half-Siblings (sharing a Sire) return HIGH risk."""
        shared_sire = baker.make(Cattle, sex=Cattle.SEX_MALE, name="Shared Dad")

        bull_b = baker.make(
            Cattle, sex=Cattle.SEX_MALE, sire=shared_sire, name="Brother"
        )
        cow_a = baker.make(
            Cattle, sex=Cattle.SEX_FEMALE, sire=shared_sire, name="Sister"
        )

        _, risk_level, reason = InbreedingService.calculate_coefficient(bull_b, cow_a)
        assert risk_level == InbreedingService.RISK_HIGH
        assert "half-siblings" in reason.lower()

    def test_ancestor_recursion(self):
        """Test that get_ancestors traverses up correctly."""
        # Great-Grandpa -> Grandpa -> Dad -> Animal
        g_grandpa = baker.make(Cattle, name="G-Grandpa")
        grandpa = baker.make(Cattle, sire=g_grandpa, name="Grandpa")  # Depth 3
        dad = baker.make(Cattle, sire=grandpa, name="Dad")  # Depth 2
        animal = baker.make(Cattle, sire=dad, name="Me")  # Depth 1

        ancestors = InbreedingService.get_ancestors(animal, generations=3)

        assert dad.pk in ancestors
        assert grandpa.pk in ancestors
        assert g_grandpa.pk in ancestors
        assert len(ancestors) == 3

    def test_deep_common_ancestor_warning(self):
        """Test common ancestor deeper in tree returns WARNING."""
        # Shared Grandpa
        common_grandpa = baker.make(Cattle, name="Grandpa")

        # Line A
        dad_a = baker.make(Cattle, sire=common_grandpa, name="Dad A")
        bull = baker.make(Cattle, sire=dad_a, sex=Cattle.SEX_MALE, name="Bull")

        # Line B
        dad_b = baker.make(Cattle, sire=common_grandpa, name="Dad B")
        cow = baker.make(Cattle, sire=dad_b, sex=Cattle.SEX_FEMALE, name="Cow")

        _, risk_level, _ = InbreedingService.calculate_coefficient(bull, cow)
        # Not siblings (different parents), but share a grandparent
        assert risk_level == InbreedingService.RISK_WARNING

    def test_dam_ancestry(self):
        """Test get_ancestors traverses female line (lines 34-37)."""
        g_grandma = baker.make(Cattle, name="G-Grandma", sex=Cattle.SEX_FEMALE)
        dam = baker.make(Cattle, dam=g_grandma, name="Mom", sex=Cattle.SEX_FEMALE)
        calf = baker.make(Cattle, dam=dam, name="Calf")

        ancestors = InbreedingService.get_ancestors(calf, generations=2)
        assert dam.pk in ancestors
        assert g_grandma.pk in ancestors

    def test_dam_is_ancestor_risk(self):
        """Test risk when Dam is an ancestor of the Sire (lines 60-66)."""
        # Case: Sire's Mother is the cow we are mating him with (Oedipus complex?)
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE, name="Mom")
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE, dam=dam, name="Son")

        _, risk_level, reason = InbreedingService.calculate_coefficient(sire, dam)
        assert risk_level == InbreedingService.RISK_CRITICAL
        assert "Dam is a direct ancestor" in reason
