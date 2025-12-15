import pytest
from django.core.exceptions import ValidationError

from apps.cattle.models import Cattle


@pytest.mark.django_db
class TestCattleSexValidation:

    def test_sire_must_be_male(self):
        """Test that assigning a female as sire raises ValidationError."""
        Cattle.objects.create(tag="BULL01", sex=Cattle.SEX_MALE)
        female_cow = Cattle.objects.create(tag="COW01", sex=Cattle.SEX_FEMALE)

        # Try to assign female as sire
        calf = Cattle(tag="CALF01", sex=Cattle.SEX_MALE, sire=female_cow)

        with pytest.raises(ValidationError) as excinfo:
            calf.full_clean()

        assert "The Sire must be a male." in str(excinfo.value)

    def test_dam_must_be_female(self):
        """Test that assigning a male as dam raises ValidationError."""
        male_bull = Cattle.objects.create(tag="BULL02", sex=Cattle.SEX_MALE)
        Cattle.objects.create(tag="COW02", sex=Cattle.SEX_FEMALE)

        # Try to assign male as dam
        calf = Cattle(tag="CALF02", sex=Cattle.SEX_FEMALE, dam=male_bull)

        with pytest.raises(ValidationError) as excinfo:
            calf.full_clean()

        assert "The Dam must be a female." in str(excinfo.value)

    def test_valid_parent_assignment(self):
        """Test that assigning correct sex parents is valid."""
        male_bull = Cattle.objects.create(tag="BULL03", sex=Cattle.SEX_MALE)
        female_cow = Cattle.objects.create(tag="COW03", sex=Cattle.SEX_FEMALE)

        calf = Cattle(
            tag="CALF03", sex=Cattle.SEX_FEMALE, sire=male_bull, dam=female_cow
        )

        # Should not raise
        calf.full_clean()
        calf.save()

        assert calf.sire == male_bull
        assert calf.dam == female_cow
