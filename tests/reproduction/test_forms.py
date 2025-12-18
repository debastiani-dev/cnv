from unittest.mock import patch

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.locations.models import Location, LocationType
from apps.reproduction.forms import (
    BreedingEventForm,
    CalvingForm,
    MatingPlanForm,
    ReproductiveSeasonForm,
)
from apps.reproduction.models import BreedingEvent, Calving, MatingPlan


@pytest.mark.django_db
class TestReproductiveSeasonForm:
    def test_valid_form(self):
        data = {
            "name": "Test Season",
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timezone.timedelta(days=90)).date(),
            "active": True,
        }
        form = ReproductiveSeasonForm(data=data)
        assert form.is_valid()

    def test_invalid_form_missing_required(self):
        data = {}
        form = ReproductiveSeasonForm(data=data)
        assert not form.is_valid()
        assert "name" in form.errors
        assert "start_date" in form.errors


@pytest.mark.django_db
class TestBreedingEventForm:
    def test_valid_form(self):
        cow = Cattle.objects.create(
            tag="COW001",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            status=Cattle.STATUS_AVAILABLE,
        )
        data = {
            "dam": cow.pk,
            "date": timezone.now().date(),
            "breeding_method": BreedingEvent.METHOD_AI,
            "sire_name": "Bull 1",
        }
        form = BreedingEventForm(data=data)
        assert form.is_valid()

    def test_queryset_filtering(self):
        # Create cows with different statuses
        open_cow = Cattle.objects.create(
            tag="OPEN",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            status=Cattle.STATUS_AVAILABLE,
        )
        pregnant_cow = Cattle.objects.create(
            tag="PREG",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
        )

        form = BreedingEventForm()
        queryset = form.fields["dam"].queryset

        assert open_cow in queryset
        assert pregnant_cow not in queryset


@pytest.mark.django_db
class TestCalvingForm:
    def test_valid_form(self):
        cow = Cattle.objects.create(
            tag="COW002",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
        )
        # Create a breeding event linked to the cow
        breeding = BreedingEvent.objects.create(
            dam=cow,
            date=(timezone.now() - timezone.timedelta(days=280)).date(),
            breeding_method=BreedingEvent.METHOD_AI,
        )

        data = {
            "dam": cow.pk,
            "breeding_event": breeding.pk,
            "date": timezone.now().date(),
            "ease_of_birth": Calving.EASE_EASY,
            "calf_tag": "CALF001",
            "calf_sex": Cattle.SEX_MALE,
            "calf_weight": 35.5,
        }
        form = CalvingForm(data=data)
        assert form.is_valid(), form.errors

    def test_queryset_filtering(self):
        pregnant_cow = Cattle.objects.create(
            tag="PREG2",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
        )
        open_cow = Cattle.objects.create(
            tag="OPEN2",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            status=Cattle.STATUS_AVAILABLE,
        )

        form = CalvingForm()
        queryset = form.fields["dam"].queryset

        assert pregnant_cow in queryset
        assert open_cow not in queryset


@pytest.mark.django_db
class TestMatingPlanForm:
    def test_clean_active_status_requires_location(self):
        """Test that ACTIVE status requires a location (lines 137-141)."""
        form = MatingPlanForm(data={"status": MatingPlan.Status.ACTIVE, "location": ""})
        # Mock other required fields or allow validation to proceed to clean()
        form.cleaned_data = {
            "status": MatingPlan.Status.ACTIVE,
            "location": None,
            "sire": None,
            "cows": [],
        }
        # Force clean method call via full validation usually, or mock
        # Let's try simple valid data structure
        season = baker.make("reproduction.ReproductiveSeason")
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)

        data = {
            "season": season.pk,
            "sire": sire.pk,
            "cows": [],
            "status": MatingPlan.Status.ACTIVE,
            "location": "",
        }
        form = MatingPlanForm(data=data)
        assert not form.is_valid()
        assert "location" in form.errors
        assert "must select a location" in form.errors["location"][0]

    def test_clean_active_status_validates_move(self):
        """Test move validation during clean (lines 142-152)."""
        season = baker.make("reproduction.ReproductiveSeason")
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        loc = baker.make(Location, is_active=True, type=LocationType.PASTURE)

        data = {
            "season": season.pk,
            "sire": sire.pk,
            "cows": [cow.pk],
            "status": MatingPlan.Status.ACTIVE,
            "location": loc.pk,
        }

        # Mock validation to return error
        with patch(
            "apps.locations.services.allocation.AllocationService.validate_move"
        ) as mock_val:
            mock_val.return_value = {
                "valid": False,
                "errors": ["Capacity Exceeded"],
                "warnings": [],
            }
            form = MatingPlanForm(data=data)
            assert not form.is_valid()
            assert "location" in form.errors
            assert "Capacity Exceeded" in form.errors["location"]

    def test_clean_active_status_warnings_pass(self):
        """Test move validation warnings do not block save (lines 154-158)."""
        season = baker.make("reproduction.ReproductiveSeason")
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        loc = baker.make(Location, is_active=True, type=LocationType.PASTURE)

        data = {
            "season": season.pk,
            "sire": sire.pk,
            "cows": [cow.pk],
            "status": MatingPlan.Status.ACTIVE,
            "location": loc.pk,
        }

        with patch(
            "apps.locations.services.allocation.AllocationService.validate_move"
        ) as mock_val:
            mock_val.return_value = {
                "valid": True,
                "errors": [],
                "warnings": ["Crowded"],
            }
            form = MatingPlanForm(data=data)
            assert form.is_valid(), form.errors

    def test_save_moves_animals(self):
        """Test that saving as ACTIVE moves animals (lines 168-175)."""
        season = baker.make("reproduction.ReproductiveSeason")
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)
        loc_old = baker.make(Location, name="Old")
        loc_new = baker.make(Location, name="New", type=LocationType.PASTURE)

        sire.location = loc_old
        sire.save()
        cow.location = loc_old
        cow.save()

        data = {
            "season": season.pk,
            "sire": sire.pk,
            "cows": [cow.pk],
            "status": MatingPlan.Status.ACTIVE,
            "location": loc_new.pk,
        }

        # Ensure validation passes
        with patch(
            "apps.locations.services.allocation.AllocationService.validate_move",
            return_value={"valid": True, "errors": [], "warnings": []},
        ):
            form = MatingPlanForm(data=data)
            assert form.is_valid()
            form.save()

        sire.refresh_from_db()
        cow.refresh_from_db()
        assert sire.location == loc_new
        assert cow.location == loc_new
