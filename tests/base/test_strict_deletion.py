import pytest
from django.db.models import ProtectedError
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.models import BreedingEvent, Calving, ReproductiveSeason


@pytest.mark.django_db
class TestStrictDeletion:
    def test_reproductive_season_blocks_deletion_if_referenced(self):
        """
        Verify that a ReproductiveSeason cannot be deleted if a BreedingEvent references it.
        This tests the generic BaseModel logic inherited by ReproductiveSeason.
        """
        # Create Season
        season = baker.make(ReproductiveSeason)
        # Create Breeding Event linked to Season
        baker.make(BreedingEvent, batch=season)

        # Verify initial state
        assert ReproductiveSeason.objects.filter(pk=season.pk).exists()

        # Attempt to delete -> Should fail
        with pytest.raises(ProtectedError):
            season.delete()

        # Verify still exists
        assert ReproductiveSeason.objects.filter(pk=season.pk).exists()

        # Hard delete should also fail
        with pytest.raises(ProtectedError):
            season.delete(destroy=True)

        # Remove dependency
        BreedingEvent.objects.all().delete()

        # Now deletion should work
        season.delete()
        assert not ReproductiveSeason.objects.filter(pk=season.pk).exists()

    def test_cattle_blocks_deletion_if_referenced_as_dam(self):
        """
        Verify that a Cattle (dam) cannot be deleted if a Calving record references it.
        This tests generic BaseModel logic inherited by Cattle.
        """
        dam = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        baker.make(Calving, dam=dam)

        # Verify initial state
        assert Cattle.objects.filter(pk=dam.pk).exists()

        # Attempt delete -> Should fail (ProtectedError)
        with pytest.raises(ProtectedError):
            dam.delete()

        # Verify still exists
        assert Cattle.objects.filter(pk=dam.pk).exists()

        # Delete dependency destruction
        Calving.objects.all().delete()

        # Now deletion should work
        dam.delete()
        assert not Cattle.objects.filter(pk=dam.pk).exists()

    def test_cattle_soft_delete_works_without_dependencies(self):
        """
        Verify that Cattle can be soft deleted if no dependencies exist.
        """
        cattle = baker.make(Cattle)
        pk = cattle.pk
        cattle.delete()

        assert not Cattle.objects.filter(pk=pk).exists()
        assert Cattle.all_objects.filter(pk=pk, is_deleted=True).exists()

    def test_cattle_hard_delete_works_without_dependencies(self):
        """
        Verify that Cattle can be hard deleted if no dependencies exist.
        """
        cattle = baker.make(Cattle)
        pk = cattle.pk
        cattle.delete(destroy=True)

        assert not Cattle.all_objects.filter(pk=pk).exists()
